"""Official Matosinhos posters: OCR proposals, visually reviewed facts for publication.

A review is bound to the exact image bytes and event page. OCR alone never grants
verified session evidence. Re-fetching unchanged artwork keeps its evidence fresh.
"""
import csv
import hashlib
import io
import re
import shutil
import subprocess
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from eligibility import mark_session, normalized

HOST='www.bibliotecasearquivosmatosinhos.pt'

def ocr_text(content):
    if not shutil.which('tesseract'):
        return {'text':'','confidence':None,'error':'OCR indisponível: tesseract em falta'}
    try:
        langs=subprocess.run(['tesseract','--list-langs'],capture_output=True,text=True,timeout=5).stdout.splitlines()
        language='por+eng' if 'por' in langs and 'eng' in langs else 'eng'
        run=subprocess.run(['tesseract','stdin','stdout','-l',language,'--psm','11','-c','tessedit_create_tsv=1'],input=content,capture_output=True,timeout=20)
        if run.returncode:return {'text':'','confidence':None,'error':'Não foi possível ler a imagem'}
        rows=list(csv.DictReader(io.StringIO(run.stdout.decode('utf-8')),delimiter='\t'))
        words=[r for r in rows if r.get('text','').strip() and float(r.get('conf',-1))>=0]
        text=' '.join(r['text'] for r in words)
        score=round(sum(float(r['conf']) for r in words)/len(words),1) if words else None
        return {'text':text[:3000],'confidence':score,'error':None}
    except (OSError,subprocess.TimeoutExpired,UnicodeError,ValueError,KeyError):
        return {'text':'','confidence':None,'error':'Falha na leitura do cartaz'}

def proposed_fields(text):
    """Literal OCR candidates only; never repair O/0 or treat these as verified."""
    proposed={}
    times=set(re.findall(r'\b([01]?\d|2[0-3])(?:h|:)([0-5]\d)\b',text,re.I))
    if len(times)==1:
        h,m=next(iter(times));proposed['start']=f'{int(h):02}:{m}'
    ages=set(re.findall(r'\b(\d{1,2})\s+(?:aos|a|[-–])\s+(\d{1,2})\s+meses\b',text,re.I))
    if len(ages)==1:
        lo,hi=map(int,next(iter(ages)))
        if 0<=lo<36 and hi>=lo:proposed.update(minMonths=lo,maxMonths=hi)
    venue='Biblioteca Municipal Florbela Espanca'
    if normalized(venue) in normalized(text):proposed['venue']=venue
    return proposed


def from_posters(html,page_url,source_name,now,make_event,fetch_image,reviews):
    if urlparse(page_url).hostname!=HOST:return None,[]
    soup=BeautifulSoup(html,'html.parser')
    detail=soup.select_one('.event_detail')
    title=soup.select_one('h1.pageTitle')
    calendar=soup.select_one('.atc_date_start')
    if not detail or not title or not calendar:return None,[]
    title_text=title.get_text(' ',strip=True)
    if re.search(r'\b(?:cancelad[oa]s?|adiad[oa]s?)\b',normalized(title_text+' '+detail.get_text(' ',strip=True))):return None,[]
    urls=[]
    for img in [*detail.select('.galleria img'),*detail.select('.image_preview img')]:
        url=urljoin(page_url,img.get('src',''))
        if urlparse(url).scheme=='https' and urlparse(url).hostname==HOST and url not in urls:urls.append(url)
    reports=[]
    for image_url in urls[:2]:
        content,error=fetch_image(image_url)
        if error or not content:
            reports.append({'pageUrl':page_url,'imageUrl':image_url,'status':'unavailable','error':error or 'Imagem vazia'})
            continue
        digest=hashlib.sha256(content).hexdigest()
        review=next((r for r in reviews if r.get('pageUrl')==page_url and r.get('imageUrl')==image_url and r.get('sha256')==digest),None)
        report={'pageUrl':page_url,'imageUrl':image_url,'sha256':digest,'checkedAt':now.isoformat()}
        if not review:
            report.update(ocr_text(content));report['proposedFields']=proposed_fields(report['text']);report['status']='needs-review'
            report['reason']='Texto de imagem requer revisão; não confirma uma sessão'
            reports.append(report);continue
        # A changed page/date/title cannot inherit a previous poster's review.
        if normalized(review.get('title','')) not in normalized(title_text) or not review.get('title') or calendar.get_text(strip=True)[:10]!=review.get('date'):
            report.update(status='needs-review',reason='O título ou data da página mudou')
            reports.append(report);continue
        raw={'name':review['title'],'description':review.get('ageText',''),'startDate':review['date']+'T'+review['start'],
             'url':page_url,'location':{'name':review['venue'],'address':'Matosinhos'},'image':image_url}
        if review.get('end'):raw['endDate']=review['date']+'T'+review['end']
        event=make_event(raw,page_url,source_name,now)
        if not event:
            report.update(status='needs-review',reason='Sessão fora dos critérios atuais');reports.append(report);continue
        event['status']='soldout' if 'esgotad' in normalized(title_text+' '+detail.get_text(' ',strip=True)) or review.get('status')=='soldout' else 'unverified'
        event['price']=review.get('price') or 'Por confirmar'
        event['sourceType']='matosinhos-poster'
        event['evidence']='Detalhes do cartaz oficial revistos visualmente; imagem novamente consultada e idêntica.'
        mark_session(event,page_url,now,'reviewed-official-poster')
        event['sessionEvidence'].update(imageUrl=image_url,imageSha256=digest,reviewedAt=review['reviewedAt'])
        report.update(status='reviewed',reviewedAt=review['reviewedAt'])
        reports.append(report)
        return event,reports
    return None,reports
