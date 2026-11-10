"""Venue-level coordinates and explicit evidence are required for publication."""
import math
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse


def normalized(value):
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',value or '').encode('ascii','ignore').decode().lower()).split())


def host(url):
    return (urlparse(url or '').hostname or '').removeprefix('www.')


def haversine_km(a,b):
    lat1,lat2=map(math.radians,(a['latitude'],b['latitude']))
    dlat=lat2-lat1;dlon=math.radians(b['longitude']-a['longitude'])
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371.0088*2*math.asin(min(1,math.sqrt(h)))


def locate(event,registry):
    name=normalized(event.get('venue',''))
    matches=[(key,v) for key,v in registry.get('venues',{}).items() if name in {normalized(x) for x in v.get('aliases',[])+[v['name']]}]
    if len(matches)!=1:return None
    key,venue=matches[0]
    if venue.get('precision')!='venue':return None
    return dict(venue,id=key)


def set_distance(event,registry):
    venue=locate(event,registry)
    for key in ('distanceKm','distanceWithinRadius','venueId','geo'):
        event.pop(key,None)
    if not venue:return None
    origin=registry['origin'];distance=haversine_km(origin,venue)
    event.update(distanceKm=round(distance,4),distanceWithinRadius=distance<=registry['radiusKm'],venueId=venue['id'],geo={'latitude':venue['latitude'],'longitude':venue['longitude'],'coordinateSourceUrl':venue['coordinateSourceUrl'],'originId':origin['id'],'method':'straight-line'})
    return venue


def mark_session(event,url,now,kind):
    event['sessionEvidence']={key:event.get(key) for key in ('date','start','end','minMonths','maxMonths','venue')}
    event['sessionEvidence'].update(sourceUrl=url,checkedAt=now.isoformat(),kind=kind)
    return event


def booking_publisher_matches(event,evidence,venue):
    if evidence.get('kind')!='provider-booking':return False
    partner=event.get('allegrowPartnerId')
    address=event.get('locationAddress')
    if not partner or not address or partner!=evidence.get('partnerId') or normalized(address)!=normalized(evidence.get('address')):return False
    return any(rule.get('host')==host(evidence.get('sourceUrl')) and rule.get('partnerId')==partner and normalized(rule.get('address'))==normalized(address) for rule in venue.get('bookingPublishers',[]))


def assess(event,registry,now):
    venue=set_distance(event,registry)
    reasons=[]
    if not venue:reasons.append('Local exato por verificar')
    elif not event['distanceWithinRadius']:reasons.append('Fora do raio de 15 km')
    try:
        day=date.fromisoformat(event['date'])
        if day.weekday()<5 or not now.date()<=day<=now.date()+timedelta(days=45):reasons.append('Fora dos próximos fins de semana')
    except (KeyError,ValueError,TypeError):reasons.append('Data por verificar')
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',event.get('start') or ''):reasons.append('Hora por verificar')
    lo,hi=event.get('minMonths'),event.get('maxMonths')
    if not isinstance(lo,(int,float)) or not isinstance(hi,(int,float)) or not 0<=lo<36 or hi<lo:reasons.append('Idade inadequada ou por verificar')
    evidence=event.get('sessionEvidence',{})
    if not evidence or any(evidence.get(k)!=event.get(k) for k in ('date','start','end','minMonths','maxMonths','venue')):
        reasons.append('Sessão sem evidência específica')
    elif venue and host(evidence.get('sourceUrl')) not in venue.get('officialHosts',[]) and not booking_publisher_matches(event,evidence,venue):
        reasons.append('Sessão sem confirmação na fonte original')
    else:
        try:
            checked=datetime.fromisoformat(evidence['checkedAt'])
            if checked.tzinfo is None or not timedelta(0)<=now-checked<=timedelta(hours=48):reasons.append('Evidência da sessão desatualizada')
        except (KeyError,ValueError,TypeError):reasons.append('Verificação da sessão em falta')
    event['validationStatus']='verified' if not reasons else ('excluded' if venue and not event['distanceWithinRadius'] else 'pending')
    event['validationReasons']=reasons
    return event


def classify(events,registry,now):
    groups={'events':[],'pendingEvents':[],'excludedEvents':[]}
    for item in events:
        event=assess(item,registry,now)
        key={'verified':'events','pending':'pendingEvents','excluded':'excludedEvents'}[event['validationStatus']]
        groups[key].append(event)
    return groups
