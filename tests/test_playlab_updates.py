import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update
from playlab import AGENDA,WEEKEND_FORM,WEEKEND_SHORT,collect_programme,programme_watch,weekend_form,parse_choice
from eligibility import assess
NOW=datetime(2026,11,18,12,tzinfo=ZoneInfo('Europe/Lisbon'))
PROGRAMME=json.loads((ROOT/'public/data/playlab-programme.json').read_text())
NEW='https://docs.google.com/forms/d/e/new_public_programme/viewform'
AGENDA_HTML=f'<a href="{NEW}">Inscrição - ao fim de semana</a><img src="https://sites.google.com/sitesv-images-rt/poster=w1280">'
LABEL='Baby Lab de Natal, 6-18 meses/months - Sáb. 19/12, 10:00-10:45'
FORM=f'<h1>Programa de dezembro 2026</h1><div role="checkbox" data-answer-value="{LABEL}"></div>'

class PlayLabUpdatesTests(unittest.TestCase):
    def test_new_official_form_and_explicit_year_extend_live_collection_without_extending_review(self):
        self.assertEqual(weekend_form(AGENDA_HTML,AGENDA),NEW)
        events,report=collect_programme(PROGRAMME,FORM,None,NOW,update.make_event,NEW,AGENDA_HTML)
        self.assertEqual(len(events),1);self.assertEqual(events[0]['date'],'2026-12-19')
        self.assertFalse(report['reviewNeeded']);self.assertEqual(events[0]['bookingUrl'],NEW)
        self.assertEqual(events[0]['sourceUrl'],AGENDA)
        self.assertEqual(events[0]['sessionEvidence']['formUrl'],NEW)
        self.assertEqual(events[0]['price'],'Por confirmar')
        registry=json.loads((ROOT/'public/data/venues.json').read_text())
        self.assertEqual(assess(events[0],registry,NOW)['validationStatus'],'verified')
        self.assertEqual(PROGRAMME['validUntil'],'2026-12-13')

    def test_unlinked_form_and_unpublished_year_do_not_import_new_sessions(self):
        for agenda,form in [(None,FORM),('<a href="https://evil.example">Inscrição - ao fim de semana</a>',FORM),(AGENDA_HTML,FORM.replace('2026',''))]:
            events,report=collect_programme(PROGRAMME,form,None,NOW,update.make_event,NEW,agenda)
            self.assertEqual(events,[]);self.assertTrue(report['reviewNeeded'])
        self.assertEqual(collect_programme(PROGRAMME,None,'HTTP 401',NOW,update.make_event,NEW,AGENDA_HTML)[0],[])

    def test_full_date_year_and_new_year_rollover_are_explicit(self):
        label='Baby Yoga, 6-18 meses - Sáb. 02/01/2027, 10:00-10:45'
        self.assertEqual(parse_choice(label,None)['date'],'2027-01-02')
        self.assertIsNone(parse_choice(label.replace('02/01/2027','02/01'),None))
        now=datetime(2026,12,20,12,tzinfo=NOW.tzinfo)
        html=f'<div role="checkbox" data-answer-value="{label}"></div>'
        events,report=collect_programme({},html,None,now,update.make_event,NEW,AGENDA_HTML)
        self.assertEqual(len(events),1);self.assertEqual(events[0]['date'],'2027-01-02')
        self.assertFalse(report['reviewNeeded'])

    def test_invalid_or_incomplete_public_options_keep_dated_fallback_and_do_not_repair_new_typos(self):
        bad=FORM.replace('19/12','20/12') # Saturday label on Sunday.
        events,report=collect_programme(PROGRAMME,bad,None,NOW,update.make_event)
        self.assertTrue(report['reviewNeeded']);self.assertEqual(report['liveSessions'],0)
        self.assertEqual(len(events),8)
        self.assertTrue(all(e['sessionEvidence']['checkedAt']==PROGRAMME['reviewedAt'] for e in events))

    def test_programme_reference_changes_persist_once_and_failed_reads_do_not_erase_snapshot(self):
        news='<a href="/p/novembro">Novembro</a>'
        first,reasons=programme_watch(AGENDA_HTML,news,NEW,None,{},NOW)
        self.assertEqual(reasons,[])
        # Width-only Google image changes are not a programme edit.
        same,reasons=programme_watch(AGENDA_HTML.replace('w1280','w1600'),news,NEW,None,first,NOW+timedelta(hours=1))
        self.assertEqual(reasons,[])
        changed,reasons=programme_watch(AGENDA_HTML.replace('poster=','new-poster='),news+'<a href="/p/dezembro">Dezembro</a>',NEW,None,same,NOW+timedelta(hours=2))
        self.assertEqual(len(reasons),2);self.assertTrue(changed['pendingReview'])
        again,reasons=programme_watch(None,None,None,None,changed,NOW+timedelta(hours=3))
        self.assertEqual(reasons,[]);self.assertEqual(again['snapshot'],changed['snapshot']);self.assertTrue(again['pendingReview'])
        reviewed,_=programme_watch(None,None,None,None,again,NOW+timedelta(hours=4),(NOW+timedelta(hours=4)).isoformat())
        self.assertFalse(reviewed['pendingReview'])

    def test_scan_follows_changed_form_and_removal_does_not_reuse_old_review(self):
        source={'name':'PlayLab Porto','url':'https://playlabporto.beehiiv.com/','programmeUrls':[AGENDA]}
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder);(data/'playlab-programme.json').write_text(json.dumps(PROGRAMME))
            def fetch(url):return ({source['url']:'<main>Newsletter</main>',AGENDA:AGENDA_HTML,NEW:FORM}.get(url,'<main></main>'),None)
            with patch.object(update,'DATA',data),patch.object(update,'fetch',side_effect=fetch),patch.object(update.time,'sleep'):
                first,events,h,*_=update.scan([source],{},{},NOW)
            self.assertEqual([e['date'] for e in events['events']],['2026-12-19'])
            (data/'events.json').write_text(json.dumps(events))
            # Live form becomes inaccessible: a superseded manual programme must not return.
            def blocked(url):return (None,'HTTP 401') if url==NEW else fetch(url)
            with patch.object(update,'DATA',data),patch.object(update,'fetch',side_effect=blocked),patch.object(update.time,'sleep'):
                _,next_events,_,*_=update.scan([source],first,h,NOW+timedelta(hours=1))
            self.assertEqual(len(next_events['events']),1)
            self.assertTrue(all(e['date']=='2026-12-19' for e in next_events['events']))
            def removed(url):return ('<main>Agenda por atualizar</main>',None) if url==AGENDA else fetch(url)
            with patch.object(update,'DATA',data),patch.object(update,'fetch',side_effect=removed),patch.object(update.time,'sleep'):
                _,gone,_,*_=update.scan([source],first,h,NOW+timedelta(hours=1))
            self.assertEqual(gone['events'],[])
