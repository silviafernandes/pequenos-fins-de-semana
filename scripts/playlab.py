"""Public PlayLab entry points; general age ranges never become session evidence."""
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

AGENDA='https://sites.google.com/view/playlabporto/agenda'
WEEKEND_SHORT='https://forms.gle/hMDB9KzHpHbUbagV8'
WEEKEND_FORM='https://docs.google.com/forms/d/e/1FAIpQLScd4N4mxUFYqP6l6kMYB6LvdyTCm4_Q5LGWyfWp5ekNYFtKSw/viewform'


def programme_links(html, url):
    """Follow monthly issues even when their titles contain no baby keywords."""
    parsed=urlparse(url)
    if parsed.hostname!='playlabporto.beehiiv.com':return []
    found=[]
    for a in BeautifulSoup(html,'html.parser').find_all('a',href=True):
        target=urljoin(url,a['href'])
        p=urlparse(target)
        if p.scheme=='https' and p.hostname=='playlabporto.beehiiv.com' and p.path.startswith('/p/'):
            found.append((target,a.get_text(' ',strip=True) or 'Programa PlayLab'))
    return list(dict(found).items())


def weekend_form(html, url):
    """Use the observed expanded URL only while the agenda still links to it."""
    if url.rstrip('/')!=AGENDA:return None
    for a in BeautifulSoup(html,'html.parser').find_all('a',href=True):
        target=urljoin(url,a['href'])
        # Google Sites wraps outgoing public links in a Google redirect.
        if urlparse(target).hostname=='www.google.com' and urlparse(target).path=='/url':
            from urllib.parse import parse_qs
            target=parse_qs(urlparse(target).query).get('q',[''])[0]
        if target.rstrip('/')==WEEKEND_SHORT:return WEEKEND_FORM
    return None

# Yearless form choices belong only to this explicitly reviewed programme window.
def parse_choice(label, year, corrections=None):
    original=' '.join(label.split())
    label=(corrections or {}).get(original,original)
    match=re.fullmatch(r'(.+?)[,\s]+(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(meses|anos)(?:/months|/years)?\s*[-–]\s*(Sáb|Dom)\.?\s*(\d{1,2})/(\d{1,2}),?\s*(\d{1,2}):(\d{2})(?:\s*[-–]\s*(\d{1,2}):(\d{2}))?',label,re.I)
    if not match:return None
    title,lo,hi,unit,weekday,d,m,h,minute,eh,em=match.groups()
    try:
        start=datetime(year,int(m),int(d),int(h),int(minute))
        end=start.replace(hour=int(eh),minute=int(em)) if eh is not None else None
    except ValueError:return None
    if start.weekday()!=({'sáb':5,'dom':6}[weekday.lower()]) or (end is not None and end<=start):return None
    factor=12 if unit.lower()=='anos' else 1
    if int(hi)<int(lo):return None
    return {'title':title,'date':start.date().isoformat(),'start':start.strftime('%H:%M'),'end':end.strftime('%H:%M') if end else None,'minMonths':int(lo)*factor,'maxMonths':int(hi)*factor,'originalChoice':original}


def public_choices(html):
    soup=BeautifulSoup(html,'html.parser')
    questions=soup.select('[role="listitem"]')
    target=next((q for q in questions if re.search(r'Em que Laborat[oó]rio|In what laboratory',q.get_text(' ',strip=True),re.I)),None)
    if questions and target is None:return []
    soup=target or soup
    return list(dict.fromkeys(' '.join(str(node.get('data-answer-value') or node.get('data-value') or node.get('aria-label') or node.get_text(' ',strip=True)).split()) for node in soup.select('[role="checkbox"], [role="radio"]')))


