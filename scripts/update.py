#!/usr/bin/env python3
"""Conservative scheduled discovery for public event pages.

- Starts from primary sources and public aggregators.
- Finds *leads*; a public link/form does not prove an open registration.
- Auto-adds events only when a structured Event item includes an eligible local
  venue, weekend date, and an explicit suitable age band.
- Stores first-seen data, evidence and scan failures. No account automation.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from urllib.robotparser import RobotFileParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from eligibility import mark_session, classify, assess, normalized
from adapters import organiser_sessions
from telegram_alerts import send_alerts, report as report_telegram
from allegrow import collect as collect_allegrow
from posters import from_posters

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data'
PT = ZoneInfo('Europe/Lisbon')
HEADERS = {'User-Agent': 'PequenosFinsDeSemana/0.1 (public event discovery; gentle checks; contact via repository)'}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
TIMEOUT = 14
MAX_LINKS = 12
MAX_DETAILS = 3
LIMIT_DISCOVERIES = 160

KEYWORDS = re.compile(r'\b(?:beb[eéê]s?|bebeteca|primeira.inf[aâ]ncia|crian[cç]as?|infantil|fam[ií]lias?|hist[oó]rias?|contos?|sensorial|music(?:a|al)|musicais|teatro|oficina|workshop|papi|atividades?|eventos?)\b', re.I)
STRONG = re.compile(r'\b(?:bebeteca|beb[eéê]s?|primeira.inf[aâ]ncia|0\s*[-–]\s*3|6\s*[-–]\s*36|12\s*[-–]\s*36|18\s*[-–]\s*36|sensorial|papi|hist[oó]rias?|m[uú]sica\s+para|teatro\s+para)\b', re.I)
LINK_PATH = re.compile(r'/(?:evento|event|atividade|workshop|oficina|bebes|bebe|baby|programa|agenda|bilhete|inscri)', re.I)
FORM_HOST = re.compile(r'(?:forms\.gle|docs\.google\.com/forms|forms\.office\.com|eventbrite\.|bol\.pt|ticketline\.|bilheteiraonline\.)', re.I)
MONTHS = {'janeiro':1,'fevereiro':2,'março':3,'marco':3,'abril':4,'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,'outubro':10,'novembro':11,'dezembro':12}
LOCAL = re.compile(r'matosinhos|porto|maia|gaia|senhora da hora|são mamede|sao mamede|boavista|bonfim|leça|leca',re.I)


def now_pt():
    return datetime.now(PT)

def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def load(path, default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError): return default

def save(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=False)+'\n',encoding='utf-8')

def canonical(url):
    url, _ = urldefrag(str(url).strip())
    try:
        p=urlparse(url)
        if p.scheme not in ('http','https') or not p.hostname: return None
        # Preserve booking token/query links; remove meaningless trackers only.
        return url
    except ValueError: return None

ROBOTS = {}
ROBOTS_ERRORS = {}

def allowed_url(url):
    parsed = urlparse(url)
    origin = f'{parsed.scheme}://{parsed.netloc}'
    if origin not in ROBOTS:
        parser = RobotFileParser()
        try:
            response = SESSION.get(origin+'/robots.txt', timeout=TIMEOUT)
            if response.status_code in (404, 410):
                parser.parse([])
            elif response.ok:
                parser.parse(response.text.splitlines())
            else:
                ROBOTS_ERRORS[origin] = f'robots.txt unavailable: HTTP {response.status_code}'
                return False
        except requests.RequestException as error:
            ROBOTS_ERRORS[origin] = f'robots.txt unavailable: {type(error).__name__}'
            return False
        ROBOTS[origin] = parser
    allowed = ROBOTS[origin].can_fetch(HEADERS['User-Agent'], url)
    if not allowed: ROBOTS_ERRORS[origin] = 'robots.txt disallows this URL'
    return allowed

def fetch(url, content_types=None, binary=False):
    try:
        if not allowed_url(url): return None, ROBOTS_ERRORS.get(f'{urlparse(url).scheme}://{urlparse(url).netloc}', 'Robots policy unavailable')
        time.sleep(.35)
        for _ in range(5):
            if not allowed_url(url): return None, 'Robots policy disallows redirect destination'
            res=SESSION.get(url,timeout=TIMEOUT,allow_redirects=False)
            if res.is_redirect:
                url=urljoin(url,res.headers['Location'])
                continue
            break
        else: return None, 'Too many redirects'
        res.raise_for_status()
        if len(res.content)>3_000_000: raise ValueError('Page too large')
        typ=res.headers.get('Content-Type','')
        if typ and not any(t in typ for t in (content_types or ('text/html','application/xhtml','application/ld+json'))):
            raise ValueError('Unexpected content type')
        if binary:return res.content,None
        try: text=res.content.decode('utf-8')
        except UnicodeDecodeError: text=res.text
        return text, None
    except (requests.RequestException,ValueError) as e:
        return None, f'{type(e).__name__}: {str(e)[:130]}'

def fetch_json(url):
    content,error=fetch(url,content_types=('application/json',))
    if error:return None,error
    try:return json.loads(content),None
    except (ValueError,TypeError):return None,'Resposta JSON pública inválida'


def strip_text(s):
    return re.sub(r'\s+',' ',s or '').strip()

def links_from(html, base):
    soup=BeautifulSoup(html,'html.parser')
    seen={}
    for a in soup.find_all('a',href=True):
        url=canonical(urljoin(base,a['href']))
        if not url: continue
        text=strip_text(a.get_text(' ',strip=True) or a.get('aria-label','') or a.get('title',''))
        if len(text)>180: text=text[:180]
        seen.setdefault(url,text or urlparse(url).path.rsplit('/',1)[-1].replace('-',' '))
    return list(seen.items()),soup

def possible_link(url,title):
    if FORM_HOST.search(url) or excludes_under_three(title): return False
    if any(k in url.lower() for k in ('wp-admin','login','privacy','politica-de','newsletter','contactos','/tag/','/category/')):return False
    return bool((STRONG.search(title) and (LINK_PATH.search(url) or len(title)>18)) or (KEYWORDS.search(title) and LINK_PATH.search(url) and len(title)>12))

def extract_json_ld(soup):
    found=[]
    for tag in soup.select('script[type="application/ld+json"]'):
        try: js=json.loads(tag.string or tag.get_text())
        except (ValueError,TypeError):continue
        stack=[js]
        while stack:
            x=stack.pop()
            if isinstance(x,list): stack.extend(x)
            if isinstance(x,dict):
                # Event items also appear inside ItemList, item and subEvent.
                stack.extend(v for v in x.values() if isinstance(v,(dict,list)))
                typ=x.get('@type',[])
                if isinstance(typ,str): typ=[typ]
                if 'Event' in typ or any(str(y).endswith('Event') for y in typ):found.append(x)
    return found

def age_band(text):
    """Parse explicit age *ranges*; intentionally reject vague 'for families'."""
    t=unicodedata.normalize('NFKC',strip_text(text)).lower().replace('–','-').replace('—','-')
    def match(p, factors):
        m=re.search(p,t)
        if not m:return None
        lo,hi=int(m.group(1))*factors[0],int(m.group(2))*factors[1]
        return (lo,hi) if 0<=lo<=hi<=216 else None
    ranged = (match(r'(\d{1,2})\s*(?:meses|m[eê]s|months)\s*(?:aos|a|at[eé]|to|-)\s*(\d{1,2})\s*(?:meses|m[eê]s|months)',(1,1))
        or match(r'(\d{1,2})\s*(?:meses|m[eê]s)\s*(?:aos|a|at[eé]|-)\s*(\d{1,2})\s*(?:anos|years)',(1,12))
        or match(r'(\d{1,2})\s*(?:anos|years)\s*(?:aos|a|at[eé]|to|-)\s*(\d{1,2})\s*(?:anos|years)',(12,12))
        or match(r'\b(\d{1,2})\s*(?:aos|a|at[eé]|-)\s*(\d{1,2})\s*(?:anos|years)\b',(12,12))
        or match(r'\b(\d{1,2})\s*(?:aos|a|at[eé]|-)\s*(\d{1,2})\s*(?:meses|months)\b',(1,1)))

    if ranged: return ranged
    lower = minimum_age(t)
    return (lower,144) if lower is not None and lower <= 216 else None


def minimum_age(text):
    text=unicodedata.normalize('NFKC',strip_text(text)).lower()
    unit=r'(meses|mês|mes|anos?|years?|months?|a\b)'
    patterns=[
        rf'(?:a partir d[eo](?:s)?|desde (?:os )?|maiores de|mais de|idade m[ií]nima(?: de)?|m[ií]nimo(?: de)?)\s*(\d{{1,2}})\s*{unit}',
        rf'\+\s*(\d{{1,2}})\s*{unit}',
        rf'\b(\d{{1,2}})\s*\+\s*{unit}',
        rf'\b(\d{{1,2}})\s*{unit}\s*\+',
        r'\bm/(\d{1,2})\b',
        r'\b(\d{1,2})\s*\+(?!\s*(?:meses|mês|anos?|years?|months?|a\b))'
    ]
    ages=[]
    for pattern in patterns:
        for match in re.finditer(pattern,text):
            value=int(match[1]); unit_text=match[2] if len(match.groups())>1 else 'anos'
            ages.append(value if unit_text.startswith(('mês','mes','month')) else value*12)
    return max(ages) if ages else None


def excludes_under_three(text):
    lower=minimum_age(text)
    if lower is not None and lower >= 36: return True
    band=age_band(text)
    return band is not None and band[0] >= 36


def qualify_discovery(item):
    """Only publish announcements with explicit evidence of admission below 36 months."""
    if excludes_under_three(item.get('title','')): return None
    # A dated announcement already in the past is not a new plan.
    dated=re.search(r'\b(?:seg|ter|qua|qui|sex|s[áa]b|dom)\s+(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\b',item.get('title',''),re.I)
    if dated:
        month=['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'].index(dated[2].lower())+1
        try: day=datetime(now_pt().year,month,int(dated[1]),tzinfo=PT).date()
        except ValueError: return None
        if day < now_pt().date(): return None
    band=age_band(item.get('title',''))
    if band is None and item.get('ageEvidence') in ('official-adapter','structured-event'):
        lo,hi=item.get('minMonths'),item.get('maxMonths')
        if isinstance(lo,(int,float)) and isinstance(hi,(int,float)): band=(lo,hi)
    if band is None or not 0 <= band[0] < 36 or band[1] < band[0]: return None
    return dict(item,minMonths=band[0],maxMonths=band[1],ageEvidence=item.get('ageEvidence') or 'announcement-title')


def age_from_event(item):
    parts=[]
    for k in ('description','name','audience','typicalAgeRange'):
        v=item.get(k,'')
        if isinstance(v,str):parts.append(v)
        elif isinstance(v,dict):parts.extend(str(v.get(x,'')) for x in ('name','description','suggestedMinAge','suggestedMaxAge'))
    return age_band(' '.join(parts))

def parse_dt(value):
    if not isinstance(value,str):return None
    try:return datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:return None

def make_event(item,source_url,source_name,now):
    # Future *weekend* in next six weeks; require explicit child age, local venue.
    if any(status in str(item.get('eventStatus','')).lower() for status in ('cancelled','canceled','postponed')):return None
    if re.search(r'\b(?:cancelad[oa]|adiad[oa])\b',str(item.get('name','')),re.I):return None
    st=parse_dt(item.get('startDate'))
    if not st or not re.search(r"T\d{2}:\d{2}", item.get("startDate", "")):return None
    if st.tzinfo:st=st.astimezone(PT)
    if st.weekday()<5 or not (now.date()<=st.date()<= (now+timedelta(days=45)).date()):return None
    age=age_from_event(item)
    if not age or age[0]>=36 or excludes_under_three(' '.join(str(item.get(k,'')) for k in ('name','description','typicalAgeRange'))):return None
    loc=item.get('location',{})
    if isinstance(loc,list):loc=loc[0] if loc else {}
    if isinstance(loc,str):where=loc;venue=loc
    else:
        addr=loc.get('address','') if isinstance(loc,dict) else ''
        if isinstance(addr,dict):addr=' '.join(str(addr.get(k,'')) for k in ('streetAddress','addressLocality','addressRegion'))
        venue=str(loc.get('name','') or addr) if isinstance(loc,dict) else ''
        where=venue+' '+str(addr)
    if not LOCAL.search(where):return None
    title=strip_text(item.get('name',''))
    if not title or not KEYWORDS.search(title+' '+item.get('description','')):return None
    end=parse_dt(item.get('endDate'))
    if end and end.tzinfo:end=end.astimezone(PT)
    if end and (not re.search(r'T\d{2}:\d{2}',item.get('endDate','')) or end.date()!=st.date() or end.replace(tzinfo=None)<=st.replace(tzinfo=None)):
        end=None
    link=canonical(item.get('url')) or source_url
    offer=item.get('offers') or {}
    if isinstance(offer,list):offer=offer[0] if offer else {}
    booking=canonical(offer.get('url')) if isinstance(offer,dict) else None
    price='Por confirmar'
    if isinstance(offer,dict) and offer.get('price') is not None:
        price=f"{offer['price']} {offer.get('priceCurrency','EUR')}"
    pic=item.get('image');pic=pic[0] if isinstance(pic,list) and pic else pic
    if isinstance(pic,dict):pic=pic.get('url')
    category='Bibliotecas' if 'biblioteca' in where.lower() else ('Sensorial' if re.search(r'sensorial|pintura|cerâmica|barro',title,re.I) else 'Música' if re.search(r'música|concerto|som',title,re.I) else 'Outras')
    slug=hashlib.sha256(f'{link}|{st.date()}|{st.hour}:{st.minute}|{normalized(title)}|{normalized(venue)}'.encode()).hexdigest()[:13]
    event = {'id':'auto-'+slug,'title':title[:140],'date':st.date().isoformat(),'start':st.strftime('%H:%M'),'end':end.strftime('%H:%M') if end else None,'minMonths':age[0],'maxMonths':age[1],'ageText':f'{age[0]}–{age[1]} meses','price':price,'venue':venue[:130],'area':re.search(LOCAL,where).group(0).title(),'category':category,'kind':'Evento publicado','description':strip_text(BeautifulSoup(item.get('description',''),'html.parser').get_text(' ',strip=True))[:260] or 'Atividade para crianças pequenas.','bookingUrl':booking,'sourceUrl':link,'sourceName':source_name,'imageUrl':canonical(pic),'status':'unverified','openingAt':None,'capacity':None,'indoor':None,'confidence':'structured-official' if 'Oficina' in source_name else 'structured-listing','evidence':'Dados estruturados do evento; vagas não confirmadas.','evidenceDate':now.date().isoformat(),'discoveredAt':stamp(),'sourceType':'auto-jsonld','priority':48}
    return mark_session(event,source_url,now,'structured-event')

def opening_dates(html,year):
    text=unicodedata.normalize('NFKC', strip_text(BeautifulSoup(html,'html.parser').get_text(' ',strip=True)))
    pat=re.compile(r'inscri[cç][oõ]es\s+(?:abrem|abertas?\s+(?:a\s+partir\s+de|em))\s*(?:no\s+dia\s+|dia\s+|a\s+)?(\d{1,2})\s+de\s+([a-zçãé]+)(?:\s+de\s+(\d{4}))?\s*(?:[àa]s|as)\s*(\d{1,2})\s*(?:h|:)\s*(\d{2})',re.I)
    dates=[]
    for m in pat.finditer(text):
       month=MONTHS.get(m.group(2).lower())
       if not month:continue
       try:
           year_=int(m.group(3) or year);hour=int(m.group(4) or 0);minute=int(m.group(5) or 0)
           dt=datetime(year_,month,int(m.group(1)),hour,minute,tzinfo=PT)
           dates.append(dt.isoformat(timespec='minutes'))
       except ValueError:pass
    return list(dict.fromkeys(dates))[:8]

def booking_links(html, base):
    links, soup = links_from(html, base)
    candidates = [u for u, _ in links]
    candidates += re.findall(r'https?://[^\s<>"\']+', soup.get_text(' ', strip=True))
    return sorted({u for raw in candidates if (u := canonical(raw.rstrip('.,;)'))) and FORM_HOST.search(u)})


def library_event(html, url, name, now):
    """Matosinhos publishes real hours separately from its midnight calendar metadata."""
    soup = BeautifulSoup(html, 'html.parser')
    detail = soup.select_one('.event_detail')
    title = soup.select_one('h1.pageTitle')
    date = soup.select_one('.atc_date_start')
    schedule = detail.select_one('.schedule .widget_value') if detail else None
    if not all((detail, title, date, schedule)): return None
    text = unicodedata.normalize('NFKC', detail.get_text(' ', strip=True))
    if 'Biblioteca Municipal Florbela Espanca' not in text: return None
    hour = re.search(r'\b(\d{1,2})(?:h|:)(\d{2})\b', schedule.get_text(' ', strip=True))
    if not hour: return None
    age_text = detail.select_one('.additional_info')
    item = {'name': title.get_text(' ', strip=True),
            'description': age_text.get_text(' ', strip=True) if age_text else '',
            'startDate': date.get_text(strip=True)[:10]+'T'+f'{int(hour[1]):02}:{hour[2]}',
            'location': {'name': 'Biblioteca Municipal Florbela Espanca', 'address': 'Matosinhos'},
            'url': url}
    event = make_event(item, url, name, now)
    if event:
        event['sourceType'] = 'matosinhos-official'
        if 'esgotad' in normalized(title.get_text(' ',strip=True)+' '+text):event['status']='soldout'
        event['confidence'] = 'official-listing'
        event['evidence'] = 'Data, horário, biblioteca e faixa etária publicados na página oficial; vagas por verificar.'
        forms = booking_links(str(detail), url)
        event['bookingUrl'] = forms[0] if len(forms) == 1 else None
        price = detail.select_one('.price')
        if price and 'gratuita' in price.get_text().lower(): event['price'] = 'Gratuito'
    return mark_session(event,url,now,'official-adapter') if event else None


def apply_registration(events, history, page, title, source, forms, dates, checked, evidence_url=None):
    """Associate evidence only with the exact event URL; never infer open places."""
    matching = [e for e in events if canonical(e.get('sourceUrl')) == canonical(page)]
    if len(matching) != 1: return
    for event in matching:
        if len(forms) == 1: event['bookingUrl'] = forms[0]
        if len(dates) != 1 or event.get('status')=='soldout': continue
        opening = parse_dt(dates[0])
        if not opening or opening.date() > datetime.fromisoformat(event['date']).date(): continue
        event['openingAt'] = opening.astimezone(PT).isoformat(timespec='minutes')
        event['status'] = 'scheduled'
        event['registrationEvidenceUrl'] = evidence_url or page
        event['registrationCheckedAt'] = checked
        oid = hashlib.sha256(f"{event['id']}|{dates[0]}".encode()).hexdigest()[:15]
        observations = history.setdefault('observations', [])
        if not any(o['id'] == oid for o in observations):
            observations.append({'id': oid, 'eventId': event['id'], 'organiser': source,
                                 'openingAt': dates[0], 'firstObserved': checked,
                                 'sourceUrl': evidence_url or page, 'certainty': 'official-page'})


def notify_telegram(lines):
    result=send_alerts(lines,session=SESSION)
    report_telegram(result)
    return result


def scan(sources,previous,history,now):
    old_index=previous.get('sourceIndex',{})
    old_disc={d['id']:d for d in previous.get('pendingDiscoveries',[])+previous.get('discoveries',[])}
    old_curated=load(DATA/'events.json',{});events=[e for e in old_curated.get('events',[])+old_curated.get('pendingEvents',[])+old_curated.get('excludedEvents',[]) if isinstance(e.get('minMonths'),(int,float)) and 0 <= e['minMonths'] < 36 and not excludes_under_three(e.get('ageText','')+' '+e.get('title',''))]
    registry=load(ROOT/'public/data/venues.json',{})
    results={};new_msgs=[];auto_add=[]
    poster_reviews=load(DATA/'poster-reviews.json',[])
    page_cache={}
    def get_page(url):
        if url not in page_cache: page_cache[url]=fetch(url)
        return page_cache[url]
    def adapted_sessions(page,url):
        context=None
        if urlparse(url).hostname=='www.bibliotecasdoporto.pt' and '/evento/' in urlparse(url).path:
            context,_=get_page('https://www.bibliotecasdoporto.pt/evento/nano-mini-micro-festival-para-a-infancia-do-porto/')
        return organiser_sessions(page,url,now,make_event,context)
    def session_key(event):
        return (canonical(event.get('sourceUrl')),event.get('date'),event.get('start'),normalized(event.get('title')),normalized(event.get('venue')))
    def refresh_page_evidence(url,parsed):
        current={session_key(e) for e in parsed}
        for event in events+auto_add:
            evidence=event.get('sessionEvidence',{})
            if canonical(evidence.get('sourceUrl'))==canonical(url) and session_key(event) not in current:
                event.pop('sessionEvidence',None)
    def upsert(event):
        if not event:return
        match=next((e for e in events+auto_add if canonical(e.get('sourceUrl'))==canonical(event['sourceUrl']) and e.get('date')==event['date'] and e.get('start')==event['start'] and normalized(e.get('title'))==normalized(event['title']) and normalized(e.get('venue'))==normalized(event['venue'])),None)
        if match:
            saved={k:match[k] for k in ('id','openingAt','registrationEvidenceUrl','registrationCheckedAt') if match.get(k) is not None}
            if match.get('status')=='scheduled' and match.get('openingAt') and event.get('status')!='soldout':saved['status']='scheduled'
            match.update(event);match.update(saved)
        else:auto_add.append(event)
        # A programme page can contain several different activities and times.
        # Keep a lead per parsed session rather than attach its first session to every link.
        lead_id='session-'+hashlib.sha256(f"{event['sourceUrl']}|{event['date']}|{event['start']}|{event['title']}".encode()).hexdigest()[:15]
        old=old_disc.get(lead_id,{})
        lead={key:event.get(key) for key in ('title','date','start','end','minMonths','maxMonths','venue','sessionEvidence')}
        lead.update(id=lead_id,url=event['sourceUrl'],source=event['sourceName'],firstSeen=old.get('firstSeen') or stamp(),lastSeen=stamp(),ageEvidence='official-adapter',priority=1)
        old_disc[lead_id]=lead
    for src in sources:
        name,url=src['name'],src['url'];print('Checking',name,url,flush=True)
        metadata={key:src[key] for key in ('instagramUrl','monitoringNote','agePolicyUrl') if key in src}
        if src.get('type')=='allegrow-public':
            report=collect_allegrow(fetch_json,now,make_event)
            pages=report.pop('pages')
            listed_ids=set(report.pop('listedIds',[]))
            if report['ok']:
                for page,parsed in pages.items():
                    refresh_page_evidence(page,parsed)
                    for event in parsed:upsert(event)
                if not report['truncated']:
                    for event in events+auto_add:
                        if event.get('sourceType')=='allegrow-public' and event.get('allegrowActivityId') not in listed_ids:
                            event.pop('sessionEvidence',None)
            found=list(pages)
            results[name]={**metadata,**report,'url':url,'checkedAt':stamp(),'lastLinks':found,'relevantLinks':len(found),'lastSuccessfulAt':stamp() if report['ok'] else old_index.get(name,{}).get('lastSuccessfulAt'),'contentStatus':'public-feed' if report['ok'] else 'unavailable'}
            continue
        html,err=get_page(url)
        if err:
            results[name]={**metadata,'url':url,'ok':False,'error':err,'checkedAt':stamp(),'lastLinks':old_index.get(name,{}).get('lastLinks',[]),'lastSuccessfulAt':old_index.get(name,{}).get('lastSuccessfulAt')}
            continue
        links,soup=links_from(html,url)
        clean_soup=BeautifulSoup(html,'html.parser')
        for hidden in clean_soup.select('[hidden], [aria-hidden="true"], script, style'): hidden.decompose()
        links,_=links_from(str(clean_soup),url)
        relevant=[(u,t) for (u,t) in links if possible_link(u,t) and u!=url]
        # Revisit known events even when they disappear from the homepage.
        known = [(e['sourceUrl'], e['title']) for e in events
                 if e.get('date', '') >= now.date().isoformat()
                 and urlparse(e.get('sourceUrl', '')).hostname == urlparse(url).hostname]
        relevant = list(dict(known + relevant).items())
        checked_before=old_index.get(name,{}).get('detailCheckedAt',{})
        known_urls={u for u,_ in known}
        # Oldest checked first; reserve room for new pages so a full known list
        # cannot starve discovery forever. Budgets bound every source's crawl.
        relevant.sort(key=lambda pair: (checked_before.get(pair[0],''), not bool(STRONG.search(pair[1])), pair[0]))
        known_links=[pair for pair in relevant if pair[0] in known_urls]
        new_links=[pair for pair in relevant if pair[0] not in known_urls]
        reserve=min(MAX_DETAILS,len(new_links))
        selected_known=known_links[:MAX_LINKS-reserve]
        selected_new=new_links[:MAX_LINKS-len(selected_known)]
        selected=selected_known+selected_new
        candidates_count=len(relevant)
        relevant=selected
        prev=set(old_index.get(name,{}).get('lastLinks',[]))
        first_scan=name not in old_index
        found=[]
        for u,t in relevant:
            eid=hashlib.sha256(u.encode()).hexdigest()[:15]
            old=old_disc.get(eid)
            item={**(old or {}),'id':eid,'title':t,'url':u,'source':name,'firstSeen':old.get('firstSeen') if old else stamp(),'lastSeen':stamp(),'status':'Por confirmar','priority':src.get('priority',3)}
            old_disc[eid]=item
            found.append(u)
        root_events=adapted_sessions(html,url)+[e for item in extract_json_ld(soup) if (e:=make_event(item,url,name,now))]
        refresh_page_evidence(url,root_events)
        for event in root_events:upsert(event)
        # Inspect a few event links for embedded form links and dates. No login/CAPTCHA.
        detail_errors=[]
        poster_reports=[]
        poster_pages=0
        detail_checked=dict(checked_before)
        parsed_keys={session_key(event) for event in root_events}
        for u,t in relevant:
            page,err2=get_page(u)
            detail_checked[u]=stamp()
            if not page:
                detail_errors.append({'url':u,'error':err2});continue
            a,s=links_from(page,u)
            # Restrict registration extraction to event content rather than navigation.
            content = s.select_one('.event_detail') or s.select_one('main') or s
            forms=booking_links(str(content),u)
            dates=opening_dates(str(content),now.year)
            form_errors=[]
            evidence_url=u
            if urlparse(u).hostname == 'www.bibliotecasearquivosmatosinhos.pt' and len(forms) == 1 and not dates:
                form_html,form_error=get_page(forms[0])
                if form_error: form_errors.append({'url':forms[0],'error':form_error})
                elif form_html:
                    form_soup=BeautifulSoup(form_html,'html.parser')
                    form_description=form_soup.select_one('.freebirdFormviewerViewHeaderDescription, .cBGGJ')
                    # Google Forms' public description only; never submitted responses.
                    if form_description:
                        dates=opening_dates(str(form_description),now.year)
                        if dates: evidence_url=forms[0]
            detail_errors.extend(form_errors)
            adapted = library_event(page,u,name,now) if urlparse(u).hostname == 'www.bibliotecasearquivosmatosinhos.pt' else None
            if not adapted and urlparse(u).hostname=='www.bibliotecasearquivosmatosinhos.pt' and '/evento-' in urlparse(u).path and poster_pages<3:
                poster_pages+=1
                adapted,reports=from_posters(page,u,name,now,make_event,lambda image:fetch(image,content_types=('image/jpeg','image/png','image/webp'),binary=True),poster_reviews)
                poster_reports.extend(reports)
            parsed=[adapted] if adapted else []
            parsed+=adapted_sessions(page,u)
            parsed+=[event for x in extract_json_ld(s) if (event:=make_event(x,u,name,now))]
            parsed_keys.update(session_key(event) for event in parsed)
            refresh_page_evidence(u,parsed)
            for event in parsed:upsert(event)
            age_event=next((e for e in parsed if canonical(e['sourceUrl'])==canonical(u)),None)
            discovery_id=hashlib.sha256(u.encode()).hexdigest()[:15]
            if age_event and discovery_id in old_disc:
                old_disc[discovery_id].update(minMonths=age_event['minMonths'],maxMonths=age_event['maxMonths'],ageEvidence='official-adapter' if adapted or age_event['sessionEvidence']['kind']=='official-programme' else 'structured-event')
            if not qualify_discovery(old_disc.get(discovery_id,{})): continue
            if not any(assess(dict(e),registry,now)['validationStatus']=='verified' for e in events+auto_add if canonical(e.get('sourceUrl'))==canonical(u)): continue
            apply_registration(events+auto_add,history,u,t,name,forms,dates,stamp(),evidence_url)
            sig_id=hashlib.sha256(u.encode()).hexdigest()[:15]
            signals=history.setdefault('signals',{})
            prevsignal=signals.get(sig_id,{})
            if forms or dates:
                old_forms=set(prevsignal.get('formUrls',[]))
                new_forms=set(forms)-old_forms
                signals[sig_id]={'page':u,'title':t,'source':name,'formUrls':forms,'openingDates':dates,'lastChecked':stamp()}
                if prevsignal and new_forms:
                    new_msgs.append(f"Novo link de formulário encontrado — {t} ({name})\n{next(iter(new_forms))}\nAbertura de vagas por confirmar")
                if prevsignal and set(dates)-set(prevsignal.get('openingDates',[])):
                    new_msgs.append(f"Data de inscrições anunciada — {t}\n{', '.join(dates)}\n{u}")
        results[name]={**metadata,'url':url,'ok':True,'checkedAt':stamp(),'lastLinks':found,'relevantLinks':len(found),'detailErrors':detail_errors,'posterCandidates':poster_reports,'detailCheckedAt':{u:detail_checked[u] for u,_ in known_links+new_links if u in detail_checked},'candidateLinks':candidates_count,'detailsChecked':len(relevant),'truncated':candidates_count>len(relevant),'parsedSessions':len(parsed_keys),'lastSuccessfulAt':stamp(),'contentStatus':'sessions-parsed' if parsed_keys else 'links-found' if found else 'no-relevant-links'}
        time.sleep(.35)
    # Retain evidence for diagnosis, but never publish unchecked seeds or city-level locations.
    groups=classify(events+auto_add,registry,now)
    old_curated.update(groups)
    for result in results.values():
        if result.get('readMode')=='public-json':
            result['eligibleSessions']=sum(e.get('sourceType')=='allegrow-public' for e in groups['events'])
            result['pendingSessions']=sum(e.get('sourceType')=='allegrow-public' for e in groups['pendingEvents']+groups['excludedEvents'])
    for group in groups.values():group.sort(key=lambda e:(e['date'],e.get('start') or '99:99'))
    new_items=[];pending_items=[]
    for discovery in old_disc.values():
        item=qualify_discovery(discovery)
        if not item:continue
        matching=[e for e in groups['events'] if canonical(e['sourceUrl'])==canonical(item['url']) and all(e.get(key)==item.get(key) for key in ('date','start','venue')) and normalized(e['title'])==normalized(item['title'])]
        if matching:
            # Carry a concrete session's checked fields; an organiser's general age policy is insufficient.
            session=matching[0]
            item.update({key:session[key] for key in ('date','start','end','minMonths','maxMonths','venue','sessionEvidence','validationStatus','distanceKm','distanceWithinRadius','geo')})
            new_items.append(item)
        else:
            item['validationStatus']='pending'
            item['validationReasons']=['Sessão e local por verificar na fonte original']
            # An explicit named venue can rule a lead out; it cannot confirm the session.
            names=[v['name'] for v in registry.get('venues',{}).values() if any(normalized(alias) in normalized(item['title']) for alias in v['aliases'])]
            if len(names)==1:
                from eligibility import set_distance
                located={'venue':names[0]};set_distance(located,registry)
                item.update({k:located[k] for k in ('distanceKm','distanceWithinRadius') if k in located})
                if item.get('distanceWithinRadius') is False:item['validationReasons']=['Fora do raio de 15 km']
            pending_items.append(item)
    new_items=sorted(new_items,key=lambda d:d['firstSeen'],reverse=True)[:LIMIT_DISCOVERIES]
    pending_items=sorted(pending_items,key=lambda d:d['firstSeen'],reverse=True)[:LIMIT_DISCOVERIES]
    previous_published={d['id'] for d in previous.get('discoveries',[])}
    if old_index:
        for item in new_items:
            if item['id'] not in previous_published:
                new_msgs.append(f"Novo anúncio potencial — {item['source']}\n{item['title']}\n{item['url']}")
    old_curated['eligibilitySummary']={'published':len(groups['events']),'pending':len(groups['pendingEvents']),'outsideRadius':len(groups['excludedEvents'])}
    old_curated['radiusKm']=registry.get('radiusKm',15)
    old_curated['distanceMethod']='straight-line'
    if any(x['ok'] for x in results.values()):old_curated['lastSuccessfulScan']=stamp()
    old_curated['updatedAt']=stamp()
    history['lastRun']=stamp()
    history['scanStats']={'sourcesOk':sum(x['ok'] for x in results.values()),'sourcesFailed':sum(not x['ok'] for x in results.values()),'autoEvents':len(auto_add)}
    new_updates={'updatedAt':stamp(),'sourceIndex':results,'discoveries':new_items,'pendingDiscoveries':pending_items}
    return new_updates,old_curated,history,new_msgs,auto_add

def main():
    now=now_pt()
    sources=load(DATA/'watchlist.json',[])
    previous=load(DATA/'discoveries.json',{'sourceIndex':{},'discoveries':[]})
    history=load(DATA/'history.json',{'observations':[],'signals':{}})
    updated,events,hist,msgs,added=scan(sources,previous,history,now)
    save(DATA/'discoveries.json',updated)
    save(DATA/'events.json',events)
    save(DATA/'history.json',hist)
    print('Sources OK:',hist['scanStats']['sourcesOk'],'failed:',hist['scanStats']['sourcesFailed'],'events auto-added:',len(added),'new actionable signals:',len(msgs))
    if os.environ.get('ALERT_ON_DISCOVERIES','')=='1':notify_telegram(msgs)
    elif any('formulário' in m or 'Data de inscrições' in m for m in msgs):
        notify_telegram([m for m in msgs if 'formulário' in m or 'Data de inscrições' in m])

if __name__=='__main__':main()
