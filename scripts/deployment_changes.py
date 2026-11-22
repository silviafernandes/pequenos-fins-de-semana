"""Reuse checked data for UI changes, never for unprocessed collector changes."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GENERATED=('events','discoveries','history')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def collection_inputs(root):
    files=set(root.glob('scripts/**/*.py'))
    files.update(root/name for name in ('requirements.txt','.github/workflows/site.yml','public/data/watchlist.json','public/data/venues.json','public/data/playlab-programme.json','public/data/poster-reviews.json','public/data/maia-programmes.json'))
    return {str(file.relative_to(root)):hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else 'missing' for file in sorted(files)}


def record_collection(root,events,discoveries,history):
    history['collectionInputs']=collection_inputs(root)
    history['collectionEventsDigest']=digest(events)
    history['collectionDiscoveriesDigest']=digest(discoveries)
    history.pop('collectionHistoryDigest',None)
    history['collectionHistoryDigest']=digest(history)


def checked_data_matches(root=ROOT,now=None):
    """Also catches source/data changes in cancelled intermediate queued pushes."""
    try:
        events,discoveries,history=[json.loads((root/'public/data'/f'{name}.json').read_text()) for name in GENERATED]
        last=datetime.fromisoformat(history['lastRun'])
        if last.tzinfo is None or not timedelta(0)<=(now or datetime.now(timezone.utc))-last<=timedelta(hours=24):return False
        own_digest=history.pop('collectionHistoryDigest')
        return (history['collectionInputs']==collection_inputs(root)
                and history['collectionEventsDigest']==digest(events)
                and history['collectionDiscoveriesDigest']==digest(discoveries)
                and own_digest==digest(history))
    except (OSError,ValueError,KeyError,TypeError):return False


def needs_collection(paths,event='push'):
    if event!='push':return True
    return any(path.startswith(('scripts/','public/data/')) or path in ('requirements.txt','.github/workflows/site.yml') for path in paths)


def detect(event,before,head,root=ROOT):
    if event!='push' or not all(re.fullmatch(r'[0-9a-f]{40}',sha or '') and set(sha)!={'0'} for sha in (before,head)):
        return True
    try:
        paths=subprocess.check_output(['git','diff','--name-only','--no-renames','-z',before,head],text=True).split('\0')
    except (OSError,subprocess.CalledProcessError):return True
    return needs_collection(paths,event) or not checked_data_matches(root)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-data',action='store_true')
    args=parser.parse_args()
    if args.check_data:
        if checked_data_matches():return 0
        print('Checked data does not match the current collection inputs. A newer run must refresh it before publication.')
        return 1
    refresh=detect(os.environ.get('GITHUB_EVENT_NAME'),os.environ.get('BEFORE_SHA'),os.environ.get('GITHUB_SHA'))
    value='true' if refresh else 'false'
    if os.environ.get('GITHUB_OUTPUT'):
        with Path(os.environ['GITHUB_OUTPUT']).open('a',encoding='utf-8') as output:output.write(f'refresh_data={value}\n')
    print('External source refresh required.' if refresh else 'Frontend-only change: reusing checked data; no external scan.')
    return 0


if __name__=='__main__':raise SystemExit(main())
