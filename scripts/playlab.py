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
        label=a.get_text(' ',strip=True).lower()
        p=urlparse(target)
        if 'fim de semana' in label and p.scheme=='https' and (p.hostname=='forms.gle' or (p.hostname=='docs.google.com' and re.fullmatch(r'/forms/d/e/[A-Za-z0-9_-]+/viewform',p.path))):return target
    return None

# Yearless form choices belong only to this explicitly reviewed programme window.
def parse_choice(label, year, corrections=None):
    original=' '.join(label.split())
    label=(corrections or {}).get(original,original)
    match=re.fullmatch(r'(.+?)[,\s]+(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(meses|anos)(?:/months|/years)?\s*[-–]\s*(Sáb|Dom)\.?\s*(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?,?\s*(\d{1,2}):(\d{2})(?:\s*[-–]\s*(\d{1,2}):(\d{2}))?',label,re.I)
    if not match:return None
    title,lo,hi,unit,weekday,d,m,published_year,h,minute,eh,em=match.groups()
    try:
        start=datetime(int(published_year) if published_year else year,int(m),int(d),int(h),int(minute))
        end=start.replace(hour=int(eh),minute=int(em)) if eh is not None else None
    except (ValueError,TypeError):return None
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


def collect_programme(programme, html, error, now, make_event, form_url=WEEKEND_FORM, agenda_html=None):
    """Retry public options; preserve dated user-reviewed evidence without faking a recheck."""
    from eligibility import mark_session
    report={'bookingCheckedAt':now.isoformat(),'reviewNeeded':True,'reviewedSessions':0,'liveSessions':0}
    if form_url!=WEEKEND_FORM and (not agenda_html or weekend_form(agenda_html,AGENDA)!=form_url):
        report['formStatus']='unlinked-form'
        return [],report
    programme=programme or {}
    valid_fallback=programme.get('sourceUrl')==WEEKEND_FORM and form_url==WEEKEND_FORM
    reviewed=now;until=now.date()-timedelta(days=1);year=None
    try:
        year=int(programme['year']);until=date.fromisoformat(programme['validUntil'])
        reviewed=datetime.fromisoformat(programme['reviewedAt'])
        valid_fallback=valid_fallback and reviewed.tzinfo is not None and reviewed<=now and reviewed.date()<=until<=reviewed.date()+timedelta(days=45)
    except (KeyError,TypeError,ValueError):valid_fallback=False
    if valid_fallback:report.update(programmeReviewedAt=reviewed.isoformat(),programmeValidUntil=until.isoformat())
    choices=public_choices(html) if html and not error else []
    soup=BeautifulSoup(html or '', 'html.parser')
    # A year must belong to the form title/description, never a copyright footer.
    heading=' '.join(n.get_text(' ',strip=True) for n in soup.select('h1, [role="heading"][aria-level="1"], .freebirdFormviewerViewHeaderDescription, .cBGGJ'))
    years=set(re.findall(r'\b20\d{2}\b',heading))
    explicit_year=int(next(iter(years))) if len(years)==1 else None
    live_year=explicit_year if explicit_year is not None else year if valid_fallback and now.date()<=until else None
    parsed=[parse_choice(c,live_year) for c in choices]
    explicitly_dated=explicit_year is not None or (bool(choices) and all(re.search(r'/20\d{2}',c) for c in choices))
    live_until=now.date()+timedelta(days=45) if explicitly_dated else until
    complete=bool(choices) and all(parsed) and (explicitly_dated or all(date.fromisoformat(p['date'])<=until for p in parsed if p))
    labels=choices if complete else programme.get('choices',[]) if valid_fallback else []
    report['reviewNeeded']=not complete
    report['formStatus']='public-options' if complete else 'access-blocked' if error else 'needs-review'
    report['changedChoices']=[c for c in choices if c not in programme.get('choices',[])]
    report['removedChoices']=[c for c in programme.get('choices',[]) if c not in choices] if complete else []
    result=[]
    if not complete and now.date()>until:return result,report
    for label in labels:
        row=parse_choice(label,live_year if complete else year,None if complete else programme.get('corrections'))
        if not row or not (now.date() if complete else reviewed.date())<=date.fromisoformat(row['date'])<=(live_until if complete else until):continue
        raw={'name':row['title'],'description':f"Atividade em família, dos {row['minMonths']} aos {row['maxMonths']} meses. Criança acompanhada por 1 ou 2 adultos.",'startDate':row['date']+'T'+row['start'],'endDate':row['date']+'T'+row['end'] if row['end'] else None,'location':{'name':'PlayLab Porto','address':'Rua de Alves Redol 386, Porto'},'url':WEEKEND_FORM,'offers':{'price':18 if 'messy play' in row['title'].lower() else 15,'priceCurrency':'EUR','url':WEEKEND_FORM}}
        if complete or label not in programme.get('choices',[]) or form_url!=WEEKEND_FORM:raw['offers'].pop('price',None)
        raw['url']=form_url;raw['offers']['url']=form_url
        source_url=WEEKEND_FORM if form_url==WEEKEND_FORM else AGENDA
        event=make_event(raw,source_url,'PlayLab Porto',now)
        if event:event['sourceUrl']=source_url
        if not event:continue
        if re.search(r'baby lab|messy play',row['title'],re.I):event['category']='Sensorial'
        event.update(sourceType='playlab-programme',confidence='official-programme' if complete else 'reviewed-programme',evidenceDate=(now if complete else reviewed).date().isoformat(),evidence='Opções do formulário consultadas; vagas por confirmar.' if complete else 'Programa do formulário revisto a partir de imagem partilhada. Vagas e alterações posteriores por confirmar.')
        if complete:
            mark_session(event,source_url,now,'official-programme');event['sessionEvidence']['formUrl']=form_url;report['liveSessions']+=1
        else:
            mark_session(event,WEEKEND_FORM,reviewed,'reviewed-playlab-programme')
            event['sessionEvidence'].update(reviewedAt=reviewed.isoformat(),validUntil=until.isoformat(),originalChoice=row['originalChoice'])
            event['sessionEvidence']['reviewDigest']=evidence_digest(event['sessionEvidence'])
            report['reviewedSessions']+=1
        result.append(event)
    return result,report


