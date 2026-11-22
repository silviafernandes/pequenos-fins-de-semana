import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update
from maia import collect, monthly_sessions, page_url, listing_expired, INDEX
from source_health import source_health

NOW=datetime(2026,11,22,12,tzinfo=ZoneInfo('Europe/Lisbon'))
MONTH='https://www.cm-maia.pt/viver/cultura/noticias-e-eventos/evento-12/agenda-biblioteca-municipal-da-maia-nov-26'
PAYLOAD=b'%PDF-test-reviewed-artwork'


class MaiaTests(unittest.TestCase):
    def setUp(self):
        self.programme=json.loads((ROOT/'public/data/maia-programmes.json').read_text())
        review=self.programme['programmes'][0]
        review.update(sha256=hashlib.sha256(PAYLOAD).hexdigest(),reviewedAt='2026-11-22T10:00:00+00:00')
        self.url=review['pageUrl'];self.document=review['documentUrl']
        self.month=(ROOT/'tests/fixtures/maia-monthly.html').read_text()
        self.festival=(ROOT/'tests/fixtures/maia-contamina.html').read_text()
        self.index='<a class="linl_overlay" href="'+self.url+'">Contamina</a><a class="linl_overlay" href="'+MONTH+'">Agenda</a>'
        self.pages={INDEX:self.index,self.url:self.festival,MONTH:self.month}
        self.source={'name':'Biblioteca da Maia','url':INDEX,'type':'maia-programmes'}

    def get(self,url):return self.pages.get(url),None if url in self.pages else 'HTTP 404'

    def run_collection(self,payload=PAYLOAD,now=NOW):
        return collect(self.source,self.get,lambda u:(payload,None),self.programme,now,update.make_event)

    def test_reviewed_linked_pdf_recovers_the_baby_show_without_workshop_booking(self):
        pages,report=self.run_collection()
        self.assertEqual(report['parsedSessions'],1)
        event=pages[self.url][0]
        self.assertEqual((event['date'],event['start'],event['end']),('2026-11-28','11:30',None))
        self.assertEqual((event['minMonths'],event['maxMonths']),(0,72))
        self.assertEqual(event['venue'],'Café Concerto do Fórum da Maia')
        self.assertIsNone(event['bookingUrl'],'The published form is only for workshops')
        self.assertEqual(event['price'],'Por confirmar')
        self.assertEqual(event['status'],'unverified')
        self.assertEqual(event['sessionEvidence']['documentSha256'],hashlib.sha256(PAYLOAD).hexdigest())
        self.assertEqual(event['sessionEvidence']['checkedAt'],NOW.isoformat())
        self.assertEqual(report['documentChecks'][0]['status'],'reviewed')

    def test_changed_pdf_requires_review_and_does_not_refresh_old_facts(self):
        pages,report=self.run_collection(b'%PDF-new-programme')
        self.assertEqual(pages[self.url],[])
        self.assertEqual(report['documentChecks'][0]['status'],'needs-review')
        self.assertTrue(report['reviewNeeded'])

    def test_removed_document_or_changed_page_dates_title_or_cancellation_cannot_inherit_review(self):
        for old,new in [(self.document.split('.pt')[1],'/cmmaia/uploads/writer_file/document/9999/changed.pdf'),('2026-11-27','2026-11-26'),('7ª edição Contamina','8ª edição Contamina'),('7ª edição Contamina','Cancelado: 7ª edição Contamina')]:
            with self.subTest(new=new):
                self.pages[self.url]=self.festival.replace(old,new)
                pages,report=self.run_collection()
                self.assertEqual(pages[self.url],[])

    def test_missing_pdf_is_reported_as_a_partial_collection(self):
        pages,report=collect(self.source,self.get,lambda u:(None,'HTTP 503'),self.programme,NOW,update.make_event)
        self.assertEqual(pages[self.url],[])
        self.assertEqual(report['documentChecks'][0]['status'],'unavailable')
        self.programme['leads']=[]
        report['reviewNeeded']=False
        self.assertEqual(source_health(report)['status'],'partial')

    def test_monthly_fields_stay_with_their_own_session_and_publish_multiple_times(self):
        events=monthly_sessions(BeautifulSoup(self.month,'html.parser'),MONTH,NOW.replace(day=1),update.make_event)
        self.assertEqual([(e['title'],e['date'],e['start'],e['end']) for e in events],[('Histórias em movimento: Yoga e contos para bebés','2026-11-07','16:00','16:40'),('Histórias em movimento: Yoga e contos para bebés','2026-11-07','17:00','17:40')])
        self.assertTrue(all((e['minMonths'],e['maxMonths'])==(6,36) for e in events))
        self.assertEqual(monthly_sessions(BeautifulSoup(self.month,'html.parser'),MONTH,NOW,update.make_event),[])

    def test_opening_ranges_missing_year_and_ages_three_plus_do_not_create_sessions(self):
        for old,new in [('16h00 e 17h00 (duas sessões com grupos diferentes)','09h30–18h00'),('2026-11-01 00:00:00',''),('bebés 6 aos 36 meses','A partir dos 3 anos')]:
            with self.subTest(new=new):
                events=monthly_sessions(BeautifulSoup(self.month.replace(old,new),'html.parser'),MONTH,NOW.replace(day=1),update.make_event)
                self.assertEqual(events,[])

    def test_known_programme_is_rechecked_even_if_it_leaves_the_library_front_page(self):
        self.pages[INDEX]='<main>Nenhuma ligação na primeira página</main>'
        pages,report=self.run_collection()
        self.assertEqual(len(pages[self.url]),1)
        self.assertEqual(report['parsedSessions'],1)
        pages,report=self.run_collection(now=NOW+timedelta(days=8))
        self.assertNotIn(self.url,pages)

    def test_expired_archives_and_reviews_cannot_crowd_out_a_new_programme(self):
        archive='<div class="linl_block"><a class="linl_overlay" href="/agenda/evento-42/old-{n}">Antigo</a><div class="dates"><span class="dia">31</span><span class="mes_curto">Out</span><span class="ano">\'26</span></div></div>'
        self.pages[INDEX]=''.join(archive.format(n=n) for n in range(15))+self.index
        for n in range(15):
            self.programme['programmes'].insert(0,{'pageUrl':'https://www.cm-maia.pt/agenda/evento-42/old-review-'+str(n),'dateRange':['2025-11-27','2025-11-29']})
        pages,report=self.run_collection()
        self.assertEqual(report['candidateLinks'],2)
        self.assertFalse(report['truncated'])
        self.assertEqual(len(pages[self.url]),1)

    def test_archive_end_dates_can_cross_month_or_year_boundaries(self):
        html='<div class="linl_block"><a href="event">Evento</a><div class="dates"><span class="dia">01</span><span class="mes_curto">Jun</span><span class="ano">\'25</span><span class="dia">30</span><span class="mes_curto">Set</span><span class="ano">\'26</span></div></div>'
        self.assertTrue(listing_expired(BeautifulSoup(html,'html.parser').a,NOW.date()))
        self.assertFalse(listing_expired(BeautifulSoup(html.replace("'26","'27"),'html.parser').a,NOW.date()))

    def test_city_alias_urls_are_deduplicated_and_social_leads_do_not_invent_ages_or_year(self):
        alias='https://www.cm-maia.pt/institucional/atualidade-e-participacao/agenda/todos-os-eventos/evento-42/7-edicao-contamina-festival-de-contos-da-maia'
        self.assertEqual(page_url(alias),self.url)
        self.pages[INDEX]+='<a class="linl_overlay" href="'+alias+'">Duplicado</a>'
        pages,report=self.run_collection()
        self.assertEqual(report['candidateLinks'],2)
        self.assertEqual(report['parsedSessions'],1)
        self.assertEqual(len(report['reviewCandidates']),1)
        self.assertNotIn('date',report['reviewCandidates'][0])
        self.assertNotIn('minMonths',report['reviewCandidates'][0])
        self.assertTrue(report['reviewNeeded'])

    def test_scan_publishes_only_verified_session_and_invalidates_it_on_programme_change(self):
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)
            (data/'maia-programmes.json').write_text(json.dumps(self.programme))
            (data/'events.json').write_text(json.dumps({'events':[]}))
            def fetch(url,**kwargs):return (PAYLOAD,None) if url==self.document else self.get(url)
            with patch.object(update,'DATA',data),patch.object(update,'fetch',side_effect=fetch):
                discoveries,events,history,_,_=update.scan([self.source],{}, {},NOW)
                self.assertEqual(len(events['events']),1)
                event=events['events'][0]
                self.assertTrue(event['distanceWithinRadius'])
                self.assertEqual(event['venueId'],'forum-maia')
                self.assertEqual(event['addedAt'],NOW.isoformat())
                (data/'events.json').write_text(json.dumps(events))
                self.pages[self.url]=self.festival.replace('programa_detalhado_2026__1_.pdf','changed.pdf')
                _,changed,_,_,_=update.scan([self.source],discoveries,history,NOW+timedelta(minutes=1))
                self.assertEqual(changed['events'],[])
                self.assertEqual(len(changed['pendingEvents']),1)
                self.assertNotIn('sessionEvidence',changed['pendingEvents'][0])


if __name__=='__main__':unittest.main()
