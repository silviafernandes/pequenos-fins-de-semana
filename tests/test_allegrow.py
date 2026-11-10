import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update
import allegrow
from eligibility import assess,mark_session

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'tests/fixtures'
LISTING=json.loads((FIXTURES/'allegrow-public-list.json').read_text())
DETAIL=json.loads((FIXTURES/'allegrow-activity.json').read_text())
NOW=datetime(2026,11,10,10,tzinfo=ZoneInfo('Europe/Lisbon'))
REGISTRY=json.loads((ROOT/'public/data/venues.json').read_text())

class AllegrowTests(unittest.TestCase):
    def read_public(self,url):
        if url==allegrow.LIST_URL:return copy.deepcopy(LISTING),None
        if url==allegrow.LIST_URL+'/'+DETAIL['id']:return copy.deepcopy(DETAIL),None
        self.fail('Unexpected request: '+url)

    def test_reads_explicit_public_slots_not_general_duration_or_spots(self):
        report=allegrow.collect(self.read_public,NOW,update.make_event)
        self.assertTrue(report['ok'])
        self.assertEqual((report['activitiesChecked'],report['detailsChecked']),(4,1))
        events=report['pages'][allegrow.WEB_BASE+DETAIL['id']]
        self.assertEqual(len(events),1)
        event=events[0]
        self.assertEqual((event['date'],event['start'],event['end']),('2026-11-14','11:00','12:00'))
        self.assertEqual((event['minMonths'],event['maxMonths']),(24,84))
        self.assertEqual(event['status'],'unverified')
        self.assertEqual(event['sessionEvidence']['partnerId'],DETAIL['partner']['id'])
        self.assertEqual(assess(event,REGISTRY,NOW)['validationStatus'],'pending')

    def test_complete_age_bounds_required_and_three_year_minimum_rejected(self):
        self.assertEqual(allegrow.age_range_months('6m - 4y'),(6,48))
        self.assertEqual(allegrow.age_range_months('0m - 16y'),(0,192))
        for age in ['0m','1m','3 years','-1m - 3y',None]:
            self.assertIsNone(allegrow.age_range_months(age))
        item=copy.deepcopy(DETAIL);item['age_range']='3y - 7y'
        self.assertEqual(allegrow.parse_activity(item,NOW,update.make_event),[])

    def test_weekdays_missing_timezone_and_cancelled_slots_are_not_promoted(self):
        weekday=next(a for a in LISTING if a['title']=='Playdate Mãe Folha')
        self.assertEqual(allegrow.parse_activity(weekday,NOW,update.make_event),[])
        for changes in [{'status':'cancelled'},{'start_time':'2026-11-14T11:00:00'}]:
            item=copy.deepcopy(DETAIL);item['schedules'][0].update(changes)
            self.assertEqual(allegrow.parse_activity(item,NOW,update.make_event),[])

    def test_missing_end_never_uses_activity_duration(self):
        item=copy.deepcopy(DETAIL);item['duration']='4 days';item['schedules'][0].pop('end_time')
        self.assertIsNone(allegrow.parse_activity(item,NOW,update.make_event)[0]['end'])

    def test_api_shape_error_and_detail_failure_are_visible(self):
        report=allegrow.collect(lambda url:({'activities':[]},None),NOW,update.make_event)
        self.assertFalse(report['ok']);self.assertIn('Formato',report['error'])
        def failed(url):return (copy.deepcopy(LISTING),None) if url==allegrow.LIST_URL else (None,'HTTP 503')
        report=allegrow.collect(failed,NOW,update.make_event)
        self.assertTrue(report['ok']);self.assertEqual(len(report['detailErrors']),1)
        self.assertNotIn(allegrow.WEB_BASE+DETAIL['id'],report['pages'])

    def test_detail_id_must_match_requested_activity(self):
        def wrong(url):
            if url==allegrow.LIST_URL:return copy.deepcopy(LISTING),None
            item=copy.deepcopy(DETAIL);item['id']='unrelated'
            return item,None
        report=allegrow.collect(wrong,NOW,update.make_event)
        self.assertEqual(len(report['detailErrors']),1)
        self.assertNotIn(allegrow.WEB_BASE+DETAIL['id'],report['pages'])

    def test_provider_booking_trust_requires_reviewed_venue_partner_and_address(self):
        registry=copy.deepcopy(REGISTRY)
        event={'title':'Oficina','date':'2026-11-14','start':'11:00','end':None,'minMonths':24,'maxMonths':84,'venue':'Oficina Josefina','sourceUrl':allegrow.WEB_BASE+DETAIL['id'],'allegrowPartnerId':DETAIL['partner']['id'],'locationAddress':'Avenida de Camilo 224'}
        mark_session(event,event['sourceUrl'],NOW,'provider-booking')
        event['sessionEvidence'].update(partnerId=event['allegrowPartnerId'],address=event['locationAddress'])
        self.assertEqual(assess(copy.deepcopy(event),registry,NOW)['validationStatus'],'pending')
        # Synthetic binding tests the gate; no such permission is added to the real catalogue.
        registry['venues']['josefina']['bookingPublishers']=[{'host':'allegrowkids.pt','partnerId':event['allegrowPartnerId'],'address':event['locationAddress']}]
        self.assertEqual(assess(copy.deepcopy(event),registry,NOW)['validationStatus'],'verified')
        changed=copy.deepcopy(event);changed['allegrowPartnerId']='another-provider'
        self.assertEqual(assess(changed,registry,NOW)['validationStatus'],'pending')
        changed=copy.deepcopy(event);changed['locationAddress']='Another street 99'
        self.assertEqual(assess(changed,registry,NOW)['validationStatus'],'pending')

    def test_scan_keeps_unverified_venue_pending_and_reports_source_results(self):
        source={'name':'Allegrow Kids','url':'https://allegrowkids.pt/pt/','type':'allegrow-public'}
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory);(data/'events.json').write_text(json.dumps({'events':[]}))
            with patch.object(update,'DATA',data),patch.object(update,'fetch_json',side_effect=self.read_public):
                discoveries,events,_,_,_=update.scan([source],{}, {},NOW)
        self.assertEqual(events['events'],[])
        self.assertEqual(len(events['pendingEvents']),1)
        self.assertEqual(discoveries['discoveries'],[])
        stats=discoveries['sourceIndex']['Allegrow Kids']
        self.assertEqual((stats['activitiesChecked'],stats['eligibleSessions'],stats['pendingSessions']),(4,0,1))
        self.assertEqual(stats['readMode'],'public-json')

    def test_removed_activity_withdraws_its_evidence_without_touching_other_sources(self):
        event=allegrow.parse_activity(copy.deepcopy(DETAIL),NOW,update.make_event)[0]
        primary={'id':'primary','title':'Oficina para bebés','date':'2026-11-14','start':'10:00','end':None,'minMonths':0,'maxMonths':36,'venue':'Oficina Josefina','sourceUrl':'https://www.oficinajosefina.com/beb%C3%A9s'}
        mark_session(primary,primary['sourceUrl'],NOW,'official-programme')
        source={'name':'Allegrow Kids','url':'https://allegrowkids.pt/pt/','type':'allegrow-public'}
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory);(data/'events.json').write_text(json.dumps({'events':[primary,event]}))
            with patch.object(update,'DATA',data),patch.object(update,'fetch_json',return_value=([],None)):
                _,events,_,_,_=update.scan([source],{}, {},NOW)
        self.assertEqual([e['id'] for e in events['events']],['primary'])
        self.assertNotIn('sessionEvidence',events['pendingEvents'][0])

    def test_detail_request_limit_is_reported_as_partial(self):
        with patch.object(allegrow,'MAX_DETAILS',0):
            report=allegrow.collect(self.read_public,NOW,update.make_event)
        self.assertTrue(report['truncated'])
        self.assertEqual(report['detailsChecked'],0)
        self.assertNotIn(allegrow.WEB_BASE+DETAIL['id'],report['pages'])

if __name__=='__main__':unittest.main()
