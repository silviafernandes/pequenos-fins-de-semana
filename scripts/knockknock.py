"""Read the public subscription calendar linked by Knock-Knock's own page."""
import hashlib
import json
import re
from datetime import datetime,timedelta,time
from urllib.parse import urlparse,parse_qs,quote
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from icalendar import Calendar
import recurring_ical_events
from eligibility import mark_session,normalized

PAGE='https://www.knock-knock.pt/calendario'
PT=ZoneInfo('Europe/Lisbon')


def public_markup(html):
    soup=BeautifulSoup(html,'html.parser')
    # Podia renders these public rich-text blocks client-side. Decode the data,
    # never execute JavaScript or read account/cart/form state.
    for node in list(soup.select('[data-react-component="creator_ui/section_adapters/Text"]')):
        try:body=json.loads(node.get('data-props','{}')).get('text','')
        except (ValueError,TypeError):continue
        if isinstance(body,str):node.append(BeautifulSoup(body,'html.parser'))
    return soup


def calendar_id(html):
    for frame in public_markup(html).select('iframe[src]'):
        p=urlparse(frame['src'])
        if p.scheme=='https' and p.hostname=='calendar.google.com' and p.path=='/calendar/embed':
            ids=parse_qs(p.query).get('src',[])
            if len(ids)==1 and re.fullmatch(r'[a-zA-Z0-9_.-]+@group\.calendar\.google\.com',ids[0]):return ids[0]
    return None


def feed_url(id):
    return 'https://calendar.google.com/calendar/ical/'+quote(id,safe='')+'/public/basic.ics'


def collect(html,fetch_feed,now,make_event):
    report={'readMode':'public-calendar','ok':False,'parsedSessions':0,'calendarIssues':[],'detailErrors':[],'reviewNeeded':False}
    id=calendar_id(html)
    if not id:
        report.update(error='Calendário público não encontrado na página oficial',reviewNeeded=True)
        return [],report
    url=feed_url(id);report.update(calendarId=id,feedUrl=url)
    body,error=fetch_feed(url)
    if error:
        report.update(error=error,detailErrors=[{'url':url,'error':error}])
        return [],report
    try:
        cal=Calendar.from_ical(body)
        if cal.name!='VCALENDAR':raise ValueError('Not a calendar')
        raw_events=cal.walk('VEVENT')
        if len(raw_events)>2000:raise ValueError('Calendar too large')
        # Exclude sub-day recurrence rules before expansion to keep work bounded.
        for item in raw_events:
            if item.get('RRULE') and str(item['RRULE'].get('FREQ',[''])[0]).upper() not in ('DAILY','WEEKLY','MONTHLY','YEARLY'):
                raise ValueError('Unsupported recurrence frequency')
        window_start=datetime.combine(now.date(),time.min,tzinfo=PT)
        window_end=window_start+timedelta(days=46)
        occurrences=recurring_ical_events.of(cal,skip_bad_series=False).between(window_start,window_end)
        if len(occurrences)>1000:raise ValueError('Too many calendar occurrences')
    except Exception:  # Malformed external calendar data must not abort other sources.
        report['error']='Calendário inválido ou recorrência não suportada'
        return [],report
    report.update(ok=True,calendarEvents=len(raw_events),upcomingOccurrences=0,feedSha256=hashlib.sha256(body.encode()).hexdigest())
    result=[];seen=set()
    for item in occurrences:
        if str(item.get('STATUS','')).upper()=='CANCELLED':continue
        start=item.decoded('DTSTART',None)
        if not isinstance(start,datetime):continue  # All-day is not a session time.
        if start.tzinfo is None:
            # Floating times require an explicit published calendar timezone.
            if item.get('DTSTART').params.get('TZID') or str(cal.get('X-WR-TIMEZONE'))!='Europe/Lisbon':continue
            start=start.replace(tzinfo=PT)
        start=start.astimezone(PT)
        if not now.date()<=start.date()<=now.date()+timedelta(days=45) or start.weekday()<5:continue
        report['upcomingOccurrences']+=1
        title=str(item.get('SUMMARY','')).strip();uid=str(item.get('UID',''))
        description=BeautifulSoup(str(item.get('DESCRIPTION','')),'html.parser').get_text(' ',strip=True)
        location=str(item.get('LOCATION',''))
        local=normalized(location)
        location_ok=local in ('knock knock family club','knock knock') or ('knock knock' in local and 'duque de saldanha 186' in local)
        end=item.decoded('DTEND',None)
        if isinstance(end,datetime) and end.tzinfo is None and str(cal.get('X-WR-TIMEZONE'))=='Europe/Lisbon':end=end.replace(tzinfo=PT)
        end=end.astimezone(PT) if isinstance(end,datetime) and end.tzinfo else None
        raw={'name':title,'description':'Atividade publicada no calendário. '+description,'startDate':start.isoformat(),'url':PAGE,'location':{'name':'Knock-Knock Family Club','address':'Rua Duque de Saldanha 186, Porto'}}
        if end and end>start:raw['endDate']=end.isoformat()
        # Never borrow the club's general 0–5 policy for a specific workshop.
        event=make_event(raw,PAGE,'Knock-Knock Family Club',now) if location_ok and uid else None
        if not event:
            report['calendarIssues'].append({'uid':uid,'title':title,'date':start.date().isoformat(),'start':start.strftime('%H:%M'),'reason':'Local da sessão por confirmar' if not location_ok else 'Idade explícita inadequada ou detalhes insuficientes'})
            continue
        key=(uid,start.isoformat())
        if key in seen:continue
        seen.add(key)
        event.update(id='knock-'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:15],sourceType='knock-public-calendar',calendarUid=uid,calendarOccurrence=start.isoformat(),status='soldout' if 'esgotad' in normalized(title+' '+description) else 'unverified',confidence='official-calendar')
        links=BeautifulSoup(str(item.get('DESCRIPTION','')),'html.parser').select('a[href]')
        booking=next((a['href'] for a in links if urlparse(a['href']).scheme=='https' and (urlparse(a['href']).hostname in ('forms.gle','docs.google.com','www.knock-knock.pt'))),None)
        if booking:event['bookingUrl']=booking
        price=re.search(r'(\d+(?:[.,]\d+)?)\s*€\s*por fam[ií]lia',description,re.I)
        if price:event['price']=price[1].replace(',','.')+' EUR por família'
        mark_session(event,PAGE,now,'official-calendar')
        event['sessionEvidence'].update(calendarId=id,calendarUid=uid,calendarFeedUrl=url)
        result.append(event)
    report['parsedSessions']=len(result)
    report['calendarIssues']=report['calendarIssues'][:50]
    report['reviewNeeded']=bool(report['calendarIssues'])
    report['calendarStatus']='sessions-parsed' if result else 'details-missing' if report['upcomingOccurrences'] else 'no-upcoming-sessions'
    return result,report
