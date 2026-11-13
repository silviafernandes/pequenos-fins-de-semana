"""Regressions for programme changes and bounded discovery coverage."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update
from adapters import organiser_sessions

NOW=datetime(2026,11,13,12,tzinfo=ZoneInfo('Europe/Lisbon'))
URL='https://www.oficinajosefina.com/beb%C3%A9s'

class ProgrammeCoverageTests(unittest.TestCase):
    def setUp(self):
        self.html=(ROOT/'tests/fixtures/josefina-season-2026-27.html').read_text()

    def test_season_heading_recovers_upcoming_sessions(self):
        events=organiser_sessions(self.html,URL,NOW,update.make_event)
        self.assertEqual(len(events),7)
        self.assertEqual([(e['date'],e['start'],e['end']) for e in events if e['title']=='Experimentar Cerâmicas'],[
            ('2026-11-15','10:00','11:00'),('2026-11-29','10:00','11:00'),('2026-12-13','10:00','11:00'),('2026-12-27','10:00','10:45')])
        self.assertEqual({e['title']:e['minMonths'] for e in events},{'Experimentar Cerâmicas':12,'Experimentar Pinturas':9,'Experimentar Luzes':12})

    def test_invisible_publisher_spacing_does_not_hide_a_session(self):
        html=self.html.replace('27 Dez . 10h-10h45','27 Dez . \u200b 10h-10h45')
        events=organiser_sessions(html,URL,NOW,update.make_event)
        self.assertIn(('2026-12-27','10:45'),[(e['date'],e['end']) for e in events])

    def test_explicit_year_labels_do_not_create_wrong_year_sessions(self):
        # Each workshop's 2027 dates stay in 2027, including November/December.
        events=organiser_sessions(self.html,URL,NOW,update.make_event)
        self.assertNotIn('2026-11-07',{e['date'] for e in events})
        self.assertNotIn('2026-12-05',{e['date'] for e in events})
        self.assertEqual(len(events),7)

    def test_january_rollover_uses_published_year_and_duration(self):
        now=datetime(2027,1,5,12,tzinfo=NOW.tzinfo)
        events=organiser_sessions(self.html,URL,now,update.make_event)
        lights=[e for e in events if e['title']=='Experimentar Luzes']
        self.assertEqual([(e['date'],e['start'],e['end']) for e in lights],[('2027-01-17','11:30','12:30')])
        self.assertTrue(all(e['date'].startswith('2027-') for e in events))

    def test_missing_or_nonconsecutive_season_stays_unverified(self):
        for text in ['Oficinas para Bebés','Oficinas para Bebés 26/29']:
            self.assertEqual(organiser_sessions(self.html.replace('Oficinas para Bebés 26/27',text),URL,NOW,update.make_event),[])

class StructuredCoverageTests(unittest.TestCase):
    def test_reads_itemlist_and_subevents_without_duplicating_graphs(self):
        data={'@graph':[{'@type':'ItemList','itemListElement':[{'@type':'ListItem','item':{'@type':'Event','name':'Baby workshop','subEvent':[{'@type':'Event','name':'Second session'}]}}]}]}
        soup=BeautifulSoup('<script type="application/ld+json">'+json.dumps(data)+'</script>','html.parser')
        self.assertCountEqual([e['name'] for e in update.extract_json_ld(soup)],['Baby workshop','Second session'])

class CrawlCoverageTests(unittest.TestCase):
    def test_known_pages_do_not_starve_new_pages_and_next_scan_rotates(self):
        root='https://www.bibliotecasearquivosmatosinhos.pt/'
        source={'name':'Biblioteca','url':root}
        known=[{'id':str(n),'sourceUrl':root+'evento-44/known-'+str(n),'title':'Bebeteca para bebés '+str(n),'date':'2026-11-21','minMonths':6,'maxMonths':36} for n in range(12)]
        new=[root+'evento-44/new-'+str(n) for n in range(4)]
        html='<main>'+''.join('<a href="'+u+'">Bebeteca para bebés '+str(n)+'</a>' for n,u in enumerate(new))+'</main>'
        def fetch(url):return (html if url==root else '<main>Detalhes por publicar</main>',None)
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory);(data/'events.json').write_text(json.dumps({'events':known}))
            with patch.object(update,'DATA',data),patch.object(update,'fetch',side_effect=fetch),patch.object(update.time,'sleep'):
                result,events,history,_,_=update.scan([source],{}, {},NOW)
                status=result['sourceIndex']['Biblioteca']
                self.assertEqual(status['detailsChecked'],12)
                self.assertEqual(status['candidateLinks'],16)
                self.assertTrue(status['truncated'])
                self.assertEqual(len(set(status['lastLinks'])&set(new)),3)
                (data/'events.json').write_text(json.dumps(events))
                second,_,_,_,_=update.scan([source],result,history,NOW)
                self.assertIn(new[3],second['sourceIndex']['Biblioteca']['lastLinks'])
                self.assertLessEqual(second['sourceIndex']['Biblioteca']['detailsChecked'],12)

if __name__=='__main__':unittest.main()