def programme_watch(agenda_html,newsletter_html,form_url,form_html,previous,now,reviewed_at=None):
    """Compare public programme references, not volatile Google page scripts.

    A changed poster or newsletter is a review signal, never session evidence.
    Keep that signal pending across unchanged runs until a newer review exists.
    """
    snapshot=dict(previous.get('snapshot',{}))
    if agenda_html:
        soup=BeautifulSoup(agenda_html,'html.parser')
        # Google Sites rotates signed image URLs on ordinary page reads.
        # Use its published revision and stable image/link structure instead.
        revisions={n['data-last-updated-at-time'] for n in soup.select('[data-last-updated-at-time]')}
        if len(revisions)==1:snapshot['agendaRevision']=next(iter(revisions))
        images=[]
        for img in soup.select('img[src]'):
            if img.find_parent(['header','nav']):continue
            if 'sitesv-images' not in img['src']:continue
            anchor=img.find_parent('a',href=True)
            images.append('google-sites-image:'+str(anchor.get('href','') if anchor else '')+':'+str(img.get('alt',img.get('aria-label',''))))
        snapshot['agendaImages']=sorted(images)
        snapshot['weekendForm']=form_url
    if newsletter_html:snapshot['newsletterIssues']=sorted(u for u,_ in programme_links(newsletter_html,'https://playlabporto.beehiiv.com/'))
    if form_html:
        choices=public_choices(form_html)
        if choices:snapshot['publicChoices']=sorted(choices)
    before=previous.get('snapshot',{});reasons=[]
    legacy_images=any('sitesv-images' in u for u in before.get('agendaImages',[]))
    if 'agendaImages' in before and not legacy_images and snapshot.get('agendaImages')!=before['agendaImages']:reasons.append('Estrutura de imagens da agenda alterada')
    if 'agendaRevision' in before and snapshot.get('agendaRevision')!=before['agendaRevision']:reasons.append('Agenda oficial atualizada')
    if 'weekendForm' in before and snapshot.get('weekendForm')!=before['weekendForm']:reasons.append('Formulário de fim de semana alterado ou removido')
    if 'newsletterIssues' in before and set(snapshot.get('newsletterIssues',[]))-set(before['newsletterIssues']):reasons.append('Nova newsletter publicada')
    if 'publicChoices' in before and snapshot.get('publicChoices')!=before['publicChoices']:reasons.append('Opções públicas do formulário alteradas')
    state={**previous,'snapshot':snapshot,'checkedAt':now.isoformat()}
    if reasons:state.update(changedAt=now.isoformat(),changeReasons=reasons,pendingReview=True)
    try:
        if reviewed_at and state.get('changedAt') and datetime.fromisoformat(reviewed_at)>=datetime.fromisoformat(state['changedAt']):state['pendingReview']=False
    except (TypeError,ValueError):pass
    return state,reasons
