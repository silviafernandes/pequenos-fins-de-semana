import React, { useEffect, useMemo, useState } from 'react'
import {
  ArrowDownRight, ArrowRight, ArrowUpRight, BellRing, Bookmark, BookOpen,
  CalendarDays, Check, CheckCircle2, ChevronDown, Clock3, CloudSun,
  ExternalLink, Filter, Heart, Info, MapPin, Menu, RefreshCw, Search,
  Sparkles, Ticket, X, CircleAlert, CalendarPlus, ImageOff, Star, Sun, Compass
} from 'lucide-react'
import { eligibleSession } from './eligibility.js'
import initial from './initialData.json'
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
const timeLabel = e => e.start ? `${e.start}${e.end ? `–${e.end}` : ' · fim n/d'}` : 'Hora por confirmar'
const registrationLabel = e => {
  if (e.status==='scheduled' && e.openingAt && e.openingAt<=nowPTStamp()) return {label:'Abertura já passou · confirmar vagas',tone:'neutral'}
  if (e.status==='scheduled' && e.openingAt) return {label:'Abre em breve',tone:'amber'}
  if (e.status==='open') return {label:'Inscrições abertas (fonte verificada)',tone:'green'}
  if (e.status==='soldout') return {label:'Esgotado',tone:'red'}
  if (e.status==='walkin') return {label:'Sem reserva anunciada',tone:'green'}
  return {label:'Vagas por verificar',tone:'neutral'}
}
const napFriendly = e => !!e.start && e.start>='09:00' && e.start<='10:30' && !!e.end && e.end<='11:30'
const napClash = e => !!e.start && !!e.end && e.start<'13:30' && e.end>'11:30'
const bestCategoryIcon = cat => cat==='Bibliotecas' ? <BookOpen size={16}/> : cat==='Música' ? <Sparkles size={16}/> : cat==='Sensorial' ? <Sun size={16}/> : <Star size={16}/>
function timeToPT(stamp){ if(!stamp) return null; const [date,time]=stamp.split('T'); return `${date.split('-').reverse().join('/')} · ${time.slice(0,5)}` }
function openingHeadline(stamp){ if (!stamp) return ''; const [date,time]=stamp.split('T'); return `${weekday(date)} ${monthDay(date)} · ${time.slice(0,5)}` }
function isSafeUrl(s){try{return ['https:','http:'].includes(new URL(s).protocol)}catch{return false}}
function eventScore(e){ let s=napFriendly(e)?100:napClash(e)?-30:0; if(e.status==='open')s+=40; if(e.status==='scheduled')s+=35; if(e.category==='Bibliotecas')s+=8; if(e.minMonths<=27 && e.maxMonths>=27)s+=15; return s+(e.priority||0)/5 }
function calendarFile(e){
  if (!e.start || !e.end) return
  const d=e.date.replaceAll('-','');const t=(e.start||'10:00').replace(':','');const end=(e.end||'11:00').replace(':','')
  const text = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Pequenos Fins de Semana//PT','BEGIN:VEVENT',`UID:${e.id}@pequenos-fins-de-semana`,`DTSTAMP:${new Date().toISOString().replaceAll('-','').replaceAll(':','').replace(/\.\d{3}/,'')}`,`DTSTART;TZID=Europe/Lisbon:${d}T${t}00`,`DTEND;TZID=Europe/Lisbon:${d}T${end}00`,`SUMMARY:${e.title.replaceAll(',','\\,')}`,`LOCATION:${(e.venue||'').replaceAll(',','\\,')}`,`DESCRIPTION:${(e.bookingUrl||e.sourceUrl||'').replaceAll(',','\\,')}`,'END:VEVENT','END:VCALENDAR'].join('\r\n')
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/calendar;charset=utf-8'}));a.download=`atividade-${e.date}-${e.id}.ics`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),10000)
}
function Img({e}){
 const [failed,setFailed]=useState(false)
 const glyph=e.category==='Bibliotecas'?'✳':e.category==='Sensorial'?'◕':e.category==='Música'?'♫':'✿'
 return <div className={`art ${e.category==='Bibliotecas'?'art-lib':e.category==='Música'?'art-mus':e.category==='Sensorial'?'art-sen':'art-muse'}`}>
   {e.imageUrl&&!failed&&isSafeUrl(e.imageUrl)?<img src={e.imageUrl} loading="lazy" alt={`Fotografia da atividade ${e.title}`} onError={()=>setFailed(true)}/>:<div className="art-pattern"><span>{glyph}</span><i></i><b></b></div>}
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
     <div className="event-tags"><StatusBadge e={e}/>{napFriendly(e)?<MiniPill kind="mint">✓ Antes da sesta</MiniPill>:napClash(e)?<MiniPill kind="rose">Cruza a sesta</MiniPill>:null}</div>
     <div className="meta-grid"><span><CalendarDays size={14}/>{weekday(e.date)}, {monthDay(e.date)}</span><span><Clock3 size={14}/><strong>{timeLabel(e)}</strong></span><span><MapPin size={14}/>{e.venue}</span><span><Ticket size={14}/>{e.price}</span></div>
     <div className="detail-line">{Number.isFinite(e.distanceKm)&&<>{e.distanceKm.toLocaleString('pt-PT',{maximumFractionDigits:1})} km em linha reta <span>·</span> </>}{e.ageText} <span>·</span> {e.indoor===true?'Interior':e.indoor===false?'Exterior':'Interior/exterior por confirmar'}{e.evidenceDate?<span> <span>·</span> Fonte de {monthDay(e.evidenceDate)}</span>:null}</div>
     {e.status==='scheduled'&&e.openingAt&&<div className="opening-note"><BellRing size={14}/><span>Inscrições: <strong>{openingHeadline(e.openingAt)}</strong></span></div>}
     <div className="card-actions"><a className="primary-link" href={url||'#'} target="_blank" rel="noopener noreferrer" aria-disabled={!url}>{e.status==='scheduled'?'Ver formulário':e.status==='walkin'?'Ver detalhes':'Ver inscrição'} <ArrowUpRight size={15}/></a><a className="secondary-link" href={e.sourceUrl} target="_blank" rel="noopener noreferrer" title="Abrir fonte oficial">Fonte <ExternalLink size={13}/></a>{e.start&&e.end?<button className="secondary-link" onClick={()=>calendarFile(e)} title="Guardar no calendário"><CalendarPlus size={15}/></button>:null}</div>
   </div>
 </article>
}
function Banner({events}){
 const future=events.filter(e=>e.status==='scheduled'&&e.openingAt&&e.openingAt>nowPTStamp()).sort((a,b)=>a.openingAt.localeCompare(b.openingAt))[0]
 if(!future) return null
 return <div className="opening-banner"><div className="banner-icon"><BellRing size={22}/></div><div className="banner-copy"><span className="tiny-title">ATENÇÃO ÀS INSCRIÇÕES</span><h2>{future.title}</h2><p>Abrem <strong>{openingHeadline(future.openingAt)}</strong> · {future.venue}</p></div><a href={future.bookingUrl} target="_blank" rel="noopener noreferrer" className="banner-action">Formulário <ArrowUpRight size={17}/></a></div>
}
function SourcePanel({history,discoveries}){
 const obs=history.observations||[]
 const stats=history.scanStats
 return <section className="source-panel" id="fontes"><div className="section-heading small"><div><div className="eyebrow">POR DETRÁS DA AGENDA</div><h2>De olho nas inscrições<span>.</span></h2></div></div>
 <div className="source-cols"><div className="source-info"><div className="source-icon"><BookOpen size={21}/></div><h3>Bibliotecas primeiro.</h3><p>Monitorizamos as páginas oficiais e formulários, com prioridade para Matosinhos. As datas de abertura são importantes mesmo que a atividade ainda esteja longe.</p><div className="sources-mini">Matosinhos <span>·</span> Porto <span>·</span> Maia <span>·</span> Gaia</div></div>
 <div className="pattern-panel"><span className="tiny-title">HISTÓRICO DE ABERTURAS</span>
  {obs.length?obs.slice(-4).reverse().map(o=><div className="pattern-row" key={o.id}><div className="pattern-pin"/><div><strong>{o.organiser}</strong><span>{o.openingAt? openingHeadline(o.openingAt):'Data em análise'}</span><small>{o.certainty==='confirmed-by-user'?'Confirmado no formulário':'Evidência recolhida'} · {o.eventId}</small></div></div>):<p>Ainda não há datas suficientes para identificar um padrão.</p>}
  <div className="source-foot"><Info size={14}/> {stats?`Última recolha: ${stats.sourcesOk} fontes acessíveis, ${stats.sourcesFailed} indisponíveis. `:"A recolha automática ainda não começou. "}Uma única sexta-feira não confirma um padrão semanal. As datas são observações, não garantias de um horário habitual.</div>
 </div></div>
 <div className="source-status-list" aria-label="Estado das fontes">{Object.entries(discoveries.sourceIndex||{}).map(([name,source])=><article className="source-status" key={name}><a href={source.url} target="_blank" rel="noopener noreferrer">{name} <ExternalLink size={12}/></a><span>{source.ok?(source.relevantLinks?'Página acessível':'Sem anúncios extraídos'):'Fonte indisponível'}{source.detailErrors?.length?` · ${source.detailErrors.length} páginas por verificar`:''}</span><small>{source.lastSuccessfulAt?`Último acesso: ${new Date(source.lastSuccessfulAt).toLocaleString('pt-PT',{dateStyle:'short',timeStyle:'short',timeZone:'Europe/Lisbon'})}`:'Sem acesso bem-sucedido registado'}</small>{source.monitoringNote&&<small>{source.monitoringNote}</small>}{source.instagramUrl&&<a href={source.instagramUrl} target="_blank" rel="noopener noreferrer">Ver Instagram <ExternalLink size={12}/></a>}{source.error&&<small>{source.error}</small>}</article>)}</div>
 </section>
}
function Discoveries({data}) {
 const leads=(data.discoveries||[]).filter(d=>d.title&&d.url&&eligibleSession(d)).slice(0,8)
 if (!leads.length) return null
 return <section className="new-discoveries" id="novidades"><div className="section-heading small"><div><div className="eyebrow">PUBLICADOS RECENTEMENTE NAS FONTES</div><h2>Novos anúncios<span>.</span></h2><p>Sessões com data, hora, idade e local verificados na fonte original, até 15 km. Confirmar sempre as vagas.</p></div></div><div className="discoveries-list">{leads.map(item=><article className="discovery" key={item.id}><div className="tiny-title">{item.source} · POR VALIDAR</div><h3>{item.title}</h3><p>Consultar a fonte original para confirmar a inscrição e as vagas.</p><a href={item.url} target="_blank" rel="noopener noreferrer">Ver anúncio <ArrowUpRight size={14}/></a><div className="discovery-status">Detetado: {new Date(item.firstSeen).toLocaleDateString('pt-PT',{timeZone:'Europe/Lisbon'})}</div></article>)}</div></section>
}
function Footer({lastSuccessfulScan}){return <footer><div className="footer-left"><span className="logo-mark">✳</span><div><strong>Pequenos fins de semana</strong><small>Planos pequenos. Manhãs grandes.</small></div></div><div className="footer-right">Dados públicos e fontes oficiais, sempre que possível.<br/>Vagas e horários devem ser confirmados na origem.<br/>Localizações: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a> e <a href="https://www.waze.com/live-map/" target="_blank" rel="noopener noreferrer">Waze</a>. <span>© 2026</span></div></footer>}
function App(){
 const [data,setData]=useState(initial), [history,setHistory]=useState(initialHistory), [discoveries,setDiscoveries]=useState(initialDiscoveries), [fetchError,setFetchError]=useState(false)
 const [search,setSearch]=useState(''), [category,setCategory]=useState('Todas'), [week,setWeek]=useState('all')
 const [napOnly,setNapOnly]=useState(true),[savedOnly,setSavedOnly]=useState(false),[showAll,setShowAll]=useState(false),[indoorOnly,setIndoorOnly]=useState(false),[openingWeekOnly,setOpeningWeekOnly]=useState(false)
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
 const urgent=useMemo(()=>allEvents.filter(e=>e.status==='open'||(e.status==='scheduled'&&e.openingAt>nowPTStamp())).length,[allEvents])
 const nice=allEvents.filter(napFriendly).length
 const libraries=allEvents.filter(e=>e.category==='Bibliotecas').length
 const categories=['Todas',...new Set(allEvents.map(e=>e.category))]
 const toggleFav=id=>setFavorites(old=>{const value=old.includes(id)?old.filter(x=>x!==id):[...old,id];localStorage.setItem('pfds-favorites',JSON.stringify(value));return value})
 const titlePeriod=`${monthDay(weekends[0])} – ${monthDay(datePlusDays(weekends[5],1))}`
 return <div className="site-shell"><header><div className="wide nav"><a className="brand" href="#inicio" aria-label="Página inicial"><span className="logo-mark">✳</span><span>pequenos <strong>fins de semana</strong></span></a><nav><a href="#atividades">Atividades</a><a href="#fontes">Inscrições</a></nav><div className="nav-right"><span className="pulse"/><span>GUIA ATUALIZÁVEL</span></div></div></header>
 <main id="inicio"><section className="hero"><div className="wide hero-inner"><div className="hero-text"><div className="eyebrow"><span className="eyebrow-dot"/> MENORES DE 3 ANOS · MATOSINHOS & ARREDORES</div><h1>Planos pequenos.<br/><em>Manhãs grandes.</em></h1><div className="hero-meta"><span><MapPin size={15}/> Até 15 km dos CTT 4 Caminhos · em linha reta</span><span><Sun size={16}/> Preferência: 10:00</span></div></div><div className="hero-art" aria-hidden="true"><div className="art-orbit"><div className="circle-a"></div><div className="circle-b"></div><div className="circle-c"></div><div className="handdrawn">✳</div><div className="mini-dash dash1">✦</div><div className="mini-dash dash2">✳</div></div><span className="art-label">FEITO PARA<br/>PEQUENOS CURIOSOS</span></div></div></section>
 <div className="wide content"><div className="update-row"><span className="updated-indicator"><RefreshCw size={14}/> Dados: {data.updatedAt? new Date(data.updatedAt).toLocaleString('pt-PT',{dateStyle:'short',timeStyle:'short',timeZone:'Europe/Lisbon'}):'sem data'}</span><span className="range-indicator">Próximas 6 semanas <strong>{titlePeriod}</strong></span></div>
 {fetchError&&<div className="fallback-warning"><CircleAlert size={17}/> Sem ligação à atualização. Só mostramos sessões com verificação recente; tenta novamente mais tarde.</div>}
 {data.lastSuccessfulScan===null&&<div className="fallback-warning"><Info size={17}/> Versão inicial: a pesquisa automática começa quando o projeto estiver publicado e o GitHub Actions estiver ativado.</div>}
 <Banner events={allEvents}/>
 <section className="stats"><div><span>Atividades encontradas</span><strong>{allEvents.length.toString().padStart(2,'0')}</strong><small>Nos próximos 6 fins de semana</small></div><div><span>Antes da sesta</span><strong>{nice.toString().padStart(2,'0')}</strong><small>Terminando até às 11:30</small></div><div><span>Bibliotecas</span><strong>{libraries.toString().padStart(2,'0')}</strong><small>Sessões para os mais pequenos</small></div><div><span>Inscrições em destaque</span><strong>{urgent.toString().padStart(2,'0')}</strong><small>Aberturas futuras ou vagas verificadas</small></div></section>
 <section id="atividades" className="list-section"><div className="section-heading"><div><h2>O próximo plano<span>.</span></h2><p>Sessões verificadas para menores de 3 anos, até 15 km em linha reta. Escolhe um fim de semana ou filtra os horários antes da sesta.</p></div><span className="section-count">{displayed.length} {displayed.length===1?'sessão':'sessões'}</span></div>
 <div className="filters"><label className="search-field"><Search size={19}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Pesquisar atividade, local, oficina…" aria-label="Pesquisar atividades"/></label><label className="select-field"><Filter size={16}/><select value={category} onChange={e=>setCategory(e.target.value)} aria-label="Categoria">{categories.map(cat=><option key={cat}>{cat}</option>)}</select><ChevronDown size={16}/></label><button className={`toggle ${napOnly?'checked':''}`} onClick={()=>setNapOnly(!napOnly)} aria-pressed={napOnly}><Sun size={16}/> Antes da sesta {napOnly?<Check size={15}/>:null}</button><button className={`toggle ${savedOnly?'checked':''}`} onClick={()=>setSavedOnly(!savedOnly)} aria-pressed={savedOnly}><Heart size={16} fill={savedOnly?'currentColor':'none'}/> Guardados</button><button className={`toggle ${indoorOnly?'checked':''}`} onClick={()=>setIndoorOnly(!indoorOnly)} aria-pressed={indoorOnly}><CloudSun size={16}/> Em interior {indoorOnly?<Check size={15}/>:null}</button><button className={`toggle ${openingWeekOnly?'checked':''}`} aria-pressed={openingWeekOnly} onClick={()=>{setOpeningWeekOnly(!openingWeekOnly);setNapOnly(false);setWeek('all');setShowAll(false)}}><BellRing size={16}/> Inscrições a abrir esta semana</button></div>
 {data.eligibilitySummary?.pending>0&&<p className="filter-note">{data.eligibilitySummary.pending} sessões aguardam confirmação de detalhes e não aparecem na agenda.</p>}
 {napOnly&&allEvents.some(e=>e.start&&e.start<='10:30'&&!e.end)&&<p className="filter-note">Há atividades de manhã com hora de fim por confirmar. <button onClick={()=>setNapOnly(false)}>Mostrar também estas atividades</button></p>}
 <div className="weeks" role="group" aria-label="Filtrar fins de semana"><button className={week==='all'?'selected':''} onClick={()=>setWeek('all')}>Todos</button>{weekends.map(w=><button key={w} className={week===w?'selected':''} onClick={()=>setWeek(w)}>{cleanDate(w).getUTCDate()}–{cleanDate(datePlusDays(w,1)).getUTCDate()} {monthDay(w).split(' ')[1]}</button>)}</div>
 {displayed.length?<div className="event-grid">{displayed.slice(0,showAll?100:12).map(e=><EventCard e={e} key={e.id} favorites={favorites} onToggle={toggleFav}/>)}</div>:<div className="empty-state"><span>✳</span><h3>Nada nesta combinação — por enquanto.</h3><p>Experimenta retirar um filtro. Continuaremos atentos a novas inscrições e atividades.</p><button onClick={()=>{setSearch('');setCategory('Todas');setWeek('all');setNapOnly(false);setSavedOnly(false);setIndoorOnly(false);setOpeningWeekOnly(false)}}>Limpar filtros <ArrowRight size={16}/></button></div>}
 {displayed.length>12&&!showAll&&<button className="more" onClick={()=>setShowAll(true)}>Ver mais {displayed.length-12} atividades <ArrowDownRight size={16}/></button>}
 </section>
 <div className="midline"><div><CloudSun size={20}/><strong>Plano B para dias de chuva?</strong><span>As bibliotecas, oficinas e museus são boas apostas para manhãs em interior.</span></div><a href="#atividades" onClick={()=>{setSearch('');setCategory('Todas');setWeek('all');setSavedOnly(false);setShowAll(false);setOpeningWeekOnly(false);setIndoorOnly(true)}}>Explorar <ArrowRight size={16}/></a></div>
 <Discoveries data={discoveries}/>
 <SourcePanel history={history} discoveries={discoveries}/>
 <section className="method"><div><h3>Como interpretamos a disponibilidade?</h3><p>Uma página publicada não significa que ainda haja vagas. Só indicamos “inscrição confirmada” com evidência explícita. Formulários que ainda não abriram aparecem com a data comunicada pelo organizador. Anúncios novos sem idade/data/local suficientes aparecem em “Novos anúncios” por validar, nunca como sessões confirmadas.</p></div><div><h3>E as notificações?</h3><p>Esta primeira versão pode enviar avisos pelo Telegram quando detetar novos formulários ou datas de inscrições — após configurar as credenciais no GitHub. As verificações não são em tempo real e a confirmação da vaga é sempre feita pelo organizador.</p></div></section>
 </div></main><Footer lastSuccessfulScan={data.lastSuccessfulScan}/></div>
}
export default App
