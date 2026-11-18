import copy
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
import update
from outings import collect,eligible,SERRALVES_MARKET,FERREIRA_MARKET,FAMA
NOW=datetime(2026,11,18,14,tzinfo=ZoneInfo('Europe/Lisbon'))
REGISTRY=json.loads((ROOT/'public/data/venues.json').read_text())
SERRALVES=(ROOT/'tests/fixtures/outings/serralves-market.html').read_text()
FERREIRA=(ROOT/'tests/fixtures/outings/ferreira-market.html').read_text()

class ChristmasMarketsTests(unittest.TestCase):
    def test_serralves_is_one_free_all_ages_visit_with_published_dates_and_hours(self):
        items,report=collect('serralves-christmas',lambda u:(SERRALVES,None),REGISTRY,NOW)
        self.assertEqual(len(items),1);o=items[0]
        self.assertEqual((o['validFrom'],o['validUntil']),('2026-12-05','2026-12-08'))
        self.assertIn('10:00–19:00',o['weekendHours']);self.assertIn('gratuita',o['price'])
        self.assertTrue(3<o['distanceKm']<4);self.assertTrue(eligible(o,REGISTRY,NOW))
        self.assertFalse(report['reviewNeeded']);self.assertNotIn('start',o);self.assertNotIn('end',o)
        self.assertEqual(collect('serralves-christmas',lambda u:(SERRALVES,None),REGISTRY,NOW.replace(month=12,day=9))[0],[])

    def test_missing_details_changed_year_or_cancellation_never_reuses_old_programme(self):
        for old,new in [('2026','2025'),('10:00 - 19:00','11:00 - 18:00'),('para todas as idades','para crianças a partir dos 3 anos'),('Acesso gratuito','Preço por confirmar'),('Mercado de Natal de Serralves','Mercado de Natal de Serralves cancelado')]:
            body=SERRALVES.replace(old,new)
            self.assertNotEqual(body,SERRALVES)
            items,report=collect('serralves-christmas',lambda u:(body,None),REGISTRY,NOW)
            self.assertEqual(items,[]);self.assertTrue(report['reviewNeeded'])

    def test_ferreira_period_boundary_times_do_not_become_daily_opening_hours(self):
        items,report=collect('ferreira-christmas',lambda u:(FERREIRA,None),REGISTRY,NOW)
        self.assertEqual(items,[]);self.assertTrue(report['reviewNeeded']);self.assertTrue(report['ok'])
        self.assertIn('Horário diário por confirmar',report['monitoringNote'])
        self.assertNotIn('14 nov 2026',collect('ferreira-christmas',lambda u:(FERREIRA.replace('2026-11-14','2025-11-14'),None),REGISTRY,NOW)[1]['monitoringNote'])

    def test_failure_and_unknown_admission_do_not_publish_a_market(self):
        self.assertFalse(collect('serralves-christmas',lambda u:(None,'HTTP 403'),REGISTRY,NOW)[1]['ok'])
        body='<main>Mercado de Natal de Matosinhos - FaMa 2026 De 27/Nov a 23/Dez Parque Basílio Teles FaMa Sr. de Matosinhos 2026 Mercado de Natal 2020 Entrada livre para todas as idades</main>'
        items,report=collect('matosinhos-christmas',lambda u:(body,None),REGISTRY,NOW)
        self.assertEqual(items,[]);self.assertTrue(report['reviewNeeded'])

    def test_scan_keeps_markets_out_of_the_timed_calendar_and_updates_without_duplicates(self):
        source={'name':'Serralves · Mercado de Natal','url':SERRALVES_MARKET,'type':'family-outings','adapter':'serralves-christmas'}
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)
            with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=(SERRALVES,None)):
                r,e,h,*_=update.scan([source],{},{},NOW)
                self.assertEqual(e['events'],[]);self.assertEqual(len(e['outings']),1)
                (data/'events.json').write_text(json.dumps(e))
                _,again,*_=update.scan([source],r,h,NOW)
                self.assertEqual(len(again['outings']),1)
