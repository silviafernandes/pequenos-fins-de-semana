const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
(async () => {
  const {activityArtwork,artworkKinds}=await import('../src/activityArtwork.js');
  for(const [title,category,expected] of [
    ['Experimentar Pinturas','Sensorial','art'],['Experimentar Cerâmicas','Sensorial','art'],
    ['Yoga de Encantar','Bibliotecas','sports'],['Som de Lá e de Cá','Bibliotecas','music'],
    ['Festival para bebés','Outras','festival'],['Hora do conto','Outras','stories'],
    ['Experimentar Luzes','Outras','sensory'],['Passeio na floresta','Outras','nature'],
    ['Bebeteca mágica','Bibliotecas','stories']]){
      assert.equal(activityArtwork({title,category}),expected);
  }
  const {collages,nextCollage}=await import('../src/collages.js');
  for(let current=-1;current<collages.length;current++){for(const random of [0,.3,.6,.999]){const next=nextCollage(current,()=>random);assert.ok(next>=0&&next<collages.length);assert.notEqual(next,current)}}
  const {sessionTiming,napFriendly,napClash,timeLabel}=await import('../src/timing.js');
  const sample={date:'2026-11-14',start:'10:00',end:null};
  assert.deepEqual(sessionTiming(sample),{startMinutes:600,endMinutes:660,end:'11:00',endDate:'2026-11-14',estimated:true});
  assert.equal(sample.end,null,'Estimation must not alter source evidence');
  assert.equal(napFriendly(sample),true);
  assert.equal(napFriendly({...sample,start:'10:30'}),true);
  assert.equal(napClash({...sample,start:'11:30'}),true);
  assert.equal(sessionTiming({...sample,end:'10:45'}).estimated,false);
  assert.equal(sessionTiming({...sample,end:'10:45'}).end,'10:45');
  assert.equal(sessionTiming({...sample,start:null}),null);
  assert.equal(sessionTiming({...sample,start:'23:30'}).endDate,'2026-11-15');
  assert.equal(sessionTiming({...sample,start:'23:30'}).end,'00:30');
  assert.match(timeLabel(sample),/10:00–11:00 · fim estimado/);
  const server = spawn('npm',['run','preview','--','--host','127.0.0.1','--port','4174'],{stdio:'ignore'});
  let browser;
  try {
    let ready=false;
    for(let attempt=0;attempt<60;attempt++){
      try{const response=await fetch('http://127.0.0.1:4174/');if(response.ok){ready=true;break}}catch{}
      await new Promise(resolve=>setTimeout(resolve,250));
    }
    assert.ok(ready,'Preview server did not start');
    browser = await chromium.launch({...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']});
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.clock.install({time:new Date('2026-11-09T12:00:00Z')});
    const fixture = {events:[
      {id:'older',title:'Atividade a partir dos 3 anos',date:'2026-11-14',start:'10:00',end:'11:00',minMonths:36,maxMonths:72,category:'Histórias'},
      {id:'baby',title:'Sessão para bebés pequenos',date:'2026-11-14',start:'10:00',end:'11:00',minMonths:0,maxMonths:6,category:'Música',indoor:null,status:'soldout'},
      {id:'library',title:'Biblioteca com inscrições futuras',date:'2026-11-21',start:'10:00',end:null,minMonths:6,maxMonths:36,category:'Bibliotecas',status:'scheduled',openingAt:'2026-11-13T10:00+00:00',bookingUrl:'https://example.org/form'},
      {id:'past',title:'Abertura passada',date:'2026-11-15',start:'10:00',end:'11:00',minMonths:0,maxMonths:36,category:'Música',status:'scheduled',openingAt:'2026-11-08T10:00+00:00',indoor:true}
    ].map(e=>({...e,venue:'Porto',area:'Porto',sourceUrl:'https://example.org/event',description:'Atividade',price:'Gratuito',ageText:'0–36 meses'})),updatedAt:'2026-11-09T10:00:00Z',lastSuccessfulScan:'2026-11-09T10:00:00Z'};
    for (const event of fixture.events) {
      event.distanceKm = 4.2
      event.distanceWithinRadius = true
      event.validationStatus = 'verified'
      event.sessionEvidence = Object.fromEntries(['date','start','end','minMonths','maxMonths','venue'].map(key=>[key,event[key]]))
      Object.assign(event.sessionEvidence,{sourceUrl:event.sourceUrl,checkedAt:'2026-11-09T10:00:00Z'})
    }
    fixture.events.push({...fixture.events.find(e=>e.id==='baby'),id:'far',title:'Atividade em Paredes',distanceKm:27,distanceWithinRadius:false})
    fixture.events.push({...fixture.events.find(e=>e.id==='baby'),id:'unknown-location',title:'Local por verificar',distanceKm:null,validationStatus:'pending'})
    fixture.events.push({...fixture.events.find(e=>e.id==='baby'),id:'unchecked',title:'Sessão sem evidência',sessionEvidence:undefined})
    await page.route('**/data/events.json',route=>route.fulfill({json:fixture}));
    await page.route('**/data/history.json',route=>route.fulfill({json:{observations:[]}}));
    await page.route('**/data/discoveries.json',route=>route.fulfill({json:{sourceIndex:{Biblioteca:{url:'https://example.org',ok:false,error:'HTTP 403',checkedAt:'2026-11-09T10:00:00Z'},Allegrow:{url:'https://allegrowkids.pt/pt/',ok:true,readMode:'public-json',activitiesChecked:12,eligibleSessions:0,pendingSessions:1}},discoveries:[
      {id:'old-lead',title:'Contamos contigo! A partir dos 3 anos',url:'https://example.org/older',minMonths:36,maxMonths:144,firstSeen:'2026-11-09'},
      {id:'unknown-lead',title:'Hora do conto para famílias',url:'https://example.org/unknown',firstSeen:'2026-11-09'},
      {...fixture.events.find(e=>e.id==='baby'),id:'baby-lead',title:'Música para bebés 0–3 anos',url:'https://example.org/babies',firstSeen:'2026-11-09'}]}}));
    await page.goto('http://127.0.0.1:4174/');
    await page.getByText('Sessão para bebés pequenos',{exact:true}).waitFor();
    assert.equal(await page.locator('.event-card').count(),3);
    assert.match(await page.locator('.event-card').filter({hasText:'Sessão para bebés pequenos'}).locator('.category-art').getAttribute('src'),/activity-music\.webp/);
    for(const kind of artworkKinds){assert.equal((await page.request.get('http://127.0.0.1:4174/pequenos-fins-de-semana/illustrations/activity-'+kind+'.webp')).status(),200)}
    const initialCollage=await page.locator('.hero-collage img').getAttribute('src');
    assert.equal(await page.getByRole('button',{name:'Mudar colagem do cabeçalho'}).count(),0);
    await page.reload();
    await page.getByText('Sessão para bebés pequenos',{exact:true}).waitFor();
    assert.notEqual(await page.locator('.hero-collage img').getAttribute('src'),initialCollage);
    for(const collage of collages){assert.equal((await page.request.get('http://127.0.0.1:4174/pequenos-fins-de-semana/illustrations/'+collage.file)).status(),200)}
    const soldout=page.locator('.event-card').filter({hasText:'Sessão para bebés pequenos'});
    assert.match(await soldout.innerText(),/Esgotado/);
    assert.equal(await soldout.getByRole('link',{name:'Ver detalhes'}).count(),1);
    assert.equal(await page.locator('.discovery').count(),1);
    assert.equal(await page.getByText('Atividade em Paredes',{exact:true}).count(),0);
    assert.equal(await page.getByText('Local por verificar',{exact:true}).count(),0);
    assert.equal(await page.getByText('Sessão sem evidência',{exact:true}).count(),0);
    assert.match(await page.locator('.event-card').first().innerText(),/km em linha reta/);
    assert.match(await page.locator('.discovery').innerText(),/Música para bebés/);
    assert.equal(await page.getByText(/Contamos contigo/).count(),0);
    assert.match(await page.locator('.weeks button').nth(1).innerText(),/nov/);
    assert.match(await page.locator('.event-card').filter({hasText:'Sessão para bebés pequenos'}).innerText(),/Interior\/exterior por confirmar/);
    const estimated=page.locator('.event-card').filter({hasText:'Biblioteca com inscrições futuras'});
    assert.match(await estimated.innerText(),/10:00–11:00 · fim estimado/);
    const downloadPromise=page.waitForEvent('download');
    await estimated.getByRole('button',{name:'Guardar no calendário'}).click();
    const download=await downloadPromise;
    const calendar=require('node:fs').readFileSync(await download.path(),'utf8');
    assert.match(calendar,/DTEND;TZID=Europe\/Lisbon:20261121T110000/);
    assert.match(calendar,/Fim estimado: duração assumida de 1 hora/);
    await page.getByRole('button',{name:'Inscrições a abrir esta semana'}).click();
    assert.equal(await page.locator('.event-card').count(),1);
    assert.match(await page.locator('.event-card').innerText(),/Biblioteca com inscrições futuras/);
    await page.getByRole('textbox').fill('nothing-matches');
    await page.getByRole('button',{name:/Limpar filtros/}).click();
    assert.equal(await page.locator('.event-card').count(),3);
    await page.getByRole('button',{name:'Guardar favorito',exact:true}).first().click();
    await page.reload();
    await page.getByRole('button',{name:'Remover dos favoritos'}).waitFor();
    await page.getByRole('button',{name:'Em interior',exact:true}).click();
    assert.equal(await page.locator('.event-card').count(),1);
    assert.match(await page.locator('.event-card').innerText(),/Abertura passada/);
    assert.match(await page.locator('.source-status-list').innerText(),/Fonte indisponível/);
    assert.match(await page.locator('.source-status-list').innerText(),/12 atividades consultadas · 0 sessões elegíveis · 1 sessão por verificar/);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.deepEqual(errors,[]);
    console.log('Browser checks passed: baby ages, unknown setting, opening filter, reset, favorites, indoor filter, sources, mobile.');
  } finally {
    if(browser) await browser.close();
    server.kill();
  }
})().catch(error=>{console.error(error);process.exit(1)});
