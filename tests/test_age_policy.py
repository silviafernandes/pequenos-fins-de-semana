import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update

class UnderThreeTests(unittest.TestCase):
    def test_explicit_lower_bounds_and_ranges(self):
        for text in ['A partir dos 3 anos','a partir de 3 anos','3–10 anos','3 a 6 anos','+3 anos','3+ anos','3 anos +','3+','M/3','a partir dos 36 meses','36–48 meses','maiores de 3 anos']:
            with self.subTest(text=text):
                self.assertTrue(update.excludes_under_three(text))
                self.assertIsNone(update.qualify_discovery({'title':text,'id':'older'}))
                self.assertFalse(update.possible_link('https://example.org/evento/historias','Histórias para crianças '+text))
        for text in ['0–3 anos','6–36 meses','18–36 meses','2–6 anos','a partir dos 2 anos','0–6 meses']:
            with self.subTest(text=text):
                self.assertFalse(update.excludes_under_three(text))
                self.assertIsNotNone(update.qualify_discovery({'title':text,'id':'younger'}))

    def test_expired_announcements_are_removed(self):
        with patch.object(update,'now_pt',return_value=datetime(2026,11,9,tzinfo=ZoneInfo('Europe/Lisbon'))):
            self.assertIsNone(update.qualify_discovery({'title':'Natureza SEX 16 OUT 0–10 anos'}))

    def test_unknown_age_is_not_a_recommendation(self):
        for title in ['Hora do Conto','Atividade para famílias','Música para bebés']:
            self.assertIsNone(update.qualify_discovery({'title':title}))

    def test_old_or_contradictory_metadata_cannot_override_older_title(self):
        self.assertIsNone(update.qualify_discovery({'title':'Histórias: a partir dos 3 anos','minMonths':12,'maxMonths':36,'ageEvidence':'structured-event'}))

    def test_event_minimum_is_exclusive(self):
        now=datetime(2026,11,9,tzinfo=ZoneInfo('Europe/Lisbon'))
        for band in ['3–6 anos','a partir dos 3 anos','36–48 meses']:
            self.assertIsNone(update.make_event({'name':'Histórias para crianças '+band,'location':'Porto','startDate':'2026-11-14T10:00'},'https://example.org/evento','Example',now))

    def test_scan_removes_previously_collected_older_and_unknown_announcements(self):
        previous={'discoveries':[{'id':'bad','title':'Contamos contigo! A partir dos 3 anos','firstSeen':'2026-11-09'}, {'id':'unknown','title':'Hora do conto para famílias','firstSeen':'2026-11-09'}, {'id':'good','title':'Música para bebés 0–3 anos','firstSeen':'2026-11-09'}]}
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory);(data/'events.json').write_text(json.dumps({'events':[]}))
            with patch.object(update,'DATA',data):
                result,_,_,_,_=update.scan([],previous,{},datetime(2026,11,9,tzinfo=ZoneInfo('Europe/Lisbon')))
        self.assertEqual([d['id'] for d in result['discoveries']],['good'])
        self.assertEqual(result['discoveries'][0]['minMonths'],0)
        self.assertEqual(result['discoveries'][0]['maxMonths'],36)
