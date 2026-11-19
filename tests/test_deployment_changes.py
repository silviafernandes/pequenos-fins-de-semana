import os
import json
from datetime import datetime,timedelta,timezone
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from deployment_changes import needs_collection,detect,main,record_collection,checked_data_matches

class DeploymentChangesTests(unittest.TestCase):
    def test_ui_and_docs_only_changes_do_not_call_external_sources(self):
        self.assertFalse(needs_collection(['src/App.jsx','src/styles.css','public/illustrations/bird.webp','docs/review.md','tests/browser.cjs','package.json','package-lock.json']))

    def test_collector_policy_or_data_changes_require_a_new_scan(self):
        for path in ['scripts/update.py','public/data/events.json','public/data/watchlist.json','public/data/venues.json','requirements.txt','.github/workflows/site.yml']:
            self.assertTrue(needs_collection(['src/App.jsx',path]),path)

    def test_schedules_and_manual_runs_never_skip_collection(self):
        for event in ['schedule','workflow_dispatch',None]:self.assertTrue(needs_collection(['src/App.jsx'],event))
        self.assertTrue(detect('push','0'*40,'a'*40))
        with patch('deployment_changes.subprocess.check_output',side_effect=OSError):self.assertTrue(detect('push','b'*40,'a'*40))

    def test_output_is_a_boolean_and_git_arguments_are_not_shell_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'output'
            with patch('sys.argv',['deployment_changes.py']),patch.dict(os.environ,{'GITHUB_EVENT_NAME':'push','BEFORE_SHA':'a'*40,'GITHUB_SHA':'b'*40,'GITHUB_OUTPUT':str(output)}),patch('deployment_changes.subprocess.check_output',return_value='src/App.jsx\0src/styles.css\0') as run,patch('deployment_changes.checked_data_matches',return_value=True):
                main()
            self.assertEqual(output.read_text(),'refresh_data=false\n')
            self.assertEqual(run.call_args.args[0],['git','diff','--name-only','--no-renames','-z','a'*40,'b'*40])

    def test_unprocessed_inputs_and_manual_data_edits_force_collection_even_after_a_ui_push(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'public/data';data.mkdir(parents=True);(root/'scripts').mkdir()
            source=root/'scripts/parser.py';source.write_text('old parser')
            events={'events':[]};discoveries={'sourceIndex':{}};history={'lastRun':datetime.now(timezone.utc).isoformat()}
            record_collection(root,events,discoveries,history)
            for name,value in [('events',events),('discoveries',discoveries),('history',history)]:
                (data/f'{name}.json').write_text(json.dumps(value))
            self.assertTrue(checked_data_matches(root))
            with patch('deployment_changes.subprocess.check_output',return_value='src/App.jsx\0'):
                self.assertFalse(detect('push','a'*40,'b'*40,root))
                source.write_text('changed parser')
                self.assertTrue(detect('push','a'*40,'b'*40,root),'An intermediate collector push must not be lost')
                source.write_text('old parser')
            (data/'events.json').write_text(json.dumps({'events':[{'title':'manually edited'}]}))
            self.assertFalse(checked_data_matches(root))
            (data/'events.json').write_text(json.dumps(events))
            history['observations']=[{'openingAt':'manually edited'}]
            (data/'history.json').write_text(json.dumps(history))
            self.assertFalse(checked_data_matches(root))

    def test_missing_or_old_collection_metadata_is_not_treated_as_a_fresh_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'public/data';data.mkdir(parents=True)
            events={'events':[]};discoveries={'sourceIndex':{}};history={'lastRun':(datetime.now(timezone.utc)-timedelta(hours=25)).isoformat()}
            record_collection(root,events,discoveries,history)
            for name,value in [('events',events),('discoveries',discoveries),('history',history)]:
                (data/f'{name}.json').write_text(json.dumps(value))
            self.assertFalse(checked_data_matches(root))
