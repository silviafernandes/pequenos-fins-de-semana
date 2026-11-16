import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update
from eligibility import mark_session
NOW=datetime(2026,11,16,12,tzinfo=ZoneInfo('Europe/Lisbon'))
URL='https://www.oficinajosefina.com/beb%C3%A9s'
RAW={'name':'Oficina para bebés','description':'Bebés dos 6 aos 36 meses','startDate':'2026-11-21T10:00:00','endDate':'2026-11-21T11:00:00','location':{'name':'Oficina Josefina','address':'Avenida de Camilo 224, Porto'},'url':URL}

class FirstAddedTests(unittest.TestCase):
    def run_scan(self,data,now=NOW,previous=None):
        def parse(*args):return [mark_session(update.make_event(RAW,URL,'Oficina Josefina',now),URL,now,'official-programme')]
        with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=('<main/>',None)),patch.object(update,'organiser_sessions',side_effect=parse),patch.object(update.time,'sleep'):
            return update.scan([{'name':'Oficina Josefina','url':URL}],previous or {},{},now)

    def test_new_admission_is_not_renewed_on_recheck(self):
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder);previous,events,*_=self.run_scan(data)
            event=events['events'][0];self.assertEqual(event['addedAt'],NOW.isoformat())
            (data/'events.json').write_text(json.dumps(events))
            _,events,*_=self.run_scan(data,NOW+timedelta(days=2),previous)
            self.assertEqual(events['events'][0]['addedAt'],event['addedAt'])

    def test_backfill_uses_matching_published_session_not_page_or_other_time(self):
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder);_,events,*_=self.run_scan(data)
            event=events['events'][0];event.pop('addedAt')
            (data/'events.json').write_text(json.dumps(events))
            lead={**event,'url':URL,'firstSeen':'2026-11-10T12:00:00+00:00'}
            previous={'discoveries':[dict(lead,start='11:00',firstSeen='2026-10-01T12:00:00+00:00'),lead]}
            _,result,*_=self.run_scan(data,previous=previous)
            self.assertEqual(result['events'][0]['addedAt'],lead['firstSeen'])

    def test_unknown_existing_history_stays_unknown_and_pending_admission_is_new(self):
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder);_,events,*_=self.run_scan(data)
            events['events'][0].pop('addedAt')
            (data/'events.json').write_text(json.dumps(events))
            _,result,*_=self.run_scan(data)
            self.assertIsNone(result['events'][0]['addedAt'])
            (data/'events.json').write_text(json.dumps(result))
            previous,result,*_=self.run_scan(data,NOW+timedelta(days=1))
            (data/'events.json').write_text(json.dumps(result))
            _,result,*_=self.run_scan(data,NOW+timedelta(days=2),previous)
            self.assertIsNone(result['events'][0]['addedAt'])
            events['events'][0]['validationStatus']='pending'
            (data/'events.json').write_text(json.dumps(events))
            _,result,*_=self.run_scan(data)
            self.assertEqual(result['events'][0]['addedAt'],NOW.isoformat())

if __name__=='__main__':unittest.main()
