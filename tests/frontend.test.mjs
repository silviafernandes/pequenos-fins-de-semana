import test from 'node:test'
import assert from 'node:assert/strict'
import {nextSixWeekends,todayPT,lisbonInstant,openingInstant,openingThisWeek} from '../src/dates.js'
import {loadFavorites,persistFavorites} from '../src/favorites.js'
import {refreshFeeds} from '../src/feeds.js'
import {calendarText,googleCalendarUrl} from '../src/calendar.js'
import {sessionTiming} from '../src/timing.js'
import {underThree} from '../src/age.js'
import {eligibleSession} from '../src/eligibility.js'

test('weekend window moves on Monday and uses Lisbon rather than the host day',()=>{
  assert.equal(nextSixWeekends(new Date('2026-11-15T12:00Z'))[0],'2026-11-14')
  assert.equal(nextSixWeekends(new Date('2026-11-16T00:00Z'))[0],'2026-11-21')
  assert.equal(todayPT(new Date('2026-07-05T23:30Z')),'2026-07-06')
  assert.equal(nextSixWeekends(new Date('2026-07-05T23:30Z'))[0],'2026-07-11')
})

test('registration instants compare offsets, including Sunday UTC crossing into Monday in Lisbon',()=>{
  assert.equal(+openingInstant('2026-07-03T10:00'),+openingInstant('2026-07-03T09:00Z'))
  assert.equal(openingThisWeek({status:'scheduled',openingAt:'2026-07-05T23:30Z'},new Date('2026-07-03T12:00Z')),false)
  assert.equal(openingThisWeek({status:'scheduled',openingAt:'2026-07-05T22:30Z'},new Date('2026-07-03T12:00Z')),true)
  assert.equal(openingInstant('2026-02-31T10:00Z'),null)
  assert.equal(lisbonInstant('2026-03-29','01:30'),null)
})

test('malformed or inaccessible favourites never crash the page',()=>{
  for(const raw of ['null','{}','"text"','invalid'])assert.deepEqual(loadFavorites({getItem:()=>raw}),[])
  assert.deepEqual(loadFavorites({getItem:()=>'["a",null,"a",4,"b"]'}),['a','b'])
  assert.deepEqual(loadFavorites({getItem:()=>{throw Error('disabled')}}),[])
  assert.equal(persistFavorites(['a'],{setItem:()=>{throw Error('full')}}),false)
})

test('fresh activities apply immediately while an optional source report is failing or waiting',async()=>{
  let release
  const waiting=new Promise(resolve=>{release=resolve})
  const seen={}
  const work=refreshFeeds({data:'events',history:'history',discoveries:'sources'},Object.fromEntries(['data','history','discoveries'].map(k=>[k,v=>{seen[k]=v}])),{fetcher:async url=>{
    if(url==='sources')return waiting
    return {ok:url!=='history',json:async()=>({events:[]})}
  }})
  await new Promise(resolve=>setTimeout(resolve,0))
  assert.deepEqual(seen.data,{events:[]})
  assert.equal(seen.history,undefined)
  release({ok:false})
  assert.equal(await work,false)
})

test('bad response shapes preserve the last good data; aborted updates do not apply',async()=>{
  let value={events:[{id:'last-good'}]}
  for(const invalid of [null,{}, {events:{}},{events:[null]},{events:[],outings:'broken'}]){
    assert.equal(await refreshFeeds({data:'events'},{data:v=>{value=v}},{fetcher:async()=>({ok:true,json:async()=>invalid})}),false)
    assert.equal(value.events[0].id,'last-good')
  }
  const controller=new AbortController();controller.abort()
  await refreshFeeds({data:'events'},{data:v=>{value=v}},{signal:controller.signal,fetcher:async()=>({ok:true,json:async()=>({events:[]})})})
  assert.equal(value.events[0].id,'last-good')
})

