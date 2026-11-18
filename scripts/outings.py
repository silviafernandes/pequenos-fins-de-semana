"""Official opening-hour outings, kept separate from timed activity sessions."""
import re
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
from eligibility import set_distance, official_source_matches

SEA_HOURS='https://www.visitsealife.com/porto/en/plan-your-visit/before-you-visit/opening-hours/'
SEA_AGES='https://www.visitsealife.com/porto/encontrar/informacoes/ajuda/'
SEA_BOOK='https://www.visitsealife.com/porto/visitar/bilhetes-e-passes/bilhetes/'
MAIA_MARKET='https://visitmaia.pt/public/eventos/mercadinho-de-natal-maia-natal-2026'
FAMA='https://www.andarte.pt/'
ZOO='https://www.zoodamaia.pt/sobre-o-zoo/horarios/index.html'
SERRALVES_MARKET='https://www.serralves.pt/atividades-serralves/0512-mercado-de-natal-de-serralves/'
FERREIRA_MARKET='https://www.agenda-porto.pt/evento/mercado-de-natal-1793352501535/'


def text(html):
    soup=BeautifulSoup(html or '','html.parser')
    main=soup.find('main') or soup
    for tag in main.select('script,style,header,footer,nav'):tag.decompose()
    return ' '.join(main.get_text(' ',strip=True).split())


def eligible(outing,registry,now):
    venue=set_distance(outing,registry)
    if not venue or not outing['distanceWithinRadius'] or outing.get('admission')!='all-ages':return False
    try:
        if not date.fromisoformat(outing['validFrom'])<=date.fromisoformat(outing['validUntil']):return False
        if date.fromisoformat(outing['validUntil'])<now.date() or date.fromisoformat(outing['validFrom'])>now.date()+timedelta(days=45):return False
        if not outing.get('weekendHours') or not outing.get('evidenceUrls'):return False
        if not all(official_source_matches(u,venue) for u in outing['evidenceUrls']):return False
        first=max(date.fromisoformat(outing['validFrom']),now.date())
        last=min(date.fromisoformat(outing['validUntil']),now.date()+timedelta(days=45))
        if not any((first+timedelta(days=d)).weekday()>=5 for d in range((last-first).days+1)):return False
        checked=datetime.fromisoformat(outing['checkedAt'])
        return checked.tzinfo is not None and timedelta(0)<=now-checked<=timedelta(hours=48)
    except (KeyError,TypeError,ValueError):return False


