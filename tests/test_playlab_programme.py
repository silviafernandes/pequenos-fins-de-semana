import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update
from playlab import collect_programme, parse_choice, WEEKEND_FORM
from eligibility import assess
NOW=datetime(2026,11,16,12,tzinfo=ZoneInfo('Europe/Lisbon'))
PROGRAMME=json.loads((ROOT/'public/data/playlab-programme.json').read_text())
REGISTRY=json.loads((ROOT/'public/data/venues.json').read_text())

class ReviewedProgrammeTests(unittest.TestCase):
    def collect(self,p=None,html=None,error='HTTP 401',now=NOW):
        return collect_programme(p or PROGRAMME,html,error,now,update.make_event)

    def test_eight_future_sessions_with_real_times_ages_and_prices(self):
        events,report=self.collect()
        self.assertEqual(len(events),8)
        self.assertEqual(report['reviewedSessions'],8)
        self.assertTrue(report['reviewNeeded'])
        self.assertEqual([(e['date'],e['start'],e['end'],e['minMonths'],e['maxMonths']) for e in events],[
            ('2026-11-22','10:00','10:50',0,72),('2026-11-28','09:30','10:10',6,18),('2026-11-28','10:30','11:15',19,36),('2026-11-29','10:00','11:00',24,72),('2026-12-06','10:00','11:00',8,36),('2026-12-12','10:00','10:45',6,18),('2026-12-12','11:00','11:30',24,72),('2026-12-13','10:00','11:00',24,72)])
        for e in events:
            self.assertEqual(assess(e,REGISTRY,NOW)['validationStatus'],'verified')
            self.assertEqual(e['price'],'18 EUR' if 'Messy Play' in e['title'] else '15 EUR')
            self.assertEqual(e['status'],'unverified')
            self.assertEqual(e['bookingUrl'],WEEKEND_FORM)
        self.assertNotIn('teatro',' '.join(e['title'] for e in events).lower())

    def test_review_survives_48_hours_without_falsifying_checked_at(self):
        later=NOW+timedelta(days=5)
        events,_=self.collect(now=later)
        for e in events:
            self.assertEqual(e['sessionEvidence']['checkedAt'],PROGRAMME['reviewedAt'])
            self.assertEqual(assess(e,REGISTRY,later)['validationStatus'],'verified')
        self.assertEqual(self.collect(now=NOW+timedelta(days=29))[0],[])

    def test_invalid_or_tampered_review_is_rejected(self):
        events,_=self.collect()
        for field,value in [('reviewDigest','wrong'),('validUntil','2027-12-31'),('reviewedAt','2026-11-30T12:00:00+00:00')]:
            e=copy.deepcopy(events[0]);e['sessionEvidence'][field]=value
            self.assertEqual(assess(e,REGISTRY,NOW)['validationStatus'],'pending')

    def test_public_options_import_new_sessions_and_remove_missing_ones(self):
        new='Baby Lab de Natal, 6-18 meses/months - Sáb. 19/12, 10:00-10:45'
        # A later programme needs an explicit new reviewed window; no silent extension.
        self.assertIsNotNone(parse_choice(new,2026))
        self.assertIsNone(parse_choice(new.replace('-10:45',''),2026)['end'])
        html='<div role="checkbox" data-answer-value="Babyoga de Outono, 6-18 meses/months - Sáb. 28/11 9:30-10:10"></div>'
        events,report=self.collect(html=html,error=None)
        self.assertEqual(len(events),1)
        self.assertEqual(report['liveSessions'],1)
        self.assertFalse(report['reviewNeeded'])
        self.assertEqual(events[0]['sessionEvidence']['kind'],'official-programme')
        self.assertEqual(events[0]['price'],'Por confirmar')
        self.assertEqual(assess(events[0],REGISTRY,NOW)['validationStatus'],'verified')
        self.assertEqual(self.collect(html=f'<div role="checkbox" data-answer-value="{new}"></div>',error=None)[1]['reviewNeeded'],True)

    def test_invalid_weekday_and_incomplete_options_require_review(self):
        label=PROGRAMME['choices'][3]
        self.assertIsNone(parse_choice(label.replace('22/11','23/11'),2026))
        self.assertIsNone(parse_choice(label.replace('0-6 anos','3 anos'),2026))
        events,report=self.collect(html='<div role="checkbox" data-answer-value="Detalhes em breve"></div>',error=None)
        self.assertEqual(len(events),8)
        self.assertTrue(report['reviewNeeded'])

    def test_daily_scan_keeps_reviewed_sessions_when_all_web_pages_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder);(data/'playlab-programme.json').write_text(json.dumps(PROGRAMME))
            with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=(None,'HTTP 401')):
                result,events,*_=update.scan([{'name':'PlayLab Porto','url':'https://playlabporto.beehiiv.com/'}],{}, {},NOW)
                self.assertEqual(len(events['events']),8)
                (data/'events.json').write_text(json.dumps(events))
                again,events,*_=update.scan([{'name':'PlayLab Porto','url':'https://playlabporto.beehiiv.com/'}],result, {},NOW+timedelta(days=3))
                self.assertEqual(len(events['events']),8)
                self.assertEqual(again['sourceIndex']['PlayLab Porto']['reviewedSessions'],8)

if __name__=='__main__':unittest.main()
