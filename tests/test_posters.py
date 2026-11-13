import copy
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import posters
import update
from eligibility import assess

NOW=datetime(2026,11,13,12,tzinfo=ZoneInfo('Europe/Lisbon'))
HTML=(ROOT/'tests/fixtures/matosinhos-yoga-poster.html').read_text()
REVIEW=json.loads((ROOT/'public/data/poster-reviews.json').read_text())[0]
URL=REVIEW['pageUrl']
IMAGE=b'reviewed poster test bytes'
OCR={'text':'Yoga de encantar 14 novembro 2026 10h00 Biblioteca Municipal Florbela Espanca familias com criancas dos 6 aos 36 meses gratuita','confidence':96,'error':None}

class PosterTests(unittest.TestCase):
    def setUp(self):
        self.review=copy.deepcopy(REVIEW)
        self.review['sha256']=hashlib.sha256(IMAGE).hexdigest()

    def parse(self,html=HTML,image=IMAGE,reviews=None):
        with patch.object(posters,'ocr_text',return_value=OCR):
            return posters.from_posters(html,URL,'Bibliotecas de Matosinhos',NOW,update.make_event,lambda u:(image,None),[self.review] if reviews is None else reviews)

    def test_reviewed_official_image_recovers_session_and_soldout(self):
        self.assertIsNone(update.library_event(HTML,URL,'Biblioteca',NOW))
        event,reports=self.parse()
        self.assertEqual((event['date'],event['start'],event['end']),('2026-11-14','10:00',None))
        self.assertEqual((event['minMonths'],event['maxMonths']),(6,36))
        self.assertEqual((event['status'],event['price']),('soldout','Gratuito'))
        self.assertEqual(event['sessionEvidence']['imageSha256'],self.review['sha256'])
        registry=json.loads((ROOT/'public/data/venues.json').read_text())
        self.assertEqual(assess(event,registry,NOW)['validationStatus'],'verified')
        self.assertEqual(reports[0]['status'],'reviewed')
        self.assertEqual(len(reports),1)

    def test_even_high_confidence_ocr_does_not_publish_without_review(self):
        event,reports=self.parse(reviews=[])
        self.assertIsNone(event)
        self.assertEqual(reports[0]['status'],'needs-review')
        self.assertEqual(reports[0]['proposedFields']['start'],'10:00')
        self.assertEqual(reports[0]['proposedFields']['minMonths'],6)

    def test_changed_artwork_date_or_title_invalidates_review(self):
        for changes in [dict(image=b'changed poster'),dict(html=HTML.replace('2026-11-14','2026-11-15')),dict(html=HTML.replace('Yoga de Encantar','Outra oficina'))]:
            event,reports=self.parse(**changes)
            self.assertIsNone(event)
            self.assertEqual(reports[0]['status'],'needs-review')

    def test_cancelled_page_cannot_reuse_an_unchanged_poster(self):
        event,_=self.parse(html=HTML.replace('já se encontra esgotada','foi cancelada'))
        self.assertIsNone(event)

    def test_external_images_are_not_fetched_or_trusted(self):
        html=HTML.replace('/thumbs/','https://elsewhere.example/thumbs/').replace('/imgcrop/','https://elsewhere.example/imgcrop/')
        with patch.object(posters,'ocr_text') as ocr:
            event,reports=posters.from_posters(html,URL,'Biblioteca',NOW,update.make_event,lambda _:self.fail('External image fetched'),[self.review])
        self.assertIsNone(event);self.assertEqual(reports,[]);ocr.assert_not_called()

    def test_image_fetch_error_remains_explicit(self):
        event,reports=posters.from_posters(HTML,URL,'Biblioteca',NOW,update.make_event,lambda _:(None,'HTTP 403'),[self.review])
        self.assertIsNone(event);self.assertEqual(reports[0]['error'],'HTTP 403')

    def test_ocr_does_not_repair_ambiguous_time_or_accept_older_age(self):
        self.assertNotIn('start',posters.proposed_fields('14 novembro 2026 1OhOO'))
        self.assertNotIn('start',posters.proposed_fields('10h00 e 11h30'))
        self.assertNotIn('minMonths',posters.proposed_fields('dos 3 aos 6 anos'))
        self.assertNotIn('minMonths',posters.proposed_fields('36 aos 48 meses'))

    def test_missing_ocr_engine_has_an_explicit_reason(self):
        with patch.object(posters.shutil,'which',return_value=None):
            self.assertIn('indisponível',posters.ocr_text(IMAGE)['error'])

    def test_registration_opening_cannot_override_soldout(self):
        event,_=self.parse()
        update.apply_registration([event],{},URL,event['title'],'Biblioteca',[],['2026-11-13T10:00+00:00'],NOW.isoformat())
        self.assertEqual(event['status'],'soldout')

    def test_scan_preserves_soldout_over_previously_scheduled_status(self):
        event,_=self.parse();event.update(status='scheduled',openingAt='2026-11-13T10:00+00:00')
        root='https://www.bibliotecasearquivosmatosinhos.pt/'
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory)
            (data/'events.json').write_text(json.dumps({'events':[event]}))
            (data/'poster-reviews.json').write_text(json.dumps([self.review]))
            def fetch(url,*args,**kwargs):
                if kwargs.get('binary'):return IMAGE,None
                return ('<main></main>' if url==root else HTML),None
            with patch.object(update,'DATA',data),patch.object(update,'fetch',side_effect=fetch),patch.object(update.time,'sleep'):
                discoveries,events,_,_,_=update.scan([{'name':'Biblioteca','url':root}],{},{},NOW)
        self.assertEqual(events['events'][0]['status'],'soldout')
        self.assertEqual(discoveries['sourceIndex']['Biblioteca']['posterCandidates'][0]['status'],'reviewed')

if __name__=='__main__':unittest.main()
