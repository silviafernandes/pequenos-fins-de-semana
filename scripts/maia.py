"""Maia library programmes: labelled HTML and rechecked, reviewed PDF artwork.

PDF date headings can be artwork rather than extractable text. A visual review is
valid only while the same document is linked from the same current event page.
Changed documents are reported for review, never silently reused.
"""
import hashlib
import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from eligibility import mark_session, normalized

INDEX='https://www.cm-maia.pt/viver/cultura/equipamentos-culturais/biblioteca/noticias-eventos'
DETAIL='https://www.cm-maia.pt/viver/cultura/noticias-e-eventos/evento-12/'
MAX_PAGES=8
MAX_DOCUMENTS=2
MONTHS=('jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez')


def page_url(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ('www.cm-maia.pt','cm-maia.pt','app.cm-maia.pt'):return None
    match=re.search(r'/evento(?:-\d+)?/([^/]+)/*$',parsed.path)
    return DETAIL+match[1] if match else None


def period(soup):
    try:
        start=date.fromisoformat(soup.select_one('.atc_date_start').get_text(strip=True)[:10])
        end=date.fromisoformat(soup.select_one('.atc_date_end').get_text(strip=True)[:10])
        return (start,end) if start<=end else None
    except (AttributeError,ValueError):return None


def listing_expired(link,today):
    block=link.find_parent(class_='linl_block')
    if not block:return False
    months=block.select('.dates .mes_curto, .dates .mes');years=block.select('.dates .ano');days=block.select('.dates .dia')
    if not months or not years or not days:return False
    try:
        label=normalized(months[-1].get_text())
        month=int(label) if label.isdigit() else MONTHS.index(label[:3])+1
        year=int(years[-1].get_text().strip().lstrip("'’"))
        if year<100:year+=2000
        return date(year,month,int(days[-1].get_text()))<today
    except (ValueError,TypeError):return False


def venue_name(text):
    value=normalized(text)
    return {
        'biblioteca municipal':'Biblioteca Municipal da Maia',
        'biblioteca municipal da maia':'Biblioteca Municipal da Maia',
        'sala do conto':'Biblioteca Municipal da Maia · Sala do Conto',
        'sala do conto da biblioteca municipal':'Biblioteca Municipal da Maia · Sala do Conto',
        'sala de conferencias da biblioteca municipal':'Biblioteca Municipal da Maia · Sala de Conferências',
        'cafe concerto do forum da maia':'Café Concerto do Fórum da Maia',
        'grande auditorio do forum da maia':'Grande Auditório do Fórum da Maia',
    }.get(value)


def monthly_sessions(soup,url,now,make_event):
    heading=soup.select_one('h1.pageTitle')
    dates=period(soup)
    if not heading or not normalized(heading.get_text()).startswith('agenda biblioteca municipal da maia') or not dates:return []
    first,last=dates
    if (first.year,first.month)!=(last.year,last.month):return []
    content=soup.select_one('.event_detail > .text .writer_text')
    if not content:return []
    events=[]
    for html in re.split(r'<hr\b[^>]*>',str(content),flags=re.I):
        block=BeautifulSoup(html,'html.parser')
        paragraph=block.find('p')
        headings=paragraph.find_all('strong') if paragraph else []
        if len(headings)<2:continue
        title=headings[-1].get_text(' ',strip=True)
        fields={}
        for p in block.find_all('p'):
            match=re.fullmatch(r'([^|]+)\|\s*(.+)',p.get_text(' ',strip=True))
            if match:fields[normalized(match[1])]=match[2]
        venue=venue_name(fields.get('local',''))
        days=re.sub(r'\b(?:seg|ter|qua|qui|sex|sáb|sab|dom)\.?\s*','',fields.get('data',''),flags=re.I)
        times=fields.get('horario','').split('(')[0].strip()
        if not venue or not re.fullmatch(r'\d{1,2}(?:\s*(?:,|e)\s*\d{1,2})*',days):continue
        # Lists of start times are sessions; opening-hour ranges are not.
        if not re.fullmatch(r'\d{1,2}[h:]\d{2}(?:\s*(?:,|e)\s*\d{1,2}[h:]\d{2})*',times,re.I):continue
        duration=re.search(r'\b(\d{1,3})\s*(?:minutos|min\b|m\b)',fields.get('duracao',''),re.I)
        for day in re.findall(r'\d{1,2}',days):
            for hour,minute in re.findall(r'(\d{1,2})[h:](\d{2})',times,re.I):
                try:start=datetime(first.year,first.month,int(day),int(hour),int(minute))
                except ValueError:continue
                if not first<=start.date()<=last:continue
                raw={'name':title,'description':fields.get('publico alvo',''),'startDate':start.isoformat(),'url':url,'location':{'name':venue,'address':'Maia'}}
                if duration:raw['endDate']=(start+timedelta(minutes=int(duration[1]))).isoformat()
                event=make_event(raw,url,'Biblioteca da Maia',now)
                if not event:continue
                event.update(sourceType='maia-monthly-programme',indoor=True,ageText=fields['publico alvo'],evidence='Sessão lida no bloco próprio do programa mensal oficial; vagas por confirmar.')
                if fields.get('preco'):event['price']=fields['preco']
                if fields.get('inscricoes'):event['registrationNote']='Inscrições: '+fields['inscricoes']+'. Disponibilidade por confirmar.'
                events.append(mark_session(event,url,now,'official-programme'))
    return events


def collect(source,get_page,fetch_document,programme,now,make_event):
    html,error=get_page(source['url'])
    links=[]
    if html:
        soup=BeautifulSoup(html,'html.parser')
        links=[page_url(urljoin(source['url'],a['href'])) for a in soup.select('.linl_overlay[href]') if not listing_expired(a,now.date())]
    reviews=programme.get('programmes',[])
    expired=set()
    for review in reviews:
        try:
            if date.fromisoformat(review['dateRange'][1])<now.date():expired.add(page_url(review.get('pageUrl','')))
        except (KeyError,IndexError,ValueError,TypeError):continue
    pinned=[page_url(u) for u in source.get('programmeUrls',[])]+[page_url(r.get('pageUrl','')) for r in reviews]
    pinned=[u for u in pinned if u not in expired]
    candidates=list(dict.fromkeys(u for u in pinned+links if u))
    report={'ok':not bool(error),'readMode':'maia-programmes','detailErrors':([{'url':source['url'],'error':error}] if error else []),'documentChecks':[],'reviewCandidates':[],'candidateLinks':len(candidates),'truncated':len(candidates)>MAX_PAGES}
    pages={}
    cache={}
    for url in candidates[:MAX_PAGES]:
        page,page_error=get_page(url)
        if page_error or not page:
            report['detailErrors'].append({'url':url,'error':page_error or 'Página vazia'});continue
        soup=BeautifulSoup(page,'html.parser')
        dates=period(soup)
        pages[url]=[]
        if not dates or dates[1]<now.date() or dates[0]>now.date()+timedelta(days=45):continue
        heading=soup.select_one('h1.pageTitle')
        title=heading.get_text(' ',strip=True) if heading else ''
        if re.search(r'\b(?:cancelad[oa]|adiad[oa])\b',normalized(title)):continue
        pages[url]=monthly_sessions(soup,url,now,make_event)
        documents=[]
        for a in soup.select('.event_detail > .text a[href]'):
            doc=urljoin(url,a['href']);parsed=urlparse(doc)
            if parsed.scheme=='https' and parsed.hostname=='www.cm-maia.pt' and parsed.path.startswith('/cmmaia/uploads/writer_file/document/') and parsed.path.lower().endswith('.pdf') and doc not in documents:documents.append(doc)
        for review in reviews:
            if page_url(review.get('pageUrl',''))==url and review.get('documentUrl') not in documents:
                report['documentChecks'].append({'pageUrl':url,'documentUrl':review.get('documentUrl'),'checkedAt':now.isoformat(),'status':'needs-review','reason':'O programa revisto deixou de estar ligado na página.'})
        for document in documents[:MAX_DOCUMENTS]:
            if document not in cache:cache[document]=fetch_document(document)
            content,doc_error=cache[document]
            check={'pageUrl':url,'documentUrl':document,'checkedAt':now.isoformat()}
            report['documentChecks'].append(check)
            if doc_error or not content:
                check.update(status='unavailable',error=doc_error or 'Documento vazio')
                report['detailErrors'].append({'url':document,'error':check['error']});continue
            digest=hashlib.sha256(content).hexdigest();check['sha256']=digest
            review=next((r for r in reviews if page_url(r.get('pageUrl',''))==url and r.get('documentUrl')==document and r.get('sha256')==digest and r.get('pageTitle')==title and r.get('dateRange')==[d.isoformat() for d in dates]),None)
            if not review:
                check['status']='needs-review';continue
            try:reviewed=datetime.fromisoformat(review['reviewedAt'])
            except (KeyError,TypeError,ValueError):check['status']='needs-review';continue
            if reviewed.tzinfo is None or reviewed>now:check['status']='needs-review';continue
            check.update(status='reviewed',reviewedAt=review['reviewedAt'])
            for session in review.get('sessions',[]):
                try:
                    day=date.fromisoformat(session['date'])
                    raw={'name':session['title'],'description':session['ageText']+'. '+session.get('description',''),'startDate':session['date']+'T'+session['start'],'url':url,'location':{'name':session['venue'],'address':'Maia'}}
                except (KeyError,TypeError,ValueError):continue
                if not dates[0]<=day<=dates[1]:continue
                if session.get('end'):raw['endDate']=session['date']+'T'+session['end']
                event=make_event(raw,url,'Biblioteca da Maia',now)
                if not event:continue
                event.update(sourceType='maia-reviewed-programme',category=session.get('category','Bibliotecas'),indoor=True,ageText=session['ageText'],price=session.get('price') or 'Por confirmar',registrationNote=session.get('registrationNote'),evidence='Programa oficial revisto visualmente; PDF novamente consultado e idêntico.')
                mark_session(event,url,now,'reviewed-official-programme')
                event['sessionEvidence'].update(documentUrl=document,documentSha256=digest,reviewedAt=review['reviewedAt'])
                pages[url].append(event)
        if len(documents)>MAX_DOCUMENTS:report['truncated']=True
    for lead in programme.get('leads',[]):
        try:age=now.date()-date.fromisoformat(lead['observedAt'])
        except (KeyError,TypeError,ValueError):continue
        if timedelta(0)<=age<=timedelta(days=45):report['reviewCandidates'].append(lead)
    report.update(lastLinks=list(pages),relevantLinks=len(candidates),detailsChecked=len(pages),parsedSessions=len({(u,e['date'],e['start'],e['title'],e['venue']) for u,items in pages.items() for e in items}),reviewNeeded=bool(report['reviewCandidates']) or any(c['status']=='needs-review' for c in report['documentChecks']))
    return pages,report
