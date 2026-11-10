"""Read session fields from the organiser's own labelled programme sections."""
import re
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from eligibility import mark_session

MONTHS={m:i+1 for i,m in enumerate(('jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'))}


def organiser_sessions(html,url,now,make_event,context=None):
    soup=BeautifulSoup(html,'html.parser')
    domain=(urlparse(url).hostname or '').removeprefix('www.')
    result=[]
    if domain=='oficinajosefina.com' and urlparse(url).path.rstrip('/') in ('/beb%C3%A9s','/bebés'):
        text=unicodedata.normalize('NFKC',soup.get_text(' ',strip=True))
        year=re.search(r'Oficinas para Bebés\s+(20\d{2})',text)
        if not year or not re.search(r'(?:Av\.?|Avenida)\s*(?:de\s+)?Camilo,?\s*(?:n[ºo]\.?\s*)?224',text,re.I):return []
        pattern=r'(Experimentar (?:Cerâmicas|Pinturas|Luzes))\s+(\d{1,2})m\s+aos\s+(\d{1,2})a\b(.*?)(?=Experimentar (?:Cerâmicas|Pinturas|Luzes)|Oficinas para Famílias|$)'
        for block in re.finditer(pattern,text,re.S):
            title,lo,hi,body=block.groups()
            dates=re.finditer(r'\b(\d{1,2})\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s*\.\s*(\d{1,2})h(\d{2})?\s*[-–]\s*(\d{1,2})h(\d{2})?',body,re.I)
            for session in dates:
                d,month,h,m,eh,em=session.groups()
                try:
                    start=datetime(int(year[1]),MONTHS[month.lower()],int(d),int(h),int(m or 0))
                    end=start.replace(hour=int(eh),minute=int(em or 0))
                except ValueError:continue
                raw={'name':title,'description':f'Oficina sensorial para bebés de {lo} meses a {hi} anos','startDate':start.isoformat(),'endDate':end.isoformat(),'url':url,'location':{'name':'Oficina Josefina','address':'Avenida de Camilo 224, Porto'}}
                price=re.search(r'(\d+(?:[.,]\d+)?)\s*€',body)
                if price:raw['offers']={'price':price[1].replace(',','.'),'priceCurrency':'EUR'}
                event=make_event(raw,url,'Oficina Josefina',now)
                if event:result.append(mark_session(event,url,now,'official-programme'))
    elif domain=='casadamusica.com' and urlparse(url).path.startswith('/event/'):
        title=soup.find('h1')
        heading=soup.select_one('#h-publico-alvo')
        target=heading.find_next_sibling('p') if heading else None
        purchase=soup.find(attrs={'x-data':re.compile(r'^Purchase\(')})
        room=purchase.select_one('.grow.whitespace-nowrap.uppercase') if purchase else None
        room_name=room.get_text(' ',strip=True) if room else ''
        if not title or not target or room_name not in ('Sala Ensaio 2','Sala Suggia','Sala 2'):return []
        for button in soup.find_all('button',attrs={'x-on:click':re.compile(r'^select\(')}):
            time=button.find('time',attrs={'datetime':True})
            if not time:continue
            raw={'name':title.get_text(' ',strip=True),'description':target.get_text(' ',strip=True),'startDate':time['datetime'].replace(' ','T'),'url':url,'location':{'name':f'Casa da Música · {room_name}','address':'Avenida da Boavista 604-610, Porto'}}
            price=soup.select_one('#session-price-info')
            amount=re.search(r'€\s*(\d+(?:[.,]\d+)?)',price.get_text(' ',strip=True)) if price else None
            if amount:raw['offers']={'price':amount[1].replace(',','.'),'priceCurrency':'EUR'}
            event=make_event(raw,url,'Casa da Música',now)
            if event:result.append(mark_session(event,url,now,'official-programme'))
    elif domain=='bibliotecasdoporto.pt' and '/evento/' in urlparse(url).path and context:
        main=soup.select_one('[data-bl-name="Main"]')
        title=main.select_one('[data-bl-name="Display Title"]') if main else None
        caption=main.select_one('[data-bl-name="hora inicio"]') if main else None
        festival=BeautifulSoup(context,'html.parser')
        year=re.search(r'Em\s+(20\d{2})\s+celebram',festival.get_text(' ',strip=True))
        linked=any(urljoin(url,a['href']).rstrip('/')==url.rstrip('/') for a in festival.find_all('a',href=True))
        if not main or not title or not caption or not year or not linked:return []
        text=main.get_text(' ',strip=True)
        if 'AUDITÓRIO DA BIBLIOTECA MUNICIPAL ALMEIDA GARRETT' not in text.upper():return []
        day=re.search(r'\b(\d{1,2})\s+(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)\b',caption.get_text(' ',strip=True),re.I)
        duration=re.search(r'Duração:\s*(\d{1,3})\s*minutos',text,re.I)
        ages=re.search(r'Dos\s+(\d{1,2})\s+aos\s+(\d{1,2})\s+meses',text,re.I)
        if not day or not ages:return []
        for time in re.finditer(r'\b(\d{1,2})H(\d{2})\b',caption.get_text(' ',strip=True),re.I):
            try:start=datetime(int(year[1]),MONTHS[day[2].lower()],int(day[1]),int(time[1]),int(time[2]))
            except ValueError:continue
            raw={'name':re.sub(r'\s*[—–-]\s*ESPETÁCULO\s*$','',title.get_text(' ',strip=True),flags=re.I),'description':f'Atividade para bebés dos {ages[1]} aos {ages[2]} meses','startDate':start.isoformat(),'url':url,'location':{'name':'Biblioteca Municipal Almeida Garrett','address':'Jardins do Palácio de Cristal, Porto'}}
            if duration:raw['endDate']=(start+timedelta(minutes=int(duration[1]))).isoformat()
            event=make_event(raw,url,'Bibliotecas do Porto',now)
            if event:
                mark_session(event,url,now,'official-programme')
                event['sessionEvidence']['contextSourceUrl']='https://www.bibliotecasdoporto.pt/evento/nano-mini-micro-festival-para-a-infancia-do-porto/'
                result.append(event)
    return list({(e['date'],e['start'],e['venue'],e['title']):e for e in result}.values())
