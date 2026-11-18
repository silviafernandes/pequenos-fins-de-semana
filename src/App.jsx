import React, { useEffect, useMemo, useState } from 'react'
import {
  ArrowDownRight, ArrowRight, ArrowUpRight, BellRing, Bookmark, BookOpen,
  CalendarDays, Check, CheckCircle2, ChevronDown, Clock3, CloudSun,
  ExternalLink, Filter, Heart, Info, MapPin, Menu, RefreshCw, Search,
  Sparkles, Ticket, X, CircleAlert, CalendarPlus, ImageOff, Star, Sun, Compass
} from 'lucide-react'
import { eligibleSession, eligibleOuting } from './eligibility.js'
import { sessionTiming, napFriendly, napClash, timeLabel } from './timing.js'
import HeaderCollage from './HeaderCollage.jsx'
import { activityArtwork } from './activityArtwork.js'
import initial from './initialData.json'
import evergreenIdeas from './evergreenIdeas.json'
import { isNewEvent } from './recency.js'
import { wazeUrl } from './navigation.js'
import { filterIdeas, ideasPage, ideaTypes, amenityDefinitions, amenitySummary, amenityLabel } from './ideas.js'
import initialHistory from './initialHistory.json'
import initialDiscoveries from './initialDiscoveries.json'

