import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import requests

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import telegram_alerts as telegram

ENV={'TELEGRAM_BOT_TOKEN':'123456:FAKE_TEST_ONLY','TELEGRAM_CHAT_ID':'987654'}

class TelegramTests(unittest.TestCase):
    def client(self,code=200,body=None):
        session=Mock()
        response=session.post.return_value
        response.status_code=code
        response.json.return_value=body if body is not None else {'ok':True,'result':{'message_id':1,'chat':{'id':987654}}}
        return session

    def test_missing_configuration_names_are_reported_without_sending(self):
        session=self.client()
        result=telegram.send_message(telegram.TEST_MESSAGE,session,{})
        self.assertEqual(result.status,'not-configured')
        self.assertEqual(result.missing,('TELEGRAM_BOT_TOKEN','TELEGRAM_CHAT_ID'))
        session.post.assert_not_called()

    def test_configuration_check_does_not_claim_live_delivery(self):
        self.assertEqual(telegram.configuration(ENV)[2].status,'ready')
        self.assertIn('ainda precisa',telegram.configuration(ENV)[2].reason)
        bad=dict(ENV,TELEGRAM_BOT_TOKEN='malformed secret')
        self.assertEqual(telegram.configuration(bad)[2].status,'invalid-config')

    def test_test_message_is_sent_once_and_destination_is_verified(self):
        session=self.client()
        result=telegram.send_message(telegram.TEST_MESSAGE,session,ENV)
        self.assertTrue(result.accepted)
        session.post.assert_called_once()
        request=session.post.call_args
        self.assertIn('TESTE',request.kwargs['json']['text'])
        self.assertEqual(request.kwargs['json']['chat_id'],'987654')
        self.assertFalse(request.kwargs['allow_redirects'])
        self.assertEqual(request.kwargs['timeout'],10)

    def test_wrong_or_missing_destination_is_not_a_delivery_confirmation(self):
        for body in [{'ok':True,'result':{'message_id':1,'chat':{'id':123}}},{'ok':True,'result':{'message_id':1}},{'ok':True,'result':{'chat':{'id':987654}}}]:
            self.assertEqual(telegram.send_message('test',self.client(body=body),ENV).status,'uncertain')

    def test_api_failure_codes_and_malformed_errors_are_safe(self):
        for code in [400,401,403,429]:
            with self.subTest(code=code):
                result=telegram.send_message('test',self.client(code,{'ok':False,'error_code':code,'description':ENV['TELEGRAM_BOT_TOKEN']}),ENV)
                self.assertEqual(result.status,'failed')
                self.assertNotIn(ENV['TELEGRAM_BOT_TOKEN'],result.reason)
        self.assertEqual(telegram.send_message('test',self.client(500,{'ok':False}),ENV).status,'uncertain')
        self.assertEqual(telegram.send_message('test',self.client(400,{'ok':False,'error_code':{}}),ENV).status,'failed')

    def test_timeout_is_uncertain_not_retried_and_never_prints_token(self):
        session=self.client();session.post.side_effect=requests.Timeout('https://api.telegram.org/bot'+ENV['TELEGRAM_BOT_TOKEN'])
        result=telegram.send_message('test',session,ENV)
        self.assertEqual(result.status,'uncertain')
        session.post.assert_called_once()
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):telegram.report(result)
        self.assertNotIn(ENV['TELEGRAM_BOT_TOKEN'],stream.getvalue())

    def test_malformed_success_json_is_not_accepted(self):
        session=self.client();session.post.return_value.json.side_effect=ValueError('bad')
        self.assertEqual(telegram.send_message('test',session,ENV).status,'uncertain')
        self.assertEqual(telegram.send_message('test',self.client(302),ENV).status,'failed')

    def test_pushes_and_empty_alert_lists_never_send(self):
        session=self.client()
        self.assertEqual(telegram.send_alerts([],session,ENV).status,'skipped')
        self.assertEqual(telegram.send_alerts(['alert'],session,dict(ENV,GITHUB_EVENT_NAME='push')).status,'disabled')
        session.post.assert_not_called()
        self.assertTrue(telegram.send_alerts(['new form'],session,dict(ENV,GITHUB_EVENT_NAME='schedule')).accepted)

    def test_summary_contains_no_destination_or_token(self):
        with tempfile.TemporaryDirectory() as directory:
            summary=Path(directory)/'summary.md'
            stream=io.StringIO()
            with contextlib.redirect_stdout(stream):telegram.report(telegram.send_message('test',self.client(),ENV),summary)
            text=summary.read_text()+stream.getvalue()
            for secret in ENV.values():self.assertNotIn(secret,text)

    def test_cli_check_mode_does_not_send_and_send_mode_fails_without_secrets(self):
        stream=io.StringIO()
        with patch.dict(os.environ,ENV,clear=True),patch.object(telegram,'send_message') as sender,contextlib.redirect_stdout(stream):
            self.assertEqual(telegram.main([]),0)
            sender.assert_not_called()
        with patch.dict(os.environ,{},clear=True),contextlib.redirect_stdout(stream):
            self.assertEqual(telegram.main(['--send-test']),1)

    def test_emoji_message_stays_within_telegram_limit(self):
        session=self.client();telegram.send_message('🧪'*5000,session,ENV)
        self.assertLessEqual(len(session.post.call_args.kwargs['json']['text'].encode('utf-16-le'))//2,4000)

if __name__=='__main__':unittest.main()
