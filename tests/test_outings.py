import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update
from outings import collect,eligible,SEA_HOURS,SEA_AGES,MAIA_MARKET,ZOO
NOW=datetime(2026,11,16,14,tzinfo=ZoneInfo('Europe/Lisbon'))
REGISTRY=json.loads((ROOT/'public/data/venues.json').read_text())
PAGES={u:(ROOT/'tests/fixtures/outings'/file).read_text() for u,file in [(SEA_HOURS,'sea-en.html'),(SEA_AGES,'sea-faq.html'),(MAIA_MARKET,'maia-market.html')]}

class OpeningHoursTests(unittest.TestCase):
    def fetch(self,u):return PAGES[u],None
    def test_aquarium_is_one_outing_not_twelve_fake_sessions(self):
        items,report=collect('sealife',self.fetch,REGISTRY,NOW)
        self.assertEqual(len(items),1);item=items[0]
        self.assertTrue(eligible(item,REGISTRY,NOW))
        self.assertNotIn('date',item);self.assertNotIn('start',item);self.assertNotIn('end',item)
        self.assertIn('10:00–19:00',item['weekendHours'])
        self.assertIn('por confirmar',item['price'])
        self.assertTrue(3<item['distanceKm']<5)
        self.assertFalse(report['reviewNeeded'])

    def test_market_uses_current_year_and_published_access_conditions(self):
        items,report=collect('maia-christmas',self.fetch,REGISTRY,NOW)
        self.assertEqual(len(items),1);item=items[0]
        self.assertEqual((item['validFrom'],item['validUntil']),('2026-11-27','2027-01-03'))
        self.assertIn('10:00–24:00',item['weekendHours'])
        self.assertIn('Artesanato até 24',item['note'])
        self.assertIn('Pista de gelo',item['note'])
        self.assertIn('gratuita',item['price'])
        self.assertTrue(5<item['distanceKm']<6)
        self.assertEqual(collect('maia-christmas',self.fetch,REGISTRY,NOW.replace(year=2027))[0],[])

    def test_missing_ages_changed_hours_and_old_programmes_are_not_published(self):
        for adapter,url,old,new in [('sealife',SEA_AGES,'adequado para visitantes de todas as idades','para crianças a partir de 3 anos'),('sealife',SEA_HOURS,'10 am to 7 pm','11 am to 6 pm'),('maia-christmas',MAIA_MARKET,'2026','2025'),('maia-christmas',MAIA_MARKET,'Para todas as idades','Dos 3 aos 12 anos')]:
            pages=dict(PAGES);pages[url]=pages[url].replace(old,new)
            result,report=collect(adapter,lambda u:(pages[u],None),REGISTRY,NOW)
            self.assertEqual(result,[],(adapter,old))
            self.assertTrue(report['reviewNeeded'])

    def test_age_price_or_source_failures_remain_pending(self):
        for adapter in ['zoo-maia','matosinhos-christmas']:
            self.assertEqual(collect(adapter,lambda u:('<main>Informação incompleta</main>',None),REGISTRY,NOW)[0],[])
        items,report=collect('sealife',lambda u:(None,'HTTP 403'),REGISTRY,NOW)
        self.assertFalse(report['ok']);self.assertTrue(report['reviewNeeded']);self.assertEqual(items,[])

    def test_revalidation_requires_fresh_evidence_exact_location_and_upcoming_weekend(self):
        item=collect('sealife',self.fetch,REGISTRY,NOW)[0][0]
        for fields in [{'checkedAt':(NOW-timedelta(hours=49)).isoformat()},{'checkedAt':(NOW+timedelta(hours=1)).isoformat()},{'admission':'unknown'},{'venue':'Porto'},{'evidenceUrls':['https://example.org']},{'validFrom':'2026-11-16','validUntil':'2026-11-20'}]:
            changed=copy.deepcopy(item);changed.update(fields)
            self.assertFalse(eligible(changed,REGISTRY,NOW),fields)

    def test_scan_replaces_outings_and_never_adds_them_as_timed_events(self):
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory)
            sources=[{'name':'SEA LIFE Porto','url':SEA_HOURS,'type':'family-outings','adapter':'sealife'}]
            with patch.object(update,'DATA',data),patch.object(update,'fetch',side_effect=self.fetch):
                first,events,*_=update.scan(sources,{}, {},NOW)
                self.assertEqual(len(events['outings']),1);self.assertEqual(events['events'],[])
                (data/'events.json').write_text(json.dumps(events))
                _,events,*_=update.scan(sources,first, {},NOW)
                self.assertEqual(len(events['outings']),1)
            with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=(None,'HTTP 403')):
                _,events,*_=update.scan(sources,first, {},NOW)
                self.assertEqual(events['outings'],[])

if __name__=='__main__':unittest.main()
