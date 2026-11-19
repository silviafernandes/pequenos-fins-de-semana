#!/usr/bin/env python3
"""Read-only completeness audit: unknown facts are reported, never inferred."""
import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from eligibility import valid_age_range

ROOT=Path(__file__).resolve().parents[1]
AMENITIES=('playground','toilets','cafe','changingTable','strollerAccess')
STATES={'confirmed','unknown','temporarily-closed','not-present'}

def audit(places,events,venues):
    errors=[];counts={a:Counter() for a in AMENITIES};seen=set()
    for place in places:
        id=place.get('id')
        if not id or id in seen:errors.append(f'Duplicate or missing place ID: {id}')
        seen.add(id)
        for key in ('title','area','navigationQuery','sourceUrl','amenityAudit'):
            if not place.get(key):errors.append(f'{id}: missing {key}')
        for key in AMENITIES:
            fact=place.get('amenities',{}).get(key)
            if not isinstance(fact,dict) or fact.get('status') not in STATES:
                errors.append(f'{id}: missing/invalid amenity {key}');continue
            state=fact['status'];counts[key][state]+=1
            if state!='unknown' and not all(fact.get(k) for k in ('sourceUrl','evidence','reviewedAt')):
                errors.append(f'{id}: {key} has no specific source evidence')
            if state!='unknown' and urlparse(fact.get('sourceUrl','')).scheme!='https':errors.append(f'{id}: insecure amenity source')
        playground=place.get('amenities',{}).get('playground',{})
        if (playground.get('status')=='confirmed')!=('playground' in place.get('types',[])):
            errors.append(f'{id}: playground tag disagrees with evidence')
        lo,hi=playground.get('minMonths'),playground.get('maxMonths')
        if lo is not None and (not isinstance(lo,(int,float)) or lo<0 or hi is None or hi<lo):errors.append(f'{id}: invalid playground ages')
    published=events.get('events',[]);sessions=set();duplicates=[]
    for event in published:
        key=tuple(event.get(k) for k in ('sourceUrl','date','start','venue','title'))
        if key in sessions:duplicates.append(event.get('id'))
        sessions.add(key)
        for field in ('id','title','date','start','sourceUrl','venue','sessionEvidence'):
            if not event.get(field):errors.append(f"{event.get('id')}: published session missing {field}")
        if not valid_age_range(event.get('minMonths'),event.get('maxMonths')):errors.append(f"{event.get('id')}: ineligible published age")
    if duplicates:errors.append(f'Duplicate published sessions: {duplicates}')
    missing={field:sum(e.get(field) is None or e.get(field) in ('','Por confirmar') for e in published) for field in ('end','indoor','price','bookingUrl')}
    return {'places':{'total':len(places),'reviewed':sum(bool(p.get('amenityAudit')) for p in places),'amenities':{k:dict(v) for k,v in counts.items()}},'events':{'published':len(published),'pending':len(events.get('pendingEvents',[])),'excluded':len(events.get('excludedEvents',[])),'duplicateSessions':duplicates,'unknownFields':missing},'outings':len(events.get('outings',[])),'venues':len(venues.get('venues',{})),'errors':errors}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events',type=Path,default=ROOT/'public/data/events.json')
    args=parser.parse_args()
    report=audit(json.loads((ROOT/'src/evergreenIdeas.json').read_text()),json.loads(args.events.read_text()),json.loads((ROOT/'public/data/venues.json').read_text()))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return bool(report['errors'])

if __name__=='__main__':raise SystemExit(main())
