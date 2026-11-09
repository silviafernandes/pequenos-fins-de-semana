import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update

URL = 'https://www.bibliotecasearquivosmatosinhos.pt/evento-44/bebeteca-magica-o-meu-primeiro-paninho'
NOW = datetime(2026, 11, 9, 10, tzinfo=ZoneInfo('Europe/Lisbon'))
FIXTURE = (Path(__file__).parent/'fixtures/matosinhos-paninho.html').read_text()

class MonitoringTests(unittest.TestCase):
    def test_real_library_html_uses_schedule_not_midnight(self):
        event = update.library_event(FIXTURE, URL, 'Bibliotecas de Matosinhos', NOW)
        self.assertEqual((event['date'], event['start'], event['end']), ('2026-11-21', '10:00', None))
        self.assertEqual((event['minMonths'], event['maxMonths']), (6, 36))
        self.assertEqual(event['bookingUrl'], 'https://forms.gle/htFeB3xMT6nSwXwDA')
        self.assertEqual(event['status'], 'unverified')
        self.assertIsNone(event['indoor'])

    def test_missing_schedule_or_age_never_invents_event(self):
        self.assertIsNone(update.library_event(FIXTURE.replace('10h00', 'hora por confirmar'), URL, 'Biblioteca', NOW))
        self.assertIsNone(update.library_event(FIXTURE.replace('6 aos 36 meses', 'idades por confirmar'), URL, 'Biblioteca', NOW))

    def test_opening_requires_explicit_time(self):
        self.assertEqual(update.opening_dates('Inscrições abrem no dia 13 de novembro.', 2026), [])
        self.assertEqual(update.opening_dates('Inscrições abrem no dia 13 de novembro às 10h00.', 2026), ['2026-11-13T10:00+00:00'])

    def test_registration_evidence_updates_card_and_history_once(self):
        event = update.library_event(FIXTURE, URL, 'Biblioteca', NOW)
        history = {}
        args = ([event], history, URL, event['title'], 'Biblioteca', [event['bookingUrl']], ['2026-11-13T10:00+00:00'], NOW.isoformat())
        update.apply_registration(*args)
        update.apply_registration(*args)
        self.assertEqual(event['status'], 'scheduled')
        self.assertEqual(event['openingAt'], '2026-11-13T10:00+00:00')
        self.assertEqual(len(history['observations']), 1)
        other = dict(event, sourceUrl='https://example.org/other', status='unverified', openingAt=None)
        update.apply_registration([other], {}, *args[2:])
        self.assertIsNone(other['openingAt'])

    def test_multiple_sessions_do_not_share_ambiguous_registration_date(self):
        event = update.library_event(FIXTURE, URL, 'Biblioteca', NOW)
        events = [event, dict(event, id='other', date='2026-11-22')]
        update.apply_registration(events, {}, URL, '', 'Biblioteca', [], ['2026-11-13T10:00+00:00'], NOW.isoformat())
        self.assertTrue(all(e['openingAt'] is None for e in events))

    def test_scan_revisits_known_event_and_preserves_data_on_failure(self):
        event = update.library_event(FIXTURE, URL, 'Biblioteca', NOW)
        event['id'] = 'curated-id'
        source = {'name':'Biblioteca', 'url':'https://www.bibliotecasearquivosmatosinhos.pt/', 'priority':1}
        html = FIXTURE
        # Put opening evidence inside the event content, as in the official template.
        html = html.replace('Horário:</div>', 'Horário:</div><p>Inscrições abrem no dia 13 de novembro às 10h00.</p>')
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory)
            (data/'events.json').write_text(json.dumps({'events':[event]}))
            with patch.object(update, 'DATA', data), patch.object(update, 'fetch', side_effect=[('<html></html>',None),(html,None)]), patch.object(update.time,'sleep'):
                discovery, events, history, messages, added = update.scan([source], {}, {}, NOW)
            self.assertEqual(len(events['events']), 1)
            self.assertEqual(events['events'][0]['id'], 'curated-id')
            self.assertEqual(events['events'][0]['openingAt'], '2026-11-13T10:00+00:00')
            self.assertEqual(added, [])
            (data/'events.json').write_text(json.dumps(events))
            with patch.object(update,'DATA',data), patch.object(update,'fetch',return_value=(None,'HTTP 403')):
                failed, preserved, _, _, _ = update.scan([source], discovery, history, NOW)
            self.assertEqual(preserved['events'], events['events'])
            self.assertEqual(failed['sourceIndex']['Biblioteca']['lastSuccessfulAt'], discovery['sourceIndex']['Biblioteca']['lastSuccessfulAt'])

    def test_robots_exclusion_prevents_page_request(self):
        response = type('Response', (), {'status_code':200, 'ok':True, 'text':'User-agent: *\nDisallow: /private'})()
        with patch.dict(update.ROBOTS, {}, clear=True), patch.object(update.SESSION,'get',return_value=response) as get:
            html, error = update.fetch('https://example.org/private')
            self.assertIsNone(html)
            self.assertIn('disallows', error)
            self.assertEqual(get.call_count, 1)

    def test_unavailable_robots_records_specific_failure(self):
        response = type('Response', (), {'status_code':400, 'ok':False})()
        with patch.dict(update.ROBOTS, {}, clear=True), patch.object(update.SESSION,'get',return_value=response):
            html, error = update.fetch('https://example.org/event')
            self.assertIsNone(html)
            self.assertIn('robots.txt unavailable: HTTP 400', error)

    def test_baby_only_age_supported_and_date_only_rejected(self):
        item={'name':'Música para bebés 0-6 meses','startDate':'2026-11-15T10:00', 'location':'Porto'}
        event=update.make_event(item,URL,'Exemplo',NOW)
        self.assertEqual(event['maxMonths'],6)
        item['startDate']='2026-11-15'
        self.assertIsNone(update.make_event(item,URL,'Exemplo',NOW))

if __name__ == '__main__': unittest.main()
