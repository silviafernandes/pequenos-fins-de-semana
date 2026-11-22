"""Bounded discovery in official city agendas; admission is checked per event."""
import json
import re
from html import unescape
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from eligibility import mark_session, normalized
from maia import listing_expired, page_url as maia_page_url

EVENT_PATHS={
    'agenda-porto.pt':r'^/evento/[^/]+/?$',
    'cm-matosinhos.pt':r'^/evento/[^/]+/?$',
    'culturamatosinhos.pt':r'^/eventos/evento-\d+/[^/]+/?$',
    'cm-maia.pt':r'/evento(?:-\d+)?/[^/]+/?$',
    'visitmaia.pt':r'^/(?:public/)?eventos/[^/]+/?$',
}
PROVIDERS={
    'casadamusica.com':'/event/',
    'bibliotecasdoporto.pt':'/evento/',
    'museudoporto.pt':'/recurso/',
}


def agenda_links(html,url,now):
    soup=BeautifulSoup(html,'html.parser')
    hostname=(urlparse(url).hostname or '').removeprefix('www.')
    pattern=EVENT_PATHS.get(hostname)
    if not pattern:return []
    base=soup.find('base',href=True)
    base=urljoin(url,base['href']) if base else url
    links={}
    for a in soup.select('a[href]'):
        target=urljoin(base,a['href']);parsed=urlparse(target)
        if parsed.scheme!='https' or (parsed.hostname or '').removeprefix('www.')!=hostname or not re.search(pattern,parsed.path):continue
        if listing_expired(a,now.date()):continue
        title=a.get_text(' ',strip=True) or a.get('aria-label','') or a.get('title','')
        # Porto uses empty overlay anchors beside the visible title.
        card=a.find_parent(attrs={'data-bl-name':'Card. Card Event'})
        heading=card.select_one('[data-bl-name="Title"]') if card else None
        if heading:title=heading.get_text(' ',strip=True)
        if not title:title=unescape(unquote(parsed.path.rstrip('/').rsplit('/',1)[-1])).replace('-',' ')
        target=maia_page_url(target) if hostname=='cm-maia.pt' else parsed._replace(query='',fragment='').geturl()
        links.setdefault(target,title[:180])
    return list(links.items())


def provider_links(html,url):
    """Only the event's explicit information link, to known official providers."""
    soup=BeautifulSoup(html,'html.parser')
    base=soup.find('base',href=True)
    base=urljoin(url,base['href']) if base else url
    links=[]
    for a in soup.select('a[href]'):
        if normalized(a.get_text(' ',strip=True)) not in ('mais info','mais informacoes','saber mais','site oficial','ver programa'):continue
        target=urljoin(base,a['href']);parsed=urlparse(target)
        prefix=PROVIDERS.get((parsed.hostname or '').removeprefix('www.'))
        if parsed.scheme=='https' and prefix and parsed.path.startswith(prefix) and target not in links:links.append(target)
    return links[:1]


def visitmaia_sessions(html,url,now,make_event):
    parsed=urlparse(url)
    if (parsed.hostname or '').removeprefix('www.')!='visitmaia.pt' or not re.fullmatch(EVENT_PATHS['visitmaia.pt'],parsed.path):return []
    soup=BeautifulSoup(html,'html.parser')
    fields={}
    for row in soup.select('table tr'):
        cells=row.find_all(['th','td'],recursive=False)
        if len(cells)==2:fields[normalized(cells[0].get_text(' ',strip=True))]=cells[1].get_text(' ',strip=True)
    audience=fields.get('mais informacoes','')
    all_ages=bool(re.search(r'\b(?:todas as idades|todas a[s]? faixas etarias)\b',normalized(audience)))
    title=soup.select_one('h4.u-text-1')
    if re.search(r'\b(?:cancelad[oa]|adiad[oa])\b',normalized((title.get_text(' ',strip=True) if title else '')+' '+audience)):return []
    results=[]
    calendars=[]
    for node in soup.select('.atcb'):
        try:data=json.loads(node.get_text())
        except (ValueError,TypeError):continue
        if isinstance(data,dict):calendars.append(data)
    names={data['name'] for data in calendars if isinstance(data.get('name'),str)}
    for data in calendars:
        if not isinstance(data,dict) or data.get('timeZone')!='Europe/Lisbon':continue
        if not isinstance(data.get('name'),str) or not data['name']:continue
        if data.get('endDate') and data['endDate']!=data.get('startDate'):continue
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',data.get('startTime') or ''):continue
        venue=data.get('location')
        if not isinstance(venue,str) or normalized(venue)!=normalized(fields.get('local')):continue
        raw={'name':unescape(data.get('name','')),'description':audience,'startDate':str(data.get('startDate',''))+'T'+data['startTime'],'url':url,'location':{'name':venue,'address':'Maia'}}
        if len(names)==1 and title:raw['name']=title.get_text(' ',strip=True)
        if all_ages:
            # All ages explicitly includes the entire 0–18 childhood interval.
            # This finite internal interval is not an upper admission limit;
            # retain the publisher's unrestricted wording in ageText/evidence.
            raw['typicalAgeRange']='0–18 anos'
        if isinstance(data.get('endDate'),str) and isinstance(data.get('endTime'),str):raw['endDate']=data['endDate']+'T'+data['endTime']
        event=make_event(raw,url,'Maia · Visit Maia',now)
        if not event:continue
        event.update(sourceType='visitmaia-calendar',ageText='Todas as idades' if all_ages else audience,price=fields.get('preco') or 'Por confirmar',category='Festival' if 'natal' in normalized(raw['name']) else event['category'],evidence='Dia, hora e local no calendário publicado pelo Visit Maia; admissão verificada nas informações do próprio evento. Vagas por confirmar.')
        mark_session(event,url,now,'official-published-calendar')
        if all_ages:event['sessionEvidence'].update(admission='all-ages',ageText=audience)
        results.append(event)
    return list({(e['date'],e['start'],e['title'],e['venue']):e for e in results}.values())
