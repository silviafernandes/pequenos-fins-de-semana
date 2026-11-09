"""Create a conservative starter dataset from the verified 9 Nov 2026 report.
This file is a one-off convenience script. After deployment, data is updated in
public/data/events.json without adding invented sessions.
"""
import json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
OLD=Path('/mnt/data/pequenos_fins_de_semana_2026-11-09.html')
if not OLD.exists():
    raise SystemExit('Historical snapshot not available; public/data/events.json is provided in the project.')
s=OLD.read_text()
data=json.loads(re.search(r'const DATA=(.*?);\nconst dateFmt',s,re.S).group(1))
imgs=data['images']
out=[]
for e in data['events']:
    origin=e.get('info') or e.get('link')
    status={'opens':'scheduled','unverified':'unverified','walkin':'walkin'}.get(e['status'],'unverified')
    out.append({
        'id':e['id'], 'title':e['title'], 'date':e['date'],
        'start':e.get('start') or None, 'end':e.get('end') or None,
        'minMonths':6 if e['id']=='paninho-21' else (9 if e['id']=='pint-22' else (18 if e['id']=='papi-19' else (3 if e['id'].startswith('som') else 12))),
        'maxMonths':36 if not e['id'].startswith('som') else 72,
        'ageText':e['ages'], 'price':e['price'], 'venue':e['venue'],
        'area':e['area'],'category':e['category'],'kind':e.get('kind',''),
        'description':e['desc'],'bookingUrl':e.get('link'),
        'sourceUrl':origin,'sourceName':e.get('source',''),
        'imageUrl':imgs.get(e.get('image')),
        'status':status, 'openingAt':e.get('opening', '').replace(' ', 'T') or None,
        'capacity':e.get('capacity') or None,
        'indoor': True, 'confidence':'official-listing',
        'evidence':e.get('note',''), 'evidenceDate':'2026-11-09',
        'discoveredAt':'2026-11-09T09:00:00Z',
        'sourceType':'curated',
        'priority':e.get('priority', 50)
    })
out.sort(key=lambda e:(e['date'],e.get('start') or '99:99'))
(ROOT/'public/data/events.json').write_text(json.dumps({
    'updatedAt':'2026-11-09T14:00:00Z','lastSuccessfulScan':None,
    'origin':'CTT Correios de 4 Caminhos, Senhora da Hora, Matosinhos',
    'windowDays':42,'events':out},ensure_ascii=False,indent=2)+'\n')
(ROOT/'public/data/history.json').write_text(json.dumps({
    'observations':[{'id':'opening-paninho','eventId':'paninho-21','organiser':'Biblioteca Municipal Florbela Espanca','kind':'opening-announced','openingAt':'2026-11-13T10:00:00+00:00','eventAt':'2026-11-21T10:00:00+00:00','firstObserved':'2026-11-09','source':'User confirmed text displayed in the official registration form','sourceUrl':'https://forms.gle/htFeB3xMT6nSwXwDA','certainty':'confirmed-by-user'}],
    'alertKeys':[]},ensure_ascii=False,indent=2)+'\n')
print(f'Wrote {len(out)} sessions')
