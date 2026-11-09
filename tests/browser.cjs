const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { chromium } = require('playwright');
(async () => {
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
      {id:'baby',title:'Sessão para bebés pequenos',date:'2026-11-14',start:'10:00',end:'11:00',minMonths:0,maxMonths:6,category:'Música',indoor:null},
      {id:'library',title:'Biblioteca com inscrições futuras',date:'2026-11-21',start:'10:00',end:null,minMonths:6,maxMonths:36,category:'Bibliotecas',status:'scheduled',openingAt:'2026-11-13T10:00+00:00',bookingUrl:'https://example.org/form'},
      {id:'past',title:'Abertura passada',date:'2026-11-15',start:'10:00',end:'11:00',minMonths:0,maxMonths:36,category:'Música',status:'scheduled',openingAt:'2026-11-08T10:00+00:00',indoor:true}
    ].map(e=>({...e,venue:'Porto',area:'Porto',sourceUrl:'https://example.org/event',description:'Atividade',price:'Gratuito',ageText:'0–36 meses'})),updatedAt:'2026-11-09T10:00:00Z',lastSuccessfulScan:'2026-11-09T10:00:00Z'};
    await page.route('**/data/events.json',route=>route.fulfill({json:fixture}));
    await page.route('**/data/history.json',route=>route.fulfill({json:{observations:[]}}));
    await page.route('**/data/discoveries.json',route=>route.fulfill({json:{sourceIndex:{Biblioteca:{url:'https://example.org',ok:false,error:'HTTP 403',checkedAt:'2026-11-09T10:00:00Z'}},discoveries:[]}}));
    await page.goto('http://127.0.0.1:4174/');
    await page.getByText('Sessão para bebés pequenos',{exact:true}).waitFor();
    assert.equal(await page.locator('.event-card').count(),2);
    assert.match(await page.locator('.weeks button').nth(1).innerText(),/nov/);
    assert.match(await page.locator('.event-card').filter({hasText:'Sessão para bebés pequenos'}).innerText(),/Interior\/exterior por confirmar/);
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
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.deepEqual(errors,[]);
    console.log('Browser checks passed: baby ages, unknown setting, opening filter, reset, favorites, indoor filter, sources, mobile.');
  } finally {
    if(browser) await browser.close();
    server.kill();
  }
})().catch(error=>{console.error(error);process.exit(1)});