def evidence_digest(evidence):
    keys=('date','start','end','minMonths','maxMonths','venue','sourceUrl','reviewedAt','validUntil','originalChoice')
    return hashlib.sha256(json.dumps({k:evidence.get(k) for k in keys},sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def valid_review(evidence, now):
    if evidence.get('kind')!='reviewed-playlab-programme' or evidence.get('sourceUrl')!=WEEKEND_FORM or evidence.get('venue')!='PlayLab Porto':return False
    try:
        reviewed=datetime.fromisoformat(evidence['reviewedAt'])
        until=date.fromisoformat(evidence['validUntil'])
        return (reviewed.tzinfo is not None and reviewed==datetime.fromisoformat(evidence['checkedAt']) and reviewed<=now
                and now.date()<=until<=reviewed.date()+timedelta(days=45)
                and reviewed.date()<=date.fromisoformat(evidence['date'])<=until
                and evidence.get('reviewDigest')==evidence_digest(evidence))
    except (KeyError,TypeError,ValueError):return False


def collect_programme(programme, html, error, now, make_event):
    """Retry public options; preserve dated user-reviewed evidence without faking a recheck."""
    from eligibility import mark_session
    report={'bookingCheckedAt':now.isoformat(),'reviewNeeded':True,'reviewedSessions':0,'liveSessions':0}
    if not programme or programme.get('sourceUrl')!=WEEKEND_FORM:return [],report
    try:
        year=int(programme['year']);until=date.fromisoformat(programme['validUntil'])
        reviewed=datetime.fromisoformat(programme['reviewedAt'])
        if reviewed.tzinfo is None or reviewed>now or not reviewed.date()<=until<=reviewed.date()+timedelta(days=45):return [],report
    except (KeyError,TypeError,ValueError):return [],report
    report.update(programmeReviewedAt=reviewed.isoformat(),programmeValidUntil=until.isoformat())
    choices=public_choices(html) if html and not error else []
    # A partial/unrecognised form must never silently erase a reviewed programme.
    parsed=[parse_choice(c,year,programme.get('corrections')) for c in choices]
    complete=bool(choices) and all(parsed) and all(date.fromisoformat(p['date'])<=until for p in parsed if p)
    labels=choices if complete else programme.get('choices',[])
    report['reviewNeeded']=not complete
    report['formStatus']='public-options' if complete else 'access-blocked' if error else 'needs-review'
    report['changedChoices']=[c for c in choices if c not in programme.get('choices',[])]
    result=[]
    if now.date()>until:return result,report
    for label in labels:
        row=parse_choice(label,year,programme.get('corrections'))
        if not row or not reviewed.date()<=date.fromisoformat(row['date'])<=until:continue
        raw={'name':row['title'],'description':f"Atividade em família, dos {row['minMonths']} aos {row['maxMonths']} meses. Criança acompanhada por 1 ou 2 adultos.",'startDate':row['date']+'T'+row['start'],'endDate':row['date']+'T'+row['end'] if row['end'] else None,'location':{'name':'PlayLab Porto','address':'Rua de Alves Redol 386, Porto'},'url':WEEKEND_FORM,'offers':{'price':18 if 'messy play' in row['title'].lower() else 15,'priceCurrency':'EUR','url':WEEKEND_FORM}}
        if label not in programme.get('choices',[]):raw['offers'].pop('price',None)
        event=make_event(raw,WEEKEND_FORM,'PlayLab Porto',now)
        if not event:continue
        if re.search(r'baby lab|messy play',row['title'],re.I):event['category']='Sensorial'
        event.update(sourceType='playlab-programme',confidence='reviewed-programme',evidenceDate=(now if complete else reviewed).date().isoformat(),evidence='Opções do formulário consultadas; vagas por confirmar.' if complete else 'Programa do formulário revisto a partir de imagem partilhada. Vagas e alterações posteriores por confirmar.')
        if complete:
            mark_session(event,WEEKEND_FORM,now,'official-programme');report['liveSessions']+=1
        else:
            mark_session(event,WEEKEND_FORM,reviewed,'reviewed-playlab-programme')
            event['sessionEvidence'].update(reviewedAt=reviewed.isoformat(),validUntil=until.isoformat(),originalChoice=row['originalChoice'])
            event['sessionEvidence']['reviewDigest']=evidence_digest(event['sessionEvidence'])
            report['reviewedSessions']+=1
        result.append(event)
    return result,report
