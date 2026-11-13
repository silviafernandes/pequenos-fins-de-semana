import json
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update
from playlab import AGENDA, WEEKEND_FORM, WEEKEND_SHORT, programme_links, weekend_form
from eligibility import assess, mark_session
NOW=datetime(2026,11,13,12,tzinfo=ZoneInfo('Europe/Lisbon'))
ROOT_URL='https://playlabporto.beehiiv.com/'
POST=ROOT_URL+'p/outubro-no-playlab'

class PlaylabTests(unittest.TestCase):
    def test_monthly_issue_without_baby_keyword_is_discovered(self):
        html=f'<a href="{POST}">Outubro no PlayLab</a><a href="https://other.beehiiv.com/p/test">Bebés</a>'
        self.assertEqual(programme_links(html,ROOT_URL),[(POST,'Outubro no PlayLab')])
        self.assertEqual(programme_links(html,'https://other.beehiiv.com/'),[])

    def test_expansion_requires_current_official_agenda_link(self):
        html=f'<a href="https://www.google.com/url?q={WEEKEND_SHORT}">Inscrição</a>'
        self.assertEqual(weekend_form(html,AGENDA),WEEKEND_FORM)
        self.assertIsNone(weekend_form(html,ROOT_URL))
        self.assertIsNone(weekend_form(html.replace(WEEKEND_SHORT,'https://forms.gle/new'),AGENDA))

    def test_scan_checks_agenda_and_reports_private_form_without_inventing_events(self):
        pages={ROOT_URL:f'<a href="{POST}">Outubro no PlayLab</a>'+''.join(f'<a href="{ROOT_URL}p/archive-{i}">Arquivo</a>' for i in range(20)),POST:'Baby Yoga — Outubro. Dos 2 meses aos 4 anos.',AGENDA:f'<a href="{WEEKEND_SHORT}">Inscrição ao fim de semana</a>'}
        def fetch(url):return (None,'HTTP 401') if url==WEEKEND_FORM else (pages.get(url,'Arquivo antigo'),None)
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(update,'DATA',Path(folder)),patch.object(update,'fetch',side_effect=fetch) as mocked,patch.object(update.time,'sleep'):
                result,events,_,messages,_=update.scan([{'name':'PlayLab Porto','url':ROOT_URL,'programmeUrls':[AGENDA]}],{}, {},NOW)
        report=result['sourceIndex']['PlayLab Porto']
        self.assertLessEqual(report['detailsChecked'],12)
        self.assertIn(AGENDA,report['lastLinks'])
        self.assertIn({'url':WEEKEND_FORM,'error':'HTTP 401'},report['detailErrors'])
        self.assertEqual(report['parsedSessions'],0)
        self.assertEqual(events['events'],[])
        self.assertEqual(messages,[])
        self.assertEqual(sum(c.args[0]==AGENDA for c in mocked.call_args_list),1)

    def test_exact_venue_and_google_sites_scope(self):
        registry=json.loads((ROOT/'public/data/venues.json').read_text())
        for url,expected in [(AGENDA,'verified'),(ROOT_URL+'p/novembro','verified'),('https://sites.google.com/view/someone-else/agenda','pending'),('https://sites.google.com/view/playlabporto-fake/agenda','pending')]:
            e={'title':'Baby Yoga','date':'2026-11-14','start':'10:00','end':None,'minMonths':2,'maxMonths':48,'venue':'PlayLab Porto'}
            mark_session(e,url,NOW,'official-programme');assess(e,registry,NOW)
            self.assertEqual(e['validationStatus'],expected)
            self.assertTrue(4<e['distanceKm']<5)

if __name__=='__main__':unittest.main()
