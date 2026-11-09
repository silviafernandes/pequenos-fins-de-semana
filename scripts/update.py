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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

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

def fetch(url):
    try:
        res=SESSION.get(url,timeout=TIMEOUT,allow_redirects=True)
        res.raise_for_status()
        if len(res.content)>3_000_000: raise ValueError('Page too large')
        typ=res.headers.get('Content-Type','')
        if typ and not any(t in typ for t in ('text/html','application/xhtml','application/ld+json')):
            raise ValueError('Unexpected content type')
        return res.text, None
    except (requests.RequestException,ValueError) as e:
        return None, f'{type(e).__name__}: {str(e)[:130]}'

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
    if FORM_HOST.search(url): return False
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
                if '@graph' in x: stack.append(x['@graph'])
                typ=x.get('@type',[])
                if isinstance(typ,str): typ=[typ]
                if 'Event' in typ or any(str(y).endswith('Event') for y in typ):found.append(x)
    return found

def age_band(text):
    """Parse explicit age *ranges*; intentionally reject vague 'for families'."""
    t=strip_text(text).lower().replace('–','-').replace('—','-')
    def match(p, factors):
        m=re.search(p,t)
        if not m:return None
        lo,hi=int(m.group(1))*factors[0],int(m.group(2))*factors[1]
        return (lo,hi) if 0<=lo<=hi<=144 else None
    return (match(r'(\d{1,2})\s*(?:meses|m[eê]s|months)\s*(?:a|at[eé]|to|-)\s*(\d{1,2})\s*(?:meses|m[eê]s|months)',(1,1))
        or match(r'(\d{1,2})\s*(?:meses|m[eê]s)\s*(?:a|at[eé]|-)\s*(\d{1,2})\s*(?:anos|years)',(1,12))
        or match(r'(\d{1,2})\s*(?:anos|years)\s*(?:a|at[eé]|to|-)\s*(\d{1,2})\s*(?:anos|years)',(12,12))
        or match(r'\b(\d{1,2})\s*(?:a|at[eé]|-)\s*(\d{1,2})\s*(?:anos|years)\b',(12,12))
        or match(r'\b(\d{1,2})\s*(?:a|at[eé]|-)\s*(\d{1,2})\s*(?:meses|months)\b',(1,1)))

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
    st=parse_dt(item.get('startDate'))
    if not st:return None
    if st.tzinfo:st=st.astimezone(PT)
    if st.weekday()<5 or not (now.date()<=st.date()<= (now+timedelta(days=45)).date()):return None
    age=age_from_event(item)
    if not age or age[0]>30 or age[1]<24:return None
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
    slug=hashlib.sha256(f'{link}|{st.date()}|{st.hour}:{st.minute}'.encode()).hexdigest()[:13]
    return {'id':'auto-'+slug,'title':title[:140],'date':st.date().isoformat(),'start':st.strftime('%H:%M'),'end':end.strftime('%H:%M') if end else None,'minMonths':age[0],'maxMonths':age[1],'ageText':f'{age[0]}–{age[1]} meses','price':price,'venue':venue[:130],'area':re.search(LOCAL,where).group(0).title(),'category':category,'kind':'Evento publicado','description':strip_text(BeautifulSoup(item.get('description',''),'html.parser').get_text(' ',strip=True))[:260] or 'Atividade para crianças pequenas.','bookingUrl':booking,'sourceUrl':link,'sourceName':source_name,'imageUrl':canonical(pic),'status':'unverified','openingAt':None,'capacity':None,'indoor':True,'confidence':'structured-official' if 'Oficina' in source_name else 'structured-listing','evidence':'Dados estruturados do evento; vagas não confirmadas.','evidenceDate':now.date().isoformat(),'discoveredAt':stamp(),'sourceType':'auto-jsonld','priority':48}

def opening_dates(html,year):
    text=strip_text(BeautifulSoup(html,'html.parser').get_text(' ',strip=True))
    pat=re.compile(r'inscri[cç][oõ]es\s+(?:abrem|abertas?\s+(?:a\s+partir\s+de|em))\s*(?:no\s+dia\s+)?(\d{1,2})\s+de\s+([a-zçãé]+)(?:\s+de\s+(\d{4}))?\s*(?:[àa]s|as)?\s*(\d{1,2})?\s*(?:h|:)?\s*(\d{2})?',re.I)
    dates=[]
    for m in pat.finditer(text):
       month=MONTHS.get(m.group(2).lower())
       if not month:continue
       try:
           year_=int(m.group(3) or year);hour=int(m.group(4) or 0);minute=int(m.group(5) or 0)
           dt=datetime(year_,month,int(m.group(1)),hour,minute,tzinfo=PT)
           dates.append(dt.isoformat(timespec='minutes'))
       except ValueError:pass
    return dates[:8]

