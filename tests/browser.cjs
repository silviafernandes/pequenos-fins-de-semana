const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
(async () => {
  const {isNewEvent}=await import('../src/recency.js');
  const badgeNow=new Date('2026-11-09T12:00:00Z');
  for(const [addedAt,expected] of [['2026-11-09T12:00:00Z',true],['2026-11-02T12:00:01Z',true],['2026-11-02T12:00:00Z',false],['2026-10-30T12:00:00Z',false],['2026-11-10T12:00:00Z',false],['invalid',false],[undefined,false]])assert.equal(isNewEvent({addedAt},badgeNow),expected);
  assert.equal(isNewEvent({discoveredAt:badgeNow.toISOString(),checkedAt:badgeNow.toISOString()},badgeNow),false,'Rechecks do not imply recent admission');
  const {filterIdeas,ideasPage}=await import('../src/ideas.js');
  const catalogue=JSON.parse(require('node:fs').readFileSync('src/evergreenIdeas.json','utf8'));
  assert.equal(catalogue.length,14);assert.equal(new Set(catalogue.map(i=>i.id)).size,14);
  assert.equal(filterIdeas(catalogue,{search:'botanico'})[0].id,'jardim-botanico');
  assert.equal(ideasPage(catalogue,99).page,3);assert.equal(ideasPage(catalogue,0).page,1);
  assert.deepEqual(ideasPage([],2).items,[]);
  const {activityArtwork,artworkKinds}=await import('../src/activityArtwork.js');
  for(const [title,category,expected] of [
    ['Experimentar Pinturas','Sensorial','art'],['Experimentar Cerâmicas','Sensorial','art'],
    ['Babyoga de Outono','Outras','sports'],['Yoga de Encantar','Bibliotecas','sports'],['Som de Lá e de Cá','Bibliotecas','music'],
    ['Festival para bebés','Outras','festival'],['Hora do conto','Outras','stories'],
    ['Experimentar Luzes','Outras','sensory'],['Passeio na floresta','Outras','nature'],
    ['Bebeteca mágica','Bibliotecas','stories']]){
      assert.equal(activityArtwork({title,category}),expected);
  }
  const {eligibleSession,eligibleOuting}=await import('../src/eligibility.js');
  const playlabData=JSON.parse(require('node:fs').readFileSync('public/data/playlab-programme.json','utf8'));
  const reviewed={date:'2026-11-22',start:'10:00',end:'10:50',minMonths:0,maxMonths:72,venue:'PlayLab Porto',validationStatus:'verified',distanceWithinRadius:true,distanceKm:4.2};
  reviewed.sessionEvidence={...reviewed,kind:'reviewed-playlab-programme',sourceUrl:playlabData.sourceUrl,checkedAt:playlabData.reviewedAt,reviewedAt:playlabData.reviewedAt,validUntil:playlabData.validUntil,reviewDigest:'a'.repeat(64)};
  assert.equal(eligibleSession(reviewed,new Date('2026-11-21T12:00:00Z')),true,'Reviewed programmes remain visible beyond 48 hours');
  for(const evidence of [{...reviewed.sessionEvidence,validUntil:'2027-12-13'},{...reviewed.sessionEvidence,sourceUrl:'https://example.org'},{...reviewed.sessionEvidence,reviewDigest:'invalid'}]){
    assert.equal(eligibleSession({...reviewed,sessionEvidence:evidence},new Date('2026-11-21T12:00:00Z')),false);
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
      {id:'baby',addedAt:'2026-11-08T12:00:00Z',title:'Sessão para bebés pequenos',date:'2026-11-14',start:'10:00',end:'11:00',minMonths:0,maxMonths:6,category:'Música',indoor:null,status:'soldout'},
      {id:'library',addedAt:'2026-10-30T12:00:00Z',title:'Biblioteca com inscrições futuras',date:'2026-11-21',start:'10:00',end:null,minMonths:6,maxMonths:36,category:'Bibliotecas',status:'scheduled',openingAt:'2026-11-13T10:00+00:00',bookingUrl:'https://example.org/form'},
      {id:'past',title:'Abertura passada',date:'2026-11-15',start:'11:30',end:'12:30',minMonths:0,maxMonths:36,category:'Música',status:'scheduled',openingAt:'2026-11-08T10:00+00:00',indoor:true}
    ].map(e=>({...e,venue:'Porto',area:'Porto',sourceUrl:'https://example.org/event',description:'Atividade',price:'Gratuito',ageText:'0–36 meses'})),updatedAt:'2026-11-09T10:00:00Z',lastSuccessfulScan:'2026-11-09T10:00:00Z'};
    const outing={id:'outing-sealife',title:'Visitar o SEA LIFE Porto',venue:'SEA LIFE Porto',category:'Natureza',description:'Visita ao aquário para todas as idades.',weekendHours:'Sábados e domingos: 10:00–19:00.',periodLabel:'Horário habitual de fim de semana',note:'Escolhe a hora de visita.',price:'Preço por confirmar',admission:'all-ages',sourceUrl:'https://www.visitsealife.com/porto/',checkedAt:'2026-11-09T10:00:00Z',validationStatus:'verified',distanceWithinRadius:true,distanceKm:3.7,validFrom:'2026-11-09',validUntil:'2026-12-24'};
    fixture.outings=[outing,{...outing,id:'outing-market',title:'Mercadinho de Natal da Maia',venue:'Praça Dr. José Vieira de Carvalho',description:'Mercado para todas as idades.',category:'Festival',price:'Entrada gratuita',validFrom:'2026-11-27',validUntil:'2027-01-03'}, {...outing,id:'far-outing',title:'Passeio distante',distanceKm:25},{...outing,id:'unverified-outing',title:'Passeio sem idade confirmada',admission:'unknown'}];
    assert.equal(eligibleOuting(outing,new Date('2026-11-09T12:00:00Z')),true);
    assert.equal(eligibleOuting(outing,new Date('2026-11-12T12:00:00Z')),false);
    assert.equal(eligibleOuting({...outing,validUntil:'2026-11-13'},new Date('2026-11-09T12:00:00Z')),false,'A weekday-only remaining window has no weekend outing');
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
    await page.route('**/data/discoveries.json',route=>route.fulfill({json:{sourceIndex:{PlayLab:{url:'https://sites.google.com/view/playlabporto/agenda',ok:false,programmeReviewedAt:'2026-11-09T12:00:00Z',reviewedSessions:8,liveSessions:0,reviewNeeded:true},Biblioteca:{url:'https://example.org',ok:false,error:'HTTP 403',checkedAt:'2026-11-09T10:00:00Z'},Allegrow:{url:'https://allegrowkids.pt/pt/',ok:true,readMode:'public-json',activitiesChecked:12,eligibleSessions:0,pendingSessions:1}},discoveries:[
      {id:'old-lead',title:'Contamos contigo! A partir dos 3 anos',url:'https://example.org/older',minMonths:36,maxMonths:144,firstSeen:'2026-11-09'},
      {id:'unknown-lead',title:'Hora do conto para famílias',url:'https://example.org/unknown',firstSeen:'2026-11-09'},
      {...fixture.events.find(e=>e.id==='baby'),id:'baby-lead',title:'Música para bebés 0–3 anos',url:'https://example.org/babies',firstSeen:'2026-11-09'}]}}));
    await page.goto('http://127.0.0.1:4174/');
    await page.getByText('Sessão para bebés pequenos',{exact:true}).waitFor();
    assert.equal(await page.locator('.event-card').count(),3);
    assert.equal(await page.locator('.stats').count(),0);
    assert.equal(await page.locator('.filters button[aria-pressed="true"]').count(),0);
    assert.equal(await page.getByRole('combobox',{name:'Categoria'}).inputValue(),'Todas');
    await page.getByRole('button',{name:'Antes da sesta',exact:true}).click();
    assert.equal(await page.locator('.event-card').count(),2);
    await page.getByRole('button',{name:'Antes da sesta',exact:true}).click();
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
    assert.equal(await page.locator('#novidades, .new-discoveries').count(),0);
    assert.equal(await soldout.locator('.new-event-badge').count(),1);
    assert.equal(await page.locator('.event-card').filter({hasText:'Biblioteca com inscrições futuras'}).locator('.new-event-badge').count(),0);
    assert.equal(await page.getByText('Atividade em Paredes',{exact:true}).count(),0);
    assert.equal(await page.getByText('Local por verificar',{exact:true}).count(),0);
    assert.equal(await page.getByText('Sessão sem evidência',{exact:true}).count(),0);
    assert.match(await page.locator('.event-card').first().innerText(),/km em linha reta/);
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
    const disclosure=page.locator('#fontes');
    const summary=disclosure.locator('summary');
    assert.equal(await disclosure.getAttribute('open'),null,'Source section starts collapsed');
    assert.equal(await page.locator('.source-status-list').isVisible(),false);
    await summary.focus();await summary.press('Enter');
    assert.equal(await page.locator('.source-status-list').isVisible(),true,'Disclosure works with the keyboard');
    assert.match(await page.locator('.source-status-list').innerText(),/Fonte indisponível/);
    assert.match(await page.locator('.source-status-list').innerText(),/12 atividades consultadas · 0 sessões elegíveis · 1 sessão por verificar/);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.deepEqual(errors,[]);
    assert.ok(await page.getByText(/8 sessões futuras/).count());
    assert.ok(await page.getByText(/Formulário por rever; vagas e alterações por confirmar/).count());
    assert.equal(await page.locator('.outing-card').count(),1);
    assert.equal(await page.locator('.outing-card button').count(),0,'Opening hours are not exportable one-hour calendar sessions');
    assert.ok(await page.getByRole('heading',{name:'Ao vosso ritmo.'}).count());
    assert.equal(await page.locator('#ideias .evergreen-card').count(),6);
    assert.equal(await page.locator('#ideias img').count(),0,'Compact suggestions omit large illustrations');
    assert.equal(await page.locator('#ideias .evergreen-card').filter({hasText:'SEA LIFE Porto'}).count(),1);
    assert.equal(await page.locator('#passeios .outing-card').filter({hasText:'SEA LIFE Porto'}).count(),0,'SEA LIFE is not duplicated among seasonal outings');
    const ideas=JSON.parse(require('node:fs').readFileSync('src/evergreenIdeas.json','utf8'));
    assert.equal(ideas.filter(i=>i.place.includes('Matosinhos')).length,6);
    const {wazeUrl}=await import('../src/navigation.js');
    for(const idea of ideas){const url=new URL(wazeUrl(idea));assert.equal(url.hostname,'www.waze.com');assert.equal(url.searchParams.get('navigate'),'yes');assert.equal(url.searchParams.get('q'),idea.navigationQuery)}
    assert.equal(await page.locator('#ideias a[href^="https://www.waze.com/ul?"]').count(),6);
    const firstCard=page.locator('#ideias .evergreen-card').first();
    assert.ok((await firstCard.boundingBox()).height<230,'Suggestion cards stay compact on mobile');
    assert.equal(await page.locator('#ideias .evergreen-card .art-date, #ideias .evergreen-card button').count(),0,'Evergreen ideas have no calendar dates or booking controls');
    const directory=page.locator('#ideias');
    const pager=directory.getByRole('navigation',{name:'Páginas de sugestões'});
    assert.equal(await directory.getByRole('combobox',{name:'Concelho dos lugares'}).inputValue(),'all');
    assert.equal(await directory.getByRole('combobox',{name:'Tipo de lugar'}).inputValue(),'all');
    assert.equal(await pager.getByRole('button',{name:'Anterior',exact:true}).isDisabled(),true);
    const seen=new Set(await directory.locator('.evergreen-card h3').allTextContents());
    await pager.getByRole('button',{name:'Seguinte',exact:true}).click();
    assert.equal(await directory.locator('.evergreen-card').count(),6);
    for(const title of await directory.locator('.evergreen-card h3').allTextContents())seen.add(title);
    await pager.getByRole('button',{name:'Página 3 de sugestões',exact:true}).click();
    assert.equal(await directory.locator('.evergreen-card').count(),2);
    for(const title of await directory.locator('.evergreen-card h3').allTextContents())seen.add(title);
    assert.equal(seen.size,14,'Pagination exposes every place exactly once');
    assert.equal(await pager.getByRole('button',{name:'Seguinte',exact:true}).isDisabled(),true);
    await directory.getByRole('combobox',{name:'Concelho dos lugares'}).selectOption('Matosinhos');
    assert.equal(await directory.locator('.evergreen-card').count(),6,'Changing filters resets the final page');
    assert.equal(await directory.getByRole('navigation').count(),0);
    await directory.getByRole('combobox',{name:'Tipo de lugar'}).selectOption('aquarium');
    assert.equal(await directory.locator('.evergreen-card').count(),0);
    assert.equal(await directory.getByRole('button',{name:'Limpar filtros dos lugares'}).isVisible(),true);
    await directory.getByRole('combobox',{name:'Concelho dos lugares'}).selectOption('Porto');
    assert.equal(await directory.locator('.evergreen-card').count(),1);
    assert.match(await directory.locator('.evergreen-card').innerText(),/SEA LIFE/);
    await directory.getByRole('combobox',{name:'Tipo de lugar'}).selectOption('playground');
    assert.match(await directory.locator('.evergreen-card').innerText(),/Covelo/);
    await directory.getByRole('combobox',{name:'Concelho dos lugares'}).selectOption('Matosinhos');
    assert.match(await directory.locator('.evergreen-card').innerText(),/Carriçal/);
    await directory.getByRole('combobox',{name:'Tipo de lugar'}).selectOption('all');
    await directory.getByRole('searchbox').fill('sao mamede');
    assert.equal(await directory.locator('.evergreen-card').count(),1);
    assert.match(await directory.locator('.evergreen-card').innerText(),/São Mamede/);
    await directory.getByRole('searchbox').fill('nothing-here');
    await directory.getByRole('button',{name:'Limpar filtros dos lugares'}).click();
    assert.equal(await directory.locator('.evergreen-card').count(),6);
    assert.equal(await page.locator('.event-card').count(),1,'Directory filters do not change event filters');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await summary.press('Enter');
    assert.equal(await disclosure.getAttribute('open'),null);
    await page.locator('header nav').getByRole('link',{name:'Inscrições',exact:true}).click();
    assert.equal(await page.locator('.source-status-list').isVisible(),true,'Navigation reveals collapsed source details');
    await page.clock.setFixedTime(new Date('2027-05-01T12:00:00Z'));
    await page.reload();
    await page.locator('#ideias .evergreen-card').first().waitFor();
    assert.equal(await page.locator('#ideias .evergreen-card').count(),6,'Year-round ideas survive outside the calendar window');
    console.log('Browser checks passed: baby ages, unknown setting, opening filter, reset, favorites, indoor filter, sources, mobile.');
  } finally {
    if(browser) await browser.close();
    server.kill();
  }
})().catch(error=>{console.error(error);process.exit(1)});
