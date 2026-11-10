"""Read only ALLEGROW's anonymous activity endpoints used by its public website.

No login, account endpoints, reviews, booking requests or writes are used.
"""
import re
from datetime import datetime, timedelta
from uuid import UUID
from bs4 import BeautifulSoup
from eligibility import mark_session

API_BASE='https://allegrow-prod-api-4zt6fvccoq-ew.a.run.app'
LIST_URL=API_BASE+'/v1/public/activities'
WEB_BASE='https://allegrowkids.pt/pt/activities/'
MAX_ACTIVITIES=100
MAX_DETAILS=12


def age_range_months(value):
    """Single values such as '0m' are ambiguous; require both published bounds."""
    if not isinstance(value,str):return None
    match=re.fullmatch(r'\s*(\d{1,2})(m|y)\s*[-–]\s*(\d{1,2})(m|y)\s*',value,re.I)
    if not match:return None
    lo=int(match[1])*(12 if match[2].lower()=='y' else 1)
    hi=int(match[3])*(12 if match[4].lower()=='y' else 1)
    return (lo,hi) if 0<=lo<=hi<=216 else None


def identifier(value):
    try:return str(UUID(value)) if isinstance(value,str) else None
    except ValueError:return None


def timestamp(value):
    try:
        time=datetime.fromisoformat(value.replace('Z','+00:00'))
        return time if time.tzinfo is not None else None
    except (ValueError,TypeError,AttributeError):return None


def weekend_slots(activity,now):
    slots=activity.get('schedules')
    if not isinstance(slots,list):return []
    result=[]
    for slot in slots:
        if not isinstance(slot,dict):continue
        if slot.get('is_cancelled') is True or str(slot.get('status','')).lower() in ('cancelled','canceled','postponed'):continue
        start=timestamp(slot.get('start_time'))
        if start:
            start=start.astimezone(now.tzinfo)
            if start.weekday()>=5 and now.date()<=start.date()<=(now+timedelta(days=45)).date():result.append(slot)
    return result


def parse_activity(activity,now,make_event):
    band=age_range_months(activity.get('age_range'))
    activity_id=identifier(activity.get('id'))
    partner=activity.get('partner')
    if not band or band[0]>=36 or not activity_id or not isinstance(partner,dict):return []
    partner_id=identifier(partner.get('id'))
    partner_name=partner.get('full_name')
    address=activity.get('location')
    title=activity.get('title')
    if not isinstance(title,str) or not title.strip():return []
    if not partner_id or not isinstance(partner_name,str) or not partner_name.strip() or not isinstance(address,str) or not address.strip():return []
    if activity.get('is_published') is False or activity.get('is_test') is True or str(activity.get('status','')).lower() in ('stub','draft','unpublished','cancelled','canceled'):return []
    cities={'porto':'Porto','vila-nova-de-gaia':'Vila Nova de Gaia','matosinhos':'Matosinhos','maia':'Maia'}
    city=cities.get(activity.get('place_id'))
    if not city:return []
    lo,hi=band
    age_text=f'{lo} meses a {hi//12} anos' if hi>=12 and hi%12==0 else f'{lo}–{hi} meses'
    text=BeautifulSoup(str(activity.get('description') or ''),'html.parser').get_text(' ',strip=True)
    url=WEB_BASE+activity_id
    # Keep the event's address; an organiser profile/office is not the session venue.
    venue=f'{partner_name} — {address.strip()}, {city}'
    events=[]
    for slot in weekend_slots(activity,now):
        schedule_id=identifier(slot.get('id'))
        if not schedule_id:continue
        raw={'name':activity.get('title'),'description':f'{text}\nAtividade publicada para {age_text}.','typicalAgeRange':age_text,'startDate':slot['start_time'],'location':{'name':venue,'address':city},'url':url}
        if timestamp(slot.get('end_time')):raw['endDate']=slot['end_time']
        if activity.get('is_free') is True:raw['offers']={'price':0,'priceCurrency':'EUR','url':url}
        elif activity.get('price') is not None:raw['offers']={'price':activity['price'],'priceCurrency':'EUR','url':url}
        event=make_event(raw,url,f'{partner_name} · ALLEGROW',now)
        if not event:continue
        event.update(sourceType='allegrow-public',allegrowActivityId=activity_id,allegrowScheduleId=schedule_id,allegrowPartnerId=partner_id,locationAddress=address.strip(),status='unverified')
        mark_session(event,url,now,'provider-booking')
        event['sessionEvidence'].update(partnerId=partner_id,address=address.strip(),detailUrl=LIST_URL+'/'+activity_id)
        # spots_left is not a reservation guarantee and is never used to mark a session open.
        events.append(event)
    return events


def collect(fetch_json,now,make_event):
    listing,error=fetch_json(LIST_URL)
    report={'ok':False,'feedUrl':LIST_URL,'readMode':'public-json','activitiesChecked':0,'detailsChecked':0,'pages':{},'detailErrors':[],'activityIssues':[],'truncated':False}
    if error:report['error']=error;return report
    if not isinstance(listing,list):report['error']='Formato inesperado no catálogo público';return report
    report['ok']=True
    report['truncated']=len(listing)>MAX_ACTIVITIES
    for row in listing[:MAX_ACTIVITIES]:
        report['activitiesChecked']+=1
        if not isinstance(row,dict) or not identifier(row.get('id')):
            report['activityIssues'].append({'reason':'Registo público sem identificador válido'});continue
        id=identifier(row['id']);url=WEB_BASE+id
        info={'url':url,'title':str(row.get('title') or '')[:160]}
        band=age_range_months(row.get('age_range'))
        if not band:
            report['pages'][url]=[]
            report['activityIssues'].append(dict(info,reason='Faixa etária incompleta'));continue
        if band[0]>=36:
            report['pages'][url]=[]
            report['activityIssues'].append(dict(info,reason='Idade mínima de 3 anos ou mais'));continue
        if not weekend_slots(row,now):
            report['pages'][url]=[]
            report['activityIssues'].append(dict(info,reason='Sem sessões nos próximos fins de semana'));continue
        if report['detailsChecked']>=MAX_DETAILS:
            report['truncated']=True;continue
        report['detailsChecked']+=1
        detail,error=fetch_json(LIST_URL+'/'+id)
        if error:
            report['detailErrors'].append(dict(info,error=error));continue
        if not isinstance(detail,dict) or detail.get('id')!=id:
            report['detailErrors'].append(dict(info,error='Detalhe público sem correspondência com a atividade'));continue
        events=parse_activity(detail,now,make_event)
        report['pages'][url]=events
        if not events:report['activityIssues'].append(dict(info,reason='Detalhes da sessão incompletos ou inadequados'))
    report['listedIds']=[identifier(row.get('id')) for row in listing if isinstance(row,dict) and identifier(row.get('id'))]
    report['activityIssues']=report['activityIssues'][:40]
    return report