def notify_telegram(lines):
    token=os.environ.get('TELEGRAM_BOT_TOKEN','')
    chat=os.environ.get('TELEGRAM_CHAT_ID','')
    if not token or not chat or not lines:return
    message='✳ Novidades — Pequenos fins de semana\n\n'+'\n\n'.join(lines[:8])+'\n\nConfirmar sempre a inscrição na origem.'
    try:
       r=SESSION.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':message[:4000],'disable_web_page_preview':True},timeout=10)
       r.raise_for_status()
    except requests.RequestException as e:
       print('Telegram alert failed:',str(e)[:120],file=sys.stderr)

def scan(sources,previous,history,now):
    old_index=previous.get('sourceIndex',{})
    old_disc={d['id']:d for d in previous.get('discoveries',[])}
    old_curated=load(DATA/'events.json',{});events=old_curated.get('events',[])
    existing={(e.get('sourceUrl'),e.get('date')) for e in events}
    results={};new_msgs=[];auto_add=[]
    for src in sources:
        name,url=src['name'],src['url'];print('Checking',name,url,flush=True)
        html,err=fetch(url)
        if err:
            results[name]={'url':url,'ok':False,'error':err,'checkedAt':stamp(),'lastLinks':old_index.get(name,{}).get('lastLinks',[])}
            continue
        links,soup=links_from(html,url)
        relevant=[(u,t) for (u,t) in links if possible_link(u,t) and u!=url]
        relevant=relevant[:MAX_LINKS]
        prev=set(old_index.get(name,{}).get('lastLinks',[]))
        first_scan=name not in old_index
        found=[]
        for u,t in relevant:
            eid=hashlib.sha256(u.encode()).hexdigest()[:15]
            old=old_disc.get(eid)
            item={'id':eid,'title':t,'url':u,'source':name,'firstSeen':old.get('firstSeen') if old else stamp(),'lastSeen':stamp(),'status':'Por confirmar','priority':src.get('priority',3)}
            old_disc[eid]=item
            found.append(u)
            if not first_scan and u not in prev and src.get('priority',3)<3:
                new_msgs.append(f"Novo anúncio potencial — {name}\n{t}\n{u}")
        ld=extract_json_ld(soup)
        for item in ld:
            event=make_event(item,url,name,now)
            if event and (event['sourceUrl'],event['date']) not in existing:
                auto_add.append(event)
                existing.add((event['sourceUrl'],event['date']))
        # Inspect a few event links for embedded form links and dates. No login/CAPTCHA.
        for u,t in relevant[:MAX_DETAILS]:
            page,err2=fetch(u)
            if not page:continue
            a,s=links_from(page,u)
            forms=sorted({x for x,_ in a if FORM_HOST.search(x)})
            dates=opening_dates(page,now.year)
            for x in extract_json_ld(s):
                event=make_event(x,u,name,now)
                if event and (event['sourceUrl'],event['date']) not in existing:
                    auto_add.append(event);existing.add((event['sourceUrl'],event['date']))
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
        results[name]={'url':url,'ok':True,'checkedAt':stamp(),'lastLinks':found,'relevantLinks':len(found)}
        time.sleep(.35)
    # If crawl fails: don't remove existing data or overwrite observed leads.
    new_items=sorted(old_disc.values(),key=lambda d:d['firstSeen'],reverse=True)[:LIMIT_DISCOVERIES]
    old_curated['events']=sorted(events+auto_add,key=lambda e:(e['date'],e.get('start') or '99:99'))
    if any(x['ok'] for x in results.values()):old_curated['lastSuccessfulScan']=stamp()
    old_curated['updatedAt']=stamp()
    history['lastRun']=stamp()
    history['scanStats']={'sourcesOk':sum(x['ok'] for x in results.values()),'sourcesFailed':sum(not x['ok'] for x in results.values()),'autoEvents':len(auto_add)}
    new_updates={'updatedAt':stamp(),'sourceIndex':results,'discoveries':new_items}
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