const sample={id:'music',title:'Música; jogos, livros\\formas\nBEGIN:VEVENT',venue:'Salão; A, B\\C\nPorto',date:'2026-11-21',start:'10:00',end:null,sourceUrl:'https://example.org'}
test('calendar export escapes imported text, folds UTF-8 lines and cannot introduce extra events',()=>{
  const text=calendarText({...sample,title:sample.title+' çá'.repeat(70)},new Date('2026-11-19T12:00Z'))
  assert.equal(text.split('\r\n').filter(line=>line==='BEGIN:VEVENT').length,1)
  assert.ok(text.includes('SUMMARY:Música\\; jogos\\, livros\\\\formas\\nBEGIN:VEVENT'))
  assert.ok(text.includes('LOCATION:Salão\\; A\\, B\\\\C\\nPorto'))
  assert.ok(text.split('\r\n').every(line=>new TextEncoder().encode(line).length<=75))
  assert.ok(text.includes('DTSTART:20261121T100000Z\r\nDTEND:20261121T110000Z'))
  assert.ok(text.includes('duração assumida de 1 hora'))
  assert.equal(sample.end,null)
})

test('calendar export preserves local morning hours in summer and one elapsed hour across clock changes',()=>{
  assert.ok(calendarText({...sample,date:'2026-07-04'}).includes('DTSTART:20260704T090000Z'))
  for(const date of ['2026-03-29','2026-10-25']){
    const text=calendarText({...sample,date,start:date.includes('03-29')?'00:30':'01:30'})
    const start=text.match(/DTSTART:(\d{8}T\d{6}Z)/)[1], end=text.match(/DTEND:(\d{8}T\d{6}Z)/)[1]
    const parse=v=>Date.parse(v.replace(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/,'$1-$2-$3T$4:$5:$6Z'))
    assert.equal(parse(end)-parse(start),3600000)
  }
  assert.equal(sessionTiming({...sample,date:'2026-03-29',start:'00:30'}).end,'02:30')
  assert.equal(calendarText({...sample,date:'2026-02-31'}),null)
})

test('unknown upper ages and impossible dates do not become eligible sessions',()=>{
  assert.equal(underThree({minMonths:6,maxMonths:36}),true)
  for(const maxMonths of [undefined,null,NaN,Infinity,3])assert.equal(underThree({minMonths:6,maxMonths}),false)
  const e={...sample,date:'2026-02-29',minMonths:6,maxMonths:36,validationStatus:'verified',distanceWithinRadius:true,distanceKm:2}
  e.sessionEvidence={...e,checkedAt:'2026-02-27T10:00Z'}
  assert.equal(eligibleSession(e,new Date('2026-02-28T12:00Z')),false)
})


test('activity and place searches share Portuguese accent folding',async()=>{
  const {normalizeSearch}=await import('../src/search.js')
  assert.ok(normalizeSearch('Música para bebés em São Mamede').includes(normalizeSearch('musica')))
  assert.ok(normalizeSearch('São Mamede').includes(normalizeSearch('sao mamede')))
})


test('Google Calendar draft preserves event details, Unicode, Lisbon time and estimated duration',()=>{
  const e=Object.freeze({...sample,date:'2026-07-04',description:'Brincar & descobrir',ageText:'6–36 meses',price:'15 €',bookingUrl:'https://example.org/form?x=1&y=2'})
  const url=new URL(googleCalendarUrl(e))
  assert.equal(url.origin,'https://calendar.google.com')
  assert.equal(url.pathname,'/calendar/render')
  assert.equal(url.searchParams.get('action'),'TEMPLATE')
  assert.equal(url.searchParams.get('text'),e.title)
  assert.equal(url.searchParams.get('location'),e.venue)
  assert.equal(url.searchParams.get('ctz'),'Europe/Lisbon')
  assert.equal(url.searchParams.get('dates'),'20260704T090000Z/20260704T100000Z')
  const details=url.searchParams.get('details')
  for(const part of [e.description,e.ageText,e.price,e.bookingUrl,e.sourceUrl,'duração assumida de 1 hora'])assert.ok(details.includes(part))
  assert.equal(e.end,null)
})

test('Google Calendar uses the published end and rejects invalid event times',()=>{
  const url=new URL(googleCalendarUrl({...sample,end:'10:45'}))
  assert.equal(url.searchParams.get('dates'),'20261121T100000Z/20261121T104500Z')
  assert.ok(!url.searchParams.get('details').includes('Fim estimado'))
  assert.equal(googleCalendarUrl({...sample,date:'2026-02-31'}),null)
  assert.equal(googleCalendarUrl({...sample,start:null}),null)
  assert.equal(new URL(googleCalendarUrl({...sample,date:'2026-03-29',start:'00:30'})).searchParams.get('dates'),'20260329T003000Z/20260329T013000Z')
})
