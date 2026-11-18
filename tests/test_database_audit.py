import copy
import json
import sys
import unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_database import audit
import update
from adapters import organiser_sessions
NOW=datetime(2026,11,18,12,tzinfo=ZoneInfo('Europe/Lisbon'))

class PlaceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.places=json.loads((ROOT/'src/evergreenIdeas.json').read_text())
        self.by={p['id']:p for p in self.places}

    def test_all_places_reviewed_and_evidence_matches_tags(self):
        report=audit(self.places,{'events':[]},{})
        self.assertEqual(report['errors'],[])
        self.assertEqual(report['places']['reviewed'],14)
        self.assertEqual(report['places']['amenities']['playground']['confirmed'],10)
        for id in ['jardim-basilio','quinta-conceicao','parque-varas','parque-sao-mamede']:
            self.assertIn('playground',self.by[id]['types'])
            self.assertGreaterEqual(self.by[id]['amenities']['playground']['minMonths'],36)

    def test_unknown_is_not_absence_and_cafe_closure_is_not_available(self):
        self.assertEqual(self.by['jardim-botanico']['amenities']['playground']['status'],'unknown')
        self.assertEqual(self.by['quinta-santiago']['amenities']['playground']['status'],'unknown')
        self.assertEqual(self.by['parque-pasteleira']['amenities']['cafe']['status'],'temporarily-closed')
        self.assertIsNone(self.by['sea-life']['amenities']['playground'].get('minMonths'))
        self.assertEqual(self.by['sea-life']['amenities']['strollerAccess']['status'],'confirmed')

    def test_audit_catches_missing_evidence_and_stale_playground_tags(self):
        changed=copy.deepcopy(self.places)
        changed[0]['amenities']['playground'].pop('sourceUrl')
        changed[1]['types'].remove('playground')
        errors=audit(changed,{'events':[]},{})['errors']
        self.assertTrue(any('source evidence' in e for e in errors))
        self.assertTrue(any('disagrees' in e for e in errors))

class EventEnrichmentTests(unittest.TestCase):
    def test_explicit_music_room_and_purchase_interface_fill_indoor_and_booking(self):
        html=(ROOT/'tests/fixtures/music-programme.html').read_text()
        url='https://casadamusica.com/event/som-de-ca-e-de-la/'
        events=organiser_sessions(html,url,NOW,update.make_event)
        self.assertEqual(len(events),8)
        for e in events:
            self.assertTrue(e['indoor']);self.assertEqual(e['bookingUrl'],url)
            self.assertEqual(e['status'],'unverified')
            self.assertIsNone(e['end'])
            self.assertEqual(e['settingEvidence']['text'],'Sala Ensaio 2')

    def test_papi_price_capacity_and_counter_collection_need_explicit_text(self):
        html=(ROOT/'tests/fixtures/porto-papi.html').read_text()
        context=(ROOT/'tests/fixtures/porto-festival.html').read_text()
        url='https://www.bibliotecasdoporto.pt/evento/papi-opus-8-espetaculo/'
        # Same official public wording observed during the audit.
        extra='<p>Entrada gratuita (mediante levantamento de bilhete no balcão de informações da BMAG). Lotação: 20 crianças por sessão.</p>'
        html=html.replace('Duração:',extra+'Duração:')
        events=organiser_sessions(html,url,NOW,update.make_event,context)
        self.assertEqual(len(events),2)
        for e in events:
            self.assertEqual(e['price'],'Gratuito');self.assertEqual(e['capacity'],20)
            self.assertTrue(e['indoor']);self.assertIn('balcão',e['registrationNote'])
            self.assertEqual(e['registrationMethod'],'in-person-ticket')
            self.assertEqual(e['status'],'unverified');self.assertIsNone(e['bookingUrl'])
        changed=html.replace('Entrada gratuita','Entrada paga').replace('Lotação: 20 crianças','Lotação a confirmar')
        for e in organiser_sessions(changed,url,NOW,update.make_event,context):
            self.assertNotEqual(e['price'],'Gratuito');self.assertNotIn('registrationNote',e)
            self.assertIsNone(e['capacity'])

if __name__=='__main__':unittest.main()