def collect(adapter, fetch, registry, now):
    urls={'sealife':[SEA_HOURS,SEA_AGES], 'maia-christmas':[MAIA_MARKET], 'matosinhos-christmas':[FAMA], 'zoo-maia':[ZOO,'https://www.zoodamaia.pt/sobre-o-zoo/precos/index.html'], 'serralves-christmas':[SERRALVES_MARKET], 'ferreira-christmas':[FERREIRA_MARKET]}[adapter]
    pages={};errors=[]
    for url in urls:
        html,error=fetch(url)
        if error:errors.append({'url':url,'error':error})
        else:pages[url]=text(html)
    report={'ok':bool(pages),'readMode':'family-outings','url':urls[0],'checkedAt':now.isoformat(),'detailErrors':errors,'outingsCount':0,'reviewNeeded':True}
    if errors:
        report['monitoringNote']='Não foi possível verificar todos os detalhes na fonte oficial. Passeio por confirmar.'
        return [],report
    item=None
    if adapter=='sealife':
        if (re.search(r'Saturdays, Sundays and Holidays, from 10 am to 7 pm',pages[SEA_HOURS],re.I)
                and re.search(r'adequado para visitantes de todas as idades',pages[SEA_AGES],re.I)):
            item={'id':'outing-sealife','title':'Visitar o SEA LIFE Porto','venue':'SEA LIFE Porto','category':'Natureza','description':'Aquário para todas as idades. Menores de 16 anos acompanhados por um adulto. Compra de bilhetes sujeita às condições do aquário.','weekendHours':'Sábados e domingos: 10:00–19:00 · última entrada às 18:15.','validFrom':now.date().isoformat(),'validUntil':(now.date()+timedelta(days=45)).isoformat(),'periodLabel':'Horário habitual de fim de semana','price':'Bilhetes pagos · preço por confirmar','bookingUrl':SEA_BOOK,'indoor':True,'note':'Escolhe a hora de visita; este horário não é a duração de uma sessão. Confirma exceções no dia da visita.'}
    elif adapter=='maia-christmas':
        body=pages[MAIA_MARKET]
        dates=re.search(r'Data\s+(\d{2}/\d{2}/20\d{2})\s+a\s+(\d{2}/\d{2}/20\d{2})',body)
        if (dates and 'Maia Natal 2026' in body and 'Praça Dr. José Vieira de Carvalho' in body
                and re.search(r'Para todas as idades',body,re.I) and re.search(r'sábados\s*-\s*10:00 às 24:00',body,re.I)
                and re.search(r'domingos e feriados\s*-\s*10:00 às 22:00',body,re.I) and 'Preço Gratuito' in body):
            begin,end=[datetime.strptime(d,'%d/%m/%Y').date() for d in dates.groups()]
            if begin.year==2026 and end.year==2027:
                item={'id':'outing-maia-natal-2026','title':'Mercadinho de Natal da Maia','venue':'Praça Dr. José Vieira de Carvalho','category':'Festival','description':'Mercado municipal para todas as idades, com artesanato e gastronomia. Acessível a carrinhos de bebé.','weekendHours':'Sábado: 10:00–24:00 · domingo: 10:00–22:00.','validFrom':begin.isoformat(),'validUntil':end.isoformat(),'periodLabel':'27 nov 2026 – 3 jan 2027','price':'Entrada gratuita · compras à parte','bookingUrl':None,'indoor':False,'note':'Artesanato até 24 de dezembro; gastronomia até 3 de janeiro. Dias 25 de dezembro e 1 de janeiro: encerrado. Pista de gelo e carrossel têm regras próprias e não estão incluídos nesta recomendação.'}
    elif adapter=='matosinhos-christmas':
        # The homepage includes many past editions. Never borrow a 2020 free-entry
        # statement or old hours for the 2026 market.
        current=re.search(r'Mercado de Natal de Matosinhos\s*-\s*FaMa 2026(.*?)(?=FaMa Sr\.|Mercado de Natal de Matosinhos.*2025|$)',pages[FAMA],re.S)
        if current and all(t in current[1] for t in ('27/Nov','23/Dez','Basílio Teles')):
            report['monitoringNote']='FaMa 2026: 27 nov–23 dez, Parque Basílio Teles. Sábado: 12:00–23:00; domingo: 12:00–20:00. Falta confirmação explícita das condições de acesso para bebés e do preço nesta edição. Não incluído nos passeios verificados.'
    elif adapter=='serralves-christmas':
        body=pages[SERRALVES_MARKET]
        # Check the current programme itself; no dates from the URL slug/footer.
        if (re.search(r'Mercado de Natal de Serralves\s+Parque\s+5 DEZ\s*[-–]\s*8 DEZ 2026\s*\|\s*10:00\s*[-–]\s*19:00',body,re.I)
                and 'Acesso gratuito' in body and re.search(r'gratuitos e para todas as idades',body,re.I)
                and not re.search(r'\b(?:cancelado|adiado)\b',body,re.I)):
            item={'id':'outing-serralves-natal-2026','title':'Mercado de Natal de Serralves','venue':'Parque de Serralves','category':'Festival','description':'Mercado no parque com design, artesanato, presentes e street food. Acesso gratuito e programação anunciada para todas as idades.','weekendHours':'5 e 6 de dezembro: 10:00–19:00.','validFrom':'2026-12-05','validUntil':'2026-12-08','periodLabel':'5–8 dez 2026 · 10:00–19:00','price':'Entrada gratuita · compras e comida à parte','bookingUrl':None,'indoor':False,'note':'Escolhe a hora da visita. O programa detalhado ainda será publicado; oficinas e espetáculos não são apresentados como sessões com horários confirmados.'}
    elif adapter=='ferreira-christmas':
        body=pages[FERREIRA_MARKET]
        if '2026-11-14T10:00:00Z' in body and '2027-01-06T20:00:00Z' in body and 'Mercado Ferreira Borges' in body:
            report['monitoringNote']='Mercado Ferreira Borges: 14 nov 2026–6 jan 2027; entrada gratuita na agenda municipal. Horário diário por confirmar. As horas de início/fim do período não provam abertura diária das 10:00 às 20:00. Mantido fora dos passeios verificados até haver horários de visita explícitos.'
    elif adapter=='zoo-maia':
        report['monitoringNote']='Visita ao zoo por confirmar: verificar horário de inverno e condições para menores de 3 anos. As atividades pedagógicas para grupos não são sessões públicas.'
    if item:
        item.update(validationStatus='verified',admission='all-ages',sourceUrl=urls[0],evidenceUrls=urls,checkedAt=now.isoformat(),sourceType='official-outing')
        if eligible(item,registry,now):
            report.update(outingsCount=1,reviewNeeded=False,lastSuccessfulAt=now.isoformat(),monitoringNote='Horários de visita consultados na fonte oficial; não são sessões com duração marcada.')
            return [item],report
    report.setdefault('monitoringNote','Datas, horários, idade ou local ainda por confirmar na fonte oficial.')
    return [],report
