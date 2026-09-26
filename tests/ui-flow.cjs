const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {spawn}=require('node:child_process');
const path=require('node:path');
const python=process.env.PYTHON || 'python';
require('node:fs').mkdirSync('work',{recursive:true});
const env={...process.env,TEHNET_PANEL_PORT:'8767',TEHNET_PANEL_DB:path.resolve('work/ui-'+Date.now()+'.sqlite')};
let server,browser;
function start(){server=spawn(python,['outputs/panel/server.py'],{env,windowsHide:true});return new Promise((resolve,reject)=>{server.stdout.once('data',()=>resolve());server.once('error',reject);server.once('exit',code=>{if(code)reject(Error('Server exit '+code));});});}
function stop(){return new Promise(r=>{server.once('exit',r);server.kill();});}
(async()=>{
 await start();browser=await chromium.launch({headless:true,channel:'chrome'});const p=await browser.newPage({viewport:{width:1280,height:960}});const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('http://127.0.0.1:8767');await p.waitForSelector('[data-page="content"]');
 await p.locator('#new').click();await p.locator('[name="title"]').fill('آزمون سناریوی VoIP');await p.locator('[name="body"]').fill('متن واقعی تست <img src=x onerror=alert(1)>');await p.locator('[name="sources"]').fill('https://example.com/reference');await p.getByRole('button',{name:'ذخیره محتوا',exact:true}).click();await p.waitForSelector('#editor:not([open])',{state:'attached'});
 await p.locator('#brand').selectOption('mytel');await p.waitForFunction(()=>!document.querySelector('#view').innerText.includes('آزمون سناریوی VoIP'));
 await p.locator('#brand').selectOption('tehran-network');await p.getByRole('button',{name:'بررسی',exact:true}).click();await p.locator('#detail').waitFor({state:'visible'});
 if(await p.locator('#detail img').count())throw Error('XSS escaped text rendered as image');
 await p.locator('[data-decide="script"][data-status="approved"]').click();await p.waitForFunction(()=>document.querySelector('#detail-body').innerText.includes('تأیید شد'));
 await p.locator('[data-decide="publish"][data-status="approved"]').click();await p.waitForFunction(()=>document.querySelectorAll('#detail .badge.approved').length===2);
 await p.locator('[data-edit]').click();await p.locator('[name="body"]').fill('نسخه دوم سناریو');await p.getByRole('button',{name:'ذخیره محتوا',exact:true}).click();await p.waitForSelector('#editor:not([open])',{state:'attached'});await p.getByRole('button',{name:'بررسی',exact:true}).click();await p.locator('#detail').waitFor({state:'visible'});
 if(await p.locator('#detail .badge.pending').count()!==2)throw Error('Edited approval must reset');
 await p.locator('[data-close="detail"]').click();await p.getByRole('button',{name:'محتوا',exact:true}).click();await p.locator('#search').fill('نام ناموجود');await p.getByText('نتیجه‌ای پیدا نشد').waitFor();await p.locator('#search').fill('VoIP');await p.locator('#view').getByText('آزمون سناریوی VoIP',{exact:true}).waitFor();
 const dlPromise=p.waitForEvent('download');await p.locator('#export').click();const dl=await dlPromise;await dl.saveAs('work/ui-export.json');const exported=JSON.parse(require('node:fs').readFileSync('work/ui-export.json','utf8'));if(exported.items[0].history.length!==4)throw Error('Missing history backup');
 await stop();await start();await p.reload();await p.locator('#view').getByText('آزمون سناریوی VoIP',{exact:true}).waitFor();
 if(errors.length)throw Error(errors.join(';'));
 console.log('PASS: UI create/save, brand isolation, escaped HTML, script and publish approvals, edit invalidation, search, export with 4 history records, restart persistence.');
 await browser.close();await stop();
})().catch(async e=>{console.error(e);if(browser)await browser.close();if(server&&!server.killed)server.kill();process.exit(1);});