const DATA_URL = `${import.meta.env.BASE_URL}data/events.json`
const HISTORY_URL = `${import.meta.env.BASE_URL}data/history.json`
const DISCOVERIES_URL = `${import.meta.env.BASE_URL}data/discoveries.json`
const nowPTStamp = () => new Intl.DateTimeFormat('sv-SE', {timeZone:'Europe/Lisbon', year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date()).replace(' ','T')
const fmt = new Intl.DateTimeFormat('pt-PT', {day:'numeric', month:'short', timeZone:'Europe/Lisbon'})
const weekdays = new Intl.DateTimeFormat('pt-PT', {weekday:'long', timeZone:'Europe/Lisbon'})
const nowPT = () => new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/Lisbon', year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date())
const cleanDate = d => new Date(`${d}T12:00:00Z`)
const weekday = d => weekdays.format(cleanDate(d))
const monthDay = d => `${cleanDate(d).getUTCDate()} ${['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'][cleanDate(d).getUTCMonth()]}`
const openingThisWeek = e => {const now=new Date(); const start=new Date(`${nowPT()}T12:00:00Z`); const days=7-((start.getUTCDay()+6)%7); const limit=datePlusDays(nowPT(),days); return e.status==='scheduled' && !!e.openingAt && new Date(e.openingAt.length===16?`${e.openingAt}${lisbonOffset(e.openingAt)}`:e.openingAt)>now && e.openingAt.slice(0,10)<limit}
const lisbonOffset = stamp => {const d=new Date(`${stamp.slice(0,10)}T12:00:00Z`); const h=new Intl.DateTimeFormat('en-GB',{hour:'2-digit',hourCycle:'h23',timeZone:'Europe/Lisbon'}).format(d); return h==='13'?'+01:00':'+00:00'}
const weekStart = d => { const x=cleanDate(d); x.setUTCDate(x.getUTCDate()-((x.getUTCDay()+1)%7)); return x.toISOString().slice(0,10) }
const datePlusDays = (d,n) => { const x=cleanDate(d); x.setUTCDate(x.getUTCDate()+n); return x.toISOString().slice(0,10) }
const pad = s => String(s).padStart(2,'0')
function nextSixWeekends(){
  const today=nowPT(), current=cleanDate(today), day=current.getUTCDay(), delta=(6-day+7)%7
  const saturday=datePlusDays(today,day===0?-1:delta)
  return Array.from({length:6},(_,i)=> datePlusDays(saturday,i*7))
}
const shortTime = time => time || 'Hora por confirmar'
const registrationLabel = e => {
  if (e.status==='scheduled' && e.openingAt && e.openingAt<=nowPTStamp()) return {label:'Abertura já passou · confirmar vagas',tone:'neutral'}
  if (e.status==='scheduled' && e.openingAt) return {label:'Abre em breve',tone:'amber'}
  if (e.status==='open') return {label:'Inscrições abertas (fonte verificada)',tone:'green'}
  if (e.status==='soldout') return {label:'Esgotado',tone:'red'}
  if (e.status==='walkin') return {label:'Sem reserva anunciada',tone:'green'}
  return {label:'Vagas por verificar',tone:'neutral'}
}
const bestCategoryIcon = cat => cat==='Bibliotecas' ? <BookOpen size={16}/> : cat==='Música' ? <Sparkles size={16}/> : cat==='Sensorial' ? <Sun size={16}/> : <Star size={16}/>
function timeToPT(stamp){ if(!stamp) return null; const [date,time]=stamp.split('T'); return `${date.split('-').reverse().join('/')} · ${time.slice(0,5)}` }
function openingHeadline(stamp){ if (!stamp) return ''; const [date,time]=stamp.split('T'); return `${weekday(date)} ${monthDay(date)} · ${time.slice(0,5)}` }
function isSafeUrl(s){try{return ['https:','http:'].includes(new URL(s).protocol)}catch{return false}}
function eventScore(e){ let s=napFriendly(e)?100:napClash(e)?-30:0; if(e.status==='open')s+=40; if(e.status==='scheduled')s+=35; if(e.category==='Bibliotecas')s+=8; if(e.minMonths<=27 && e.maxMonths>=27)s+=15; return s+(e.priority||0)/5 }
function calendarFile(e){
  const timing=sessionTiming(e)
  if (!timing) return
  const d=e.date.replaceAll('-','');const t=e.start.replace(':','');const end=timing.end.replace(':','');const endDate=timing.endDate.replaceAll('-','')
  const text = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Pequenos Fins de Semana//PT','BEGIN:VEVENT',`UID:${e.id}@pequenos-fins-de-semana`,`DTSTAMP:${new Date().toISOString().replaceAll('-','').replaceAll(':','').replace(/\.\d{3}/,'')}`,`DTSTART;TZID=Europe/Lisbon:${d}T${t}00`,`DTEND;TZID=Europe/Lisbon:${endDate}T${end}00`,`SUMMARY:${e.title.replaceAll(',','\\,')}`,`LOCATION:${(e.venue||'').replaceAll(',','\\,')}`,`DESCRIPTION:${timing.estimated?'Fim estimado: duração assumida de 1 hora. ':''}${(e.bookingUrl||e.sourceUrl||'').replaceAll(',','\\,')}`,'END:VEVENT','END:VCALENDAR'].join('\r\n')
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/calendar;charset=utf-8'}));a.download=`atividade-${e.date}-${e.id}.ics`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),10000)
}
function Img({e}){
 const [failed,setFailed]=useState(false)
 useEffect(()=>setFailed(false),[e.imageUrl])
 const artKind=activityArtwork(e)
 return <div className={`art art-${artKind}`}>
   {e.imageUrl&&!failed&&isSafeUrl(e.imageUrl)?<img src={e.imageUrl} loading="lazy" alt={`Imagem publicada de ${e.title}`} onError={()=>setFailed(true)}/>:<img className="category-art" src={`${import.meta.env.BASE_URL}illustrations/activity-${artKind}.webp`} alt=""/>}
   <span className="art-date"><strong>{cleanDate(e.date).getUTCDate()}</strong><span>{monthDay(e.date).split(' ')[1]}</span></span>
 </div>
}
function StatusBadge({e}) { const b=registrationLabel(e);return <span className={`badge badge-${b.tone}`}>{b.label}</span> }
function MiniPill({children,kind='plain'}){return <span className={`mini mini-${kind}`}>{children}</span>}
function EventCard({e,favorites,onToggle,compact=false}){
 const saved=favorites.includes(e.id)
 const url=isSafeUrl(e.bookingUrl)?e.bookingUrl:(isSafeUrl(e.sourceUrl)?e.sourceUrl:null)
 return <article className={`event-card ${compact?'compact':''}`}>
   <Img e={e}/>
   <div className="event-body">
     <div className="event-overline"><span>{e.category} <span className="dotsep">·</span> {e.area}</span><button className={`heart ${saved?'active':''}`} aria-label={saved?'Remover dos favoritos':'Guardar favorito'} title="Guardar nos favoritos" onClick={()=>onToggle(e.id)}><Heart size={18} fill={saved?'currentColor':'none'}/></button></div>
     <h3>{e.title}</h3>
     <p className="event-description">{e.description}</p>
     <div className="event-tags">{isNewEvent(e)&&<span className="new-event-badge" title="Adicionado à agenda nos últimos 7 dias"><Sparkles size={13} aria-hidden="true"/>Novo</span>}<StatusBadge e={e}/>{napFriendly(e)?<MiniPill kind="mint">✓ Antes da sesta</MiniPill>:napClash(e)?<MiniPill kind="rose">Cruza a sesta</MiniPill>:null}</div>
     <div className="meta-grid"><span><CalendarDays size={14}/>{weekday(e.date)}, {monthDay(e.date)}</span><span><Clock3 size={14}/><strong>{timeLabel(e)}</strong></span><span><MapPin size={14}/>{e.venue}</span><span><Ticket size={14}/>{e.price}</span></div>
     <div className="detail-line">{Number.isFinite(e.distanceKm)&&<>{e.distanceKm.toLocaleString('pt-PT',{maximumFractionDigits:1})} km em linha reta <span>·</span> </>}{e.ageText} <span>·</span> {e.indoor===true?'Interior':e.indoor===false?'Exterior':'Interior/exterior por confirmar'}{e.evidenceDate?<span> <span>·</span> Fonte de {monthDay(e.evidenceDate)}</span>:null}</div>
     {e.registrationNote&&<p className="registration-note">{e.registrationNote}</p>}
     {e.status==='scheduled'&&e.openingAt&&<div className="opening-note"><BellRing size={14}/><span>Inscrições: <strong>{openingHeadline(e.openingAt)}</strong></span></div>}
     <div className="card-actions"><a className="primary-link" href={url||'#'} target="_blank" rel="noopener noreferrer" aria-disabled={!url}>{e.status==='scheduled'?'Ver formulário':(e.registrationMethod==='in-person-ticket'||e.status==='walkin'||e.status==='soldout')?'Ver detalhes':'Ver inscrição'} <ArrowUpRight size={15}/></a><a className="secondary-link" href={e.sourceUrl} target="_blank" rel="noopener noreferrer" title="Abrir fonte oficial">Fonte <ExternalLink size={13}/></a>{sessionTiming(e)?<button className="secondary-link" onClick={()=>calendarFile(e)} title="Guardar no calendário"><CalendarPlus size={15}/></button>:null}</div>
   </div>
 </article>
}
function Outings({items=[]}){
 const outings=items.filter(o=>o.id!=='outing-sealife'&&eligibleOuting(o))
 if(!outings.length)return null
 return <section className="outings-section" id="passeios" aria-label="Passeios em família"><div className="section-heading"><div><h2>Ao vosso ritmo<span>.</span></h2><p>Passeios para todas as idades. Escolhe a hora de chegada dentro do horário de abertura.</p></div></div><div className="event-grid">{outings.map(o=><article className="outing-card" key={o.id}>
 <div className={`art art-${activityArtwork(o)}`}><img className="category-art" src={`${import.meta.env.BASE_URL}illustrations/activity-${activityArtwork(o)}.webp`} alt=""/></div>
 <div className="event-body"><div className="event-overline">{o.category} · Passeio</div><h3>{o.title}</h3><p className="event-description">{o.description}</p><div className="meta-grid"><span><CalendarDays size={14}/>{o.periodLabel}</span><span><Clock3 size={14}/>{o.weekendHours}</span><span><MapPin size={14}/>{o.venue}</span><span><Ticket size={14}/>{o.price}</span></div><div className="detail-line">{o.distanceKm.toLocaleString('pt-PT',{maximumFractionDigits:1})} km em linha reta · Todas as idades · {o.indoor?'Interior':'Exterior'}</div><p className="outing-note">{o.note}</p><div className="card-actions">{o.bookingUrl&&isSafeUrl(o.bookingUrl)&&<a className="primary-link" href={o.bookingUrl} target="_blank" rel="noopener noreferrer">Ver bilhetes <ArrowUpRight size={15}/></a>}{isSafeUrl(o.sourceUrl)&&<a className="secondary-link" href={o.sourceUrl} target="_blank" rel="noopener noreferrer">Horários e detalhes <ExternalLink size={13}/></a>}</div></div></article>)}</div></section>
}
function EverydayIdeas(){
 const [search,setSearch]=useState(''),[area,setArea]=useState('all'),[type,setType]=useState('all'),[page,setPage]=useState(1)
 const areas=[...new Set(evergreenIdeas.map(i=>i.area))]
 const matching=filterIdeas(evergreenIdeas,{search,area,type})
 const results=ideasPage(matching,page)
 const change=setter=>event=>{setter(event.target.value);setPage(1)}
 const clear=()=>{setSearch('');setArea('all');setType('all');setPage(1)}
 const goToPage=next=>{setPage(next);requestAnimationFrame(()=>{const region=document.getElementById('ideas-results');region?.focus({preventScroll:true});region?.scrollIntoView({block:'start'})})}
 return <section className="evergreen-section" id="ideias" aria-label="Ideias para todo o ano"><div className="section-heading"><div><div className="eyebrow">PARA REPETIR SEMPRE QUE APETECER</div><h2>Há sempre um plano<span>.</span></h2><p>Parques e lugares para visitar em família, sem marcar uma data. Escolhe um destino e abre o percurso no Waze.</p></div></div>
 <div className="ideas-filters"><label className="search-field"><Search size={18}/><input type="search" value={search} onChange={change(setSearch)} placeholder="Pesquisar lugar ou freguesia…" aria-label="Pesquisar lugares"/></label><label className="select-field"><MapPin size={17}/><select value={area} onChange={change(setArea)} aria-label="Concelho dos lugares"><option value="all">Todos os concelhos</option>{areas.map(a=><option key={a} value={a}>{a}</option>)}</select><ChevronDown size={16}/></label><label className="select-field"><Filter size={17}/><select value={type} onChange={change(setType)} aria-label="Tipo de lugar">{ideaTypes.map(t=><option key={t.value} value={t.value}>{t.label}</option>)}</select><ChevronDown size={16}/></label>{(search||area!=='all'||type!=='all')&&<button className="ideas-clear" onClick={clear}>Limpar <X size={14}/></button>}</div>
 <p className="ideas-count" role="status">{matching.length?`${matching.length} ${matching.length===1?'lugar':'lugares'} · ${results.start+1}–${results.start+results.items.length}`:'Nenhum lugar encontrado'}</p>
 <div id="ideas-results" role="region" aria-label="Sugestões de lugares" tabIndex={-1}>{matching.length?<div className="evergreen-grid">{results.items.map(idea=><article className="evergreen-card" key={idea.id}><div className="evergreen-heading"><span className="evergreen-icon" aria-hidden="true">{idea.kind==='aquarium'?<Ticket size={20}/>:<MapPin size={20}/>}</span><div><h3>{idea.title}</h3><p className="evergreen-place">{idea.place}</p></div></div><p className="evergreen-summary">{idea.shortDescription}</p><details className="place-amenities"><summary>{amenitySummary(idea)}</summary><dl>{amenityDefinitions.map(a=>{const fact=idea.amenities?.[a.key];return <div key={a.key}><dt>{a.label}</dt><dd>{amenityLabel(fact)}{fact?.ageBasis&&<small>{fact.ageBasis}</small>}{fact?.note&&<small>{fact.note}</small>}{fact?.sourceUrl&&<a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer" aria-label={`Fonte: ${a.label} de ${idea.title}`}>Fonte <ExternalLink size={11}/></a>}</dd></div>})}</dl></details><div className="evergreen-actions"><a className="primary-link" href={wazeUrl(idea)} target="_blank" rel="noopener noreferrer" aria-label={`Ir com Waze: ${idea.title}`}>Ir com Waze <ArrowUpRight size={14}/></a><a className="evergreen-info" href={idea.sourceUrl} target="_blank" rel="noopener noreferrer" aria-label={`Informações: ${idea.title}`}>Informações <ExternalLink size={12}/></a></div></article>)}</div>:<div className="ideas-empty"><p>Não há lugares nesta combinação. Experimenta outro concelho ou tipo.</p><button onClick={clear}>Limpar filtros dos lugares</button></div>}</div>
 {results.pages>1&&<nav className="ideas-pagination" aria-label="Páginas de sugestões"><button disabled={results.page===1} onClick={()=>goToPage(results.page-1)}>Anterior</button><div>{Array.from({length:results.pages},(_,i)=><button key={i} aria-label={`Página ${i+1} de sugestões`} aria-current={results.page===i+1?'page':undefined} onClick={()=>goToPage(i+1)}>{i+1}</button>)}</div><button disabled={results.page===results.pages} onClick={()=>goToPage(results.page+1)}>Seguinte</button></nav>}
 <p className="evergreen-footnote">Confirma horários e condições de acesso na página de informações. «Com parque infantil» confirma a existência do espaço, não a adequação a menores de 3 anos. As idades indicadas referem-se aos equipamentos. «Por confirmar» não significa que a instalação não exista.</p></section>
}
function Banner({events}){
 const future=events.filter(e=>e.status==='scheduled'&&e.openingAt&&e.openingAt>nowPTStamp()).sort((a,b)=>a.openingAt.localeCompare(b.openingAt))[0]
 if(!future) return null
 return <div className="opening-banner"><div className="banner-icon"><BellRing size={22}/></div><div className="banner-copy"><span className="tiny-title">ATENÇÃO ÀS INSCRIÇÕES</span><h2>{future.title}</h2><p>Abrem <strong>{openingHeadline(future.openingAt)}</strong> · {future.venue}</p></div><a href={future.bookingUrl} target="_blank" rel="noopener noreferrer" className="banner-action">Formulário <ArrowUpRight size={17}/></a></div>
}
function SourcePanel({history,discoveries}){
 const obs=history.observations||[]
 const stats=history.scanStats
 return <section className="source-panel"><details className="source-disclosure" id="fontes"><summary className="source-summary"><div className="section-heading small"><div><div className="eyebrow">POR DETRÁS DA AGENDA</div><h2>De olho nas inscrições<span>.</span></h2></div></div><ChevronDown className="source-chevron" aria-hidden="true"/></summary><div className="source-content">
 <div className="source-cols"><div className="source-info"><div className="source-icon"><BookOpen size={21}/></div><h3>Bibliotecas primeiro.</h3><p>Monitorizamos as páginas oficiais e formulários, com prioridade para Matosinhos. As datas de abertura são importantes mesmo que a atividade ainda esteja longe.</p><div className="sources-mini">Matosinhos <span>·</span> Porto <span>·</span> Maia <span>·</span> Gaia</div></div>
 <div className="pattern-panel"><span className="tiny-title">HISTÓRICO DE ABERTURAS</span>
  {obs.length?obs.slice(-4).reverse().map(o=><div className="pattern-row" key={o.id}><div className="pattern-pin"/><div><strong>{o.organiser}</strong><span>{o.openingAt? openingHeadline(o.openingAt):'Data em análise'}</span><small>{o.certainty==='confirmed-by-user'?'Confirmado no formulário':'Evidência recolhida'} · {o.eventId}</small></div></div>):<p>Ainda não há datas suficientes para identificar um padrão.</p>}
  <div className="source-foot"><Info size={14}/> {stats?`Última recolha: ${stats.sourcesOk} fontes acessíveis, ${stats.sourcesFailed} indisponíveis. `:"A recolha automática ainda não começou. "}Uma única sexta-feira não confirma um padrão semanal. As datas são observações, não garantias de um horário habitual.</div>
 </div></div>
 <div className="source-status-list" aria-label="Estado das fontes">{Object.entries(discoveries.sourceIndex||{}).map(([name,source])=><article className="source-status" key={name}><a href={source.url} target="_blank" rel="noopener noreferrer">{name} <ExternalLink size={12}/></a><span>{source.ok?(source.readMode==='family-outings'?'Página oficial consultada':source.readMode==='public-json'?`${source.activitiesChecked} atividades consultadas · ${source.eligibleSessions} ${source.eligibleSessions===1?'sessão elegível':'sessões elegíveis'}`:(source.parsedSessions>0?`${source.parsedSessions} ${source.parsedSessions===1?'sessão extraída':'sessões extraídas'}`:(source.relevantLinks?'Links encontrados · sem sessões extraídas':'Sem sessões extraídas'))):'Fonte indisponível'}{source.readMode==='public-json'&&source.pendingSessions>0?` · ${source.pendingSessions} ${source.pendingSessions===1?'sessão':'sessões'} por verificar`:''}{source.readMode==='family-outings'?` · ${source.outingsCount} passeios verificados`:''}{source.truncated?' · consulta parcial':''}{source.detailErrors?.length?` · ${source.detailErrors.length} páginas por verificar`:''}</span><small>{source.lastSuccessfulAt?`Último acesso: ${new Date(source.lastSuccessfulAt).toLocaleString('pt-PT',{dateStyle:'short',timeStyle:'short',timeZone:'Europe/Lisbon'})}`:'Sem acesso bem-sucedido registado'}</small>{source.posterCandidates?.some(p=>p.status==='needs-review')&&<small>{source.posterCandidates.filter(p=>p.status==='needs-review').length} cartaz(es) aguardam revisão dos detalhes.</small>}{source.programmeReviewedAt&&<small>Programa revisto em {new Date(source.programmeReviewedAt).toLocaleDateString('pt-PT')} · {source.reviewedSessions+source.liveSessions} sessões futuras. {source.reviewNeeded?'Formulário por rever; vagas e alterações por confirmar.':'Opções consultadas no formulário público.'}</small>}{source.monitoringNote&&<small>{source.monitoringNote}</small>}{source.instagramUrl&&<a href={source.instagramUrl} target="_blank" rel="noopener noreferrer">Ver Instagram <ExternalLink size={12}/></a>}{source.collectionHealth?.status==='review-needed'&&<small>Recolha requer revisão manual.</small>}{source.error&&<small>{source.error}</small>}</article>)}</div>
 </div></details></section>
}
function Footer({lastSuccessfulScan}){return <footer><div className="footer-left"><span className="logo-mark" aria-hidden="true">✳</span><div><strong>Pequenos fins de semana</strong><small>Planos pequenos. Manhãs grandes.</small></div></div><div className="footer-right">Dados públicos e fontes oficiais, sempre que possível.<br/>Vagas e horários devem ser confirmados na origem.<br/>Localizações: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a> e <a href="https://www.waze.com/live-map/" target="_blank" rel="noopener noreferrer">Waze</a>. <span>© 2026</span></div></footer>}
function App(){
 const [data,setData]=useState(initial), [history,setHistory]=useState(initialHistory), [discoveries,setDiscoveries]=useState(initialDiscoveries), [fetchError,setFetchError]=useState(false)
 const [search,setSearch]=useState(''), [category,setCategory]=useState('Todas'), [week,setWeek]=useState('all')
 const [napOnly,setNapOnly]=useState(false),[savedOnly,setSavedOnly]=useState(false),[showAll,setShowAll]=useState(false),[indoorOnly,setIndoorOnly]=useState(false),[openingWeekOnly,setOpeningWeekOnly]=useState(false)
 const [favorites,setFavorites]=useState(()=>{try{return JSON.parse(localStorage.getItem('pfds-favorites')||'[]')}catch{return []}})
 useEffect(()=>{let active=true;const load=()=>Promise.all([fetch(DATA_URL,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data');return r.json()}),fetch(HISTORY_URL,{cache:'no-store'}).then(r=>r.ok?r.json():initialHistory),fetch(DISCOVERIES_URL,{cache:'no-store'}).then(r=>r.ok?r.json():initialDiscoveries)]).then(([d,h,v])=>{if(active){setData(d);setHistory(h);setDiscoveries(v);setFetchError(false)}}).catch(()=>{if(active)setFetchError(true)});load();const timer=setInterval(load,10*60*1000);return()=>{active=false;clearInterval(timer)}},[])
 const weekends=useMemo(nextSixWeekends,[])
 const today=nowPT(), end=datePlusDays(weekends[5],1)
 const allEvents=useMemo(()=>data.events.filter(e=>e.date>=today&&e.date<=end&&eligibleSession(e)),[data.events,today,end])
 const displayed=useMemo(()=>allEvents.filter(e=>{
  const text=[e.title,e.venue,e.area,e.description,e.kind].join(' ').toLocaleLowerCase('pt-PT')
  if(search&&!text.includes(search.toLocaleLowerCase('pt-PT')))return false
  if(category!=='Todas'&&e.category!==category)return false
  if(week!=='all'&&weekStart(e.date)!==week)return false
  if(napOnly&&!napFriendly(e))return false
  if(savedOnly&&!favorites.includes(e.id))return false
  if(indoorOnly&&e.indoor!==true)return false
  if(openingWeekOnly&&!openingThisWeek(e))return false
  return true
 }).sort((a,b)=>eventScore(b)-eventScore(a)||a.date.localeCompare(b.date)),[allEvents,search,category,week,napOnly,savedOnly,favorites,indoorOnly,openingWeekOnly])
 const categories=['Todas',...new Set(allEvents.map(e=>e.category))]
 const toggleFav=id=>setFavorites(old=>{const value=old.includes(id)?old.filter(x=>x!==id):[...old,id];localStorage.setItem('pfds-favorites',JSON.stringify(value));return value})
 const titlePeriod=`${monthDay(weekends[0])} – ${monthDay(datePlusDays(weekends[5],1))}`
 return <div className="site-shell"><header><div className="wide nav"><a className="brand" href="#inicio" aria-label="Página inicial"><span className="logo-mark" aria-hidden="true">✳</span><span>pequenos <strong>fins de semana</strong></span></a><nav><a href="#atividades">Atividades</a><a href="#ideias">Ideias</a><a href="#fontes" onClick={()=>{const panel=document.getElementById('fontes');if(panel)panel.open=true}}>Inscrições</a></nav></div></header>
 <main id="inicio"><section className="hero"><div className="wide hero-inner"><div className="hero-text"><h1>Planos pequenos.<br/><em>Manhãs grandes.</em></h1><p className="hero-intro">Histórias, música e pequenas descobertas.<br/>O fim de semana começa com tempo para brincar.</p><a className="hero-cta" href="#atividades">Vamos escolher um plano <ArrowDownRight size={19}/></a></div><HeaderCollage/></div></section>
 <div className="wide content"><div className="update-row"><span className="updated-indicator"><RefreshCw size={14}/> Dados: {data.updatedAt? new Date(data.updatedAt).toLocaleString('pt-PT',{dateStyle:'short',timeStyle:'short',timeZone:'Europe/Lisbon'}):'sem data'}</span><span className="range-indicator">Próximas 6 semanas <strong>{titlePeriod}</strong></span></div>
 {fetchError&&<div className="fallback-warning"><CircleAlert size={17}/> Sem ligação à atualização. Só mostramos sessões com verificação recente; tenta novamente mais tarde.</div>}
 {data.lastSuccessfulScan===null&&<div className="fallback-warning"><Info size={17}/> Versão inicial: a pesquisa automática começa quando o projeto estiver publicado e o GitHub Actions estiver ativado.</div>}
 <Banner events={allEvents}/>
 <section id="atividades" className="list-section"><div className="section-heading"><div><h2>O próximo plano<span>.</span></h2></div></div>
 <div className="filters"><label className="search-field"><Search size={19}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Pesquisar atividade, local, oficina…" aria-label="Pesquisar atividades"/></label><label className="select-field"><Filter size={16}/><select value={category} onChange={e=>setCategory(e.target.value)} aria-label="Categoria">{categories.map(cat=><option key={cat}>{cat}</option>)}</select><ChevronDown size={16}/></label><button className={`toggle ${napOnly?'checked':''}`} onClick={()=>setNapOnly(!napOnly)} aria-pressed={napOnly}><Sun size={16}/> Antes da sesta {napOnly?<Check size={15}/>:null}</button><button className={`toggle ${savedOnly?'checked':''}`} onClick={()=>setSavedOnly(!savedOnly)} aria-pressed={savedOnly}><Heart size={16} fill={savedOnly?'currentColor':'none'}/> Guardados</button><button className={`toggle ${indoorOnly?'checked':''}`} onClick={()=>setIndoorOnly(!indoorOnly)} aria-pressed={indoorOnly}><CloudSun size={16}/> Em interior {indoorOnly?<Check size={15}/>:null}</button><button className={`toggle ${openingWeekOnly?'checked':''}`} aria-pressed={openingWeekOnly} onClick={()=>{setOpeningWeekOnly(!openingWeekOnly);setNapOnly(false);setWeek('all');setShowAll(false)}}><BellRing size={16}/> Inscrições a abrir esta semana</button></div>
 {data.eligibilitySummary?.pending>0&&<p className="filter-note">{data.eligibilitySummary.pending} sessões aguardam confirmação de detalhes e não aparecem na agenda.</p>}
 {allEvents.some(e=>!e.end)&&<p className="filter-note">Sem hora de fim publicada, estimamos uma duração de 1 hora. Esta estimativa é usada nos filtros e no calendário.</p>}
 <div className="weeks" role="group" aria-label="Filtrar fins de semana"><button className={week==='all'?'selected':''} onClick={()=>setWeek('all')}>Todos</button>{weekends.map(w=><button key={w} className={week===w?'selected':''} onClick={()=>setWeek(w)}>{cleanDate(w).getUTCDate()}–{cleanDate(datePlusDays(w,1)).getUTCDate()} {monthDay(w).split(' ')[1]}</button>)}</div>
 {displayed.length?<div className="event-grid">{displayed.slice(0,showAll?100:12).map(e=><EventCard e={e} key={e.id} favorites={favorites} onToggle={toggleFav}/>)}</div>:<div className="empty-state"><span>✳︎</span><h3>Nada nesta combinação — por enquanto.</h3><p>Experimenta retirar um filtro. Continuaremos atentos a novas inscrições e atividades.</p><button onClick={()=>{setSearch('');setCategory('Todas');setWeek('all');setNapOnly(false);setSavedOnly(false);setIndoorOnly(false);setOpeningWeekOnly(false)}}>Limpar filtros <ArrowRight size={16}/></button></div>}
 {displayed.length>12&&!showAll&&<button className="more" onClick={()=>setShowAll(true)}>Ver mais {displayed.length-12} atividades <ArrowDownRight size={16}/></button>}
 </section>
 <Outings items={data.outings}/>
 <EverydayIdeas/>
 <div className="midline"><div><CloudSun size={20}/><strong>Plano B para dias de chuva?</strong><span>As bibliotecas, oficinas e museus são boas apostas para manhãs em interior.</span></div><a href="#atividades" onClick={()=>{setSearch('');setCategory('Todas');setWeek('all');setSavedOnly(false);setShowAll(false);setOpeningWeekOnly(false);setIndoorOnly(true)}}>Explorar <ArrowRight size={16}/></a></div>
 <SourcePanel history={history} discoveries={discoveries}/>
 </div></main><Footer lastSuccessfulScan={data.lastSuccessfulScan}/></div>
}
export default App
