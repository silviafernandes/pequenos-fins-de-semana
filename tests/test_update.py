import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update

class ParsingTests(unittest.TestCase):
    def test_age_exact(self):
        self.assertEqual(update.age_band('6–36 meses'),(6,36))
        self.assertEqual(update.age_band('12 meses a 3 anos'),(12,36))
        self.assertEqual(update.age_band('0-3 anos'),(0,36))
        self.assertEqual(update.age_band('2 a 6 anos'),(24,72))
        self.assertEqual(update.age_band('18-36 meses'),(18,36))
        self.assertIsNone(update.age_band('atividades familiares'))
    def test_opening_date(self):
        html='<p>Inscrições abrem no dia 13 de novembro às 10h00.</p>'
        self.assertEqual(update.opening_dates(html,2026),['2026-11-13T10:00+00:00'])
    def test_link_filter(self):
        self.assertTrue(update.possible_link('https://example.org/evento/bebeteca-magica','Bebeteca Mágica para bebés'))
        self.assertFalse(update.possible_link('https://example.org/contactos','Contactos e privacidade'))
    def test_json_ld(self):
        html='<script type="application/ld+json">{"@graph":[{"@type":"Event","name":"Oficina de música para bebés"}]}</script>'
        _,soup=update.links_from(html,'https://www.example.org')
        self.assertEqual(len(update.extract_json_ld(soup)),1)
    def test_make_event_sufficient_data(self):
        item={'@type':'Event','name':'Música para bebés 12-36 meses','description':'Oficina musical para bebés de 12 a 36 meses',
            'startDate':'2026-11-15T10:00:00+00:00','endDate':'2026-11-15T11:00:00+00:00',
            'location':{'name':'Oficina Porto','address':{'addressLocality':'Porto'}},'url':'https://example.org/oficina'}
        now=datetime(2026,11,9,10,0,tzinfo=ZoneInfo('Europe/Lisbon'))
        e=update.make_event(item,'https://example.org','Exemplo',now)
        self.assertEqual(e['status'],'unverified')
        self.assertEqual(e['start'],'10:00')
        self.assertEqual(e['maxMonths'],36)
        bad=dict(item);bad['name']='Oficina para adultos';bad['description']='Pintura para 8–12 anos'
        self.assertIsNone(update.make_event(bad,'https://example.org','Exemplo',now))

if __name__=='__main__':unittest.main()
