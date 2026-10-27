const {test} = require('node:test');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const path = require('node:path');
const fs = require('node:fs');
const root = path.resolve(__dirname, '../developer_home');
async function setup(options = {}) {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  const page = await browser.newPage({viewport:{width:1920,height:1080}});
  await page.route('http://launcher.test/**', route => {
    const name = new URL(route.request().url()).pathname.slice(1) || 'index.html';
    if (name === 'config.js') return route.fulfill({contentType:'text/javascript',body:'window.HOME_CONFIG='+JSON.stringify({apps:[{id:'test.video',name:'Vidéo'},{id:'test.live',name:'Direct'},{id:'test.missing',name:'Absente'}],discoverInputs:true})});
    return route.fulfill({path:path.join(root,name)});
  });
  await page.addInitScript(opts => {
    window.calls = [];
    window.close = () => { window.closedByBack = true; };
    window.PalmServiceBridge = function () {
      this.cancel = () => {};
      this.call = (uri, payload) => {
        const data = JSON.parse(payload); window.calls.push({uri,data});
        let response;
        if (uri.includes('getAllInputStatus')) response = opts.denyInputs ? {returnValue:false,errorText:'Denied'} : {returnValue:true,devices:[{id:'HDMI_1',appId:'test.hdmi',label:'HDMI 1'}]};
        else if (uri.includes('getAppLoadStatus')) response = {returnValue:true,exist:data.appId !== 'test.missing'};
        else response = opts.denyLaunch ? {returnValue:false,errorText:'Denied'} : {returnValue:true};
        setTimeout(() => this.onservicecallback(JSON.stringify(response)), 5);
      };
    };
  }, options);
  await page.goto('http://launcher.test/');
  await page.waitForFunction(() => window.homeDiagnostics && window.homeDiagnostics.pending.length === 0);
  return {browser,page};
}
test('remote navigation, disabled shortcuts, HDMI, OK once and Back', async () => {
  const {browser,page} = await setup();
  try {
    assert.equal(await page.locator('#apps button:disabled').count(),1);
    assert.equal(await page.evaluate(()=>document.activeElement.dataset.appId),'test.video');
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.evaluate(()=>document.activeElement.dataset.appId),'test.live');
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.evaluate(()=>document.activeElement.dataset.appId),'test.live');
    await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('acceptée'));
    assert.equal(await page.evaluate(()=>window.calls.filter(c=>c.uri.endsWith('/launch')).length),1);
    await page.keyboard.press('ArrowDown');
    assert.equal(await page.evaluate(()=>document.activeElement.dataset.appId),'test.hdmi');
    await page.keyboard.press('ArrowUp');
    assert.equal(await page.evaluate(()=>document.activeElement.dataset.appId),'test.video');
    const layout = await page.locator('footer').boundingBox(); assert.ok(layout.y+layout.height<=1080);
    if (process.env.TEST_SCREENSHOT) await page.screenshot({path:process.env.TEST_SCREENSHOT});
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(()=>window.closedByBack),true);
    assert.equal(await page.evaluate(()=>window.homeDiagnostics.events.filter(e=>e.event==='error').length),0);
  } finally {await browser.close();}
});
test('denied HDMI query leaves app row usable; launch error is visible',async()=>{
  const {browser,page}=await setup({denyInputs:true,denyLaunch:true});
  try {
    assert.equal(await page.locator('#inputs-section').isVisible(),false);
    await page.keyboard.press('ArrowDown');
    assert.equal(await page.evaluate(()=>document.activeElement.dataset.appId),'test.video');
    await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.querySelector('#status').className==='error');
    assert.match(await page.locator('#status').textContent(),/Denied/);
    assert.equal(await page.evaluate(()=>window.homeDiagnostics.pending.length),0);
  } finally {await browser.close();}
});
