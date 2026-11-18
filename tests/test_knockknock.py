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
import knockknock as knock
from eligibility import assess
NOW=datetime(2026,11,18,12,tzinfo=ZoneInfo('Europe/Lisbon'))
ID='c_test@group.calendar.google.com'
FRAME='<iframe src="https://calendar.google.com/calendar/embed?src=c_test%40group.calendar.google.com&amp;ctz=Europe%2FLisbon"></iframe>'
HTML='<div data-react-component="creator_ui/section_adapters/Text" data-props=\''+json.dumps({'text':FRAME})+'\'></div>'

def event(uid='one',start='20261122T100000Z',extra='',age='Dos 8 meses aos 5 anos',location='Knock-Knock · Family Club'):
    return f'BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTART:{start}\r\nSUMMARY:Little Atelier\r\nDESCRIPTION:{age}\r\nLOCATION:{location}\r\n{extra}END:VEVENT\r\n'

def calendar(events):return 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nX-WR-TIMEZONE:Europe/Lisbon\r\n'+events+'END:VCALENDAR\r\n'

class KnockCalendarTests(unittest.TestCase):
    def collect(self,text):return knock.collect(HTML,lambda u:(text,None),NOW,update.make_event)

    def test_podia_embed_binds_only_a_public_group_calendar(self):
        self.assertEqual(knock.calendar_id(HTML),ID)
        for html in [HTML.replace('calendar.google.com','evil.example'),HTML.replace('/calendar/embed','/private'),HTML.replace('c_test%40group.calendar.google.com','personal%40gmail.com')]:
            self.assertIsNone(knock.calendar_id(html))
        self.assertEqual(knock.calendar_id('<div data-react-component="creator_ui/section_adapters/Text" data-props="broken"></div>'),None)

    def test_recurrences_exclusions_moved_and_cancelled_occurrences(self):
        master=event(extra='RRULE:FREQ=WEEKLY;COUNT=4\r\nEXDATE:20261129T100000Z\r\n')
        moved=event(start='20261205T110000Z',extra='RECURRENCE-ID:20261206T100000Z\r\n')
        cancelled=event(start='20261213T100000Z',extra='RECURRENCE-ID:20261213T100000Z\r\nSTATUS:CANCELLED\r\n')
        events,report=self.collect(calendar(master+moved+cancelled))
        self.assertEqual([(e['date'],e['start']) for e in events],[('2026-11-22','10:00'),('2026-12-05','11:00')])
        self.assertTrue(report['ok']);self.assertEqual(report['parsedSessions'],2)
        registry=json.loads((ROOT/'public/data/venues.json').read_text())
        self.assertTrue(all(assess(e,registry,NOW)['validationStatus']=='verified' for e in events))
        self.assertTrue(all(e['status']=='unverified' and e['end'] is None for e in events))

    def test_explicit_ages_and_location_required_no_general_club_policy(self):
        rows=event(uid='no-age',age='Playtime para famílias')+event(uid='older',age='Dos 3 aos 6 anos')+event(uid='outside',location='Jardim público')
        events,report=self.collect(calendar(rows))
        self.assertEqual(events,[]);self.assertEqual(len(report['calendarIssues']),3);self.assertTrue(report['reviewNeeded'])
        self.assertEqual(self.collect(calendar(event(start='20261122',extra='')))[0],[])

    def test_empty_valid_feed_is_not_a_failed_read_and_no_stale_recurrence_extension(self):
        events,report=self.collect(calendar(event(start='20260906T100000Z',extra='RRULE:FREQ=WEEKLY;UNTIL=20261031T235959Z\r\n')))
        self.assertEqual(events,[]);self.assertTrue(report['ok']);self.assertEqual(report['calendarStatus'],'no-upcoming-sessions')
        self.assertFalse(self.collect('not a calendar')[1]['ok'])
        self.assertFalse(self.collect(calendar(event(extra='RRULE:FREQ=SECONDLY\r\n')))[1]['ok'])

    def test_summer_to_winter_local_time_and_single_price_do_not_imply_vacancies(self):
        text=calendar(event(extra='DTEND:20261122T105000Z\r\nSTATUS:CONFIRMED\r\n').replace('DTSTART:20261122T100000Z','DTSTART;TZID=Europe/Lisbon:20261122T100000'))
        rows,_=self.collect(text);self.assertEqual(rows[0]['end'],'10:50');self.assertEqual(rows[0]['status'],'unverified')
        october=datetime(2026,10,17,12,tzinfo=NOW.tzinfo)
        text=calendar(event(start='20261018T090000Z',extra='RRULE:FREQ=WEEKLY;COUNT=3\r\n').replace('DTSTART:20261018T090000Z','DTSTART;TZID=Europe/Lisbon:20261018T100000'))
        rows,_=knock.collect(HTML,lambda u:(text,None),october,update.make_event)
        self.assertEqual([e['start'] for e in rows],['10:00']*3)

    def test_scan_withdraws_successfully_removed_sessions_but_keeps_fresh_data_on_failure(self):
        source={'name':'Knock-Knock Family Club','url':knock.PAGE,'type':'knock-public-calendar'}
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)
            with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=(HTML,None)),patch.object(update,'fetch_public_calendar',return_value=(calendar(event()),None)):
                first,events,h,*_=update.scan([source],{},{},NOW)
            self.assertEqual(len(events['events']),1);(data/'events.json').write_text(json.dumps(events))
            with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=(HTML,None)),patch.object(update,'fetch_public_calendar',return_value=(None,'unavailable')):
                _,retained,*_=update.scan([source],first,h,NOW+timedelta(hours=1))
            self.assertEqual(len(retained['events']),1)
            with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=(HTML,None)),patch.object(update,'fetch_public_calendar',return_value=(calendar(''),None)):
                _,removed,*_=update.scan([source],first,h,NOW+timedelta(hours=1))
            self.assertEqual(removed['events'],[])

    def test_export_reader_rejects_private_arbitrary_and_redirected_urls(self):
        for url in ['https://calendar.google.com/calendar/ical/private/private/token.ics','https://evil.example/public/basic.ics',knock.feed_url(ID)+'?token=secret']:
            with patch.object(update.SESSION,'get') as get:
                self.assertIsNone(update.fetch_public_calendar(url)[0]);get.assert_not_called()
