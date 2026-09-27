const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {spawn}=require('node:child_process');
const path=require('node:path');
const python=process.env.PYTHON || 'python';
require('node:fs').mkdirSync('work',{recursive:true});
const env={...process.env,TEHNET_PANEL_PORT:'8767',TEHNET_PANEL_DB:path.resolve('work/ui-'+Date.now()+'.sqlite')};
let server,browser;
function start(){server=spawn(python,['outputs/panel/server.py'],{env,windowsHide:true});return new Promise((resolve,reject)=>{server.stdout.once('data',()=>resolve());server.once('error',reject);server.once('exit',code=>{if(code)reject(Error('Server exit '+code));});});}
function stop(){return new Promise(r=>{server.once('exit',r);server.kill();});}
async function waitJob(base,kind,statuses,timeout=120000){
 const end=Date.now()+timeout;
 while(Date.now()<end){
  const res=await fetch(base+'/api/jobs');
  const jobs=await res.json();
  const j=jobs.filter(x=>x.kind===kind).sort((a,b)=>a.created_at<b.created_at?1:-1)[0];
  if(j&&statuses.includes(j.status))return j;
  await new Promise(r=>setTimeout(r,800));
 }
 throw Error('job '+kind+' did not reach '+statuses);
}
(async()=>{
 await start();browser=await chromium.launch({headless:true,channel:'chrome'});
 const p=await browser.newPage({viewport:{width:1360,height:900}});
 const errors=[];
 p.on('pageerror',e=>errors.push('pageerror: '+e.message));
 p.on('response',res=>{if(res.status()>=400)errors.push('http '+res.status()+': '+res.url());});
 p.on('console',m=>{if(m.type()==='error')errors.push('console: '+m.text().slice(0,150));});
 const base='http://127.0.0.1:8767';

 // 1) dashboard renders for Tehran Network
 await p.goto(base);await p.waitForSelector('.stats');await p.waitForFunction(()=>document.querySelector('#nav').innerText.includes('کارها'));
 await p.screenshot({path:'docs/images/dashboard.png',fullPage:true});

 // 2) wizard: new content from voice upload
 await p.click('#new');await p.waitForSelector('[data-wiznext]');
 await p.click('[data-wiznext]');                       // step1 brand: tehran-network (default)
 await p.waitForSelector('[data-wtype="upload"]');
 await p.click('[data-wtype="upload"]');await p.click('[data-wiznext]');
 await p.waitForSelector('#wiz-title');
 await p.fill('#wiz-title','آزمون جامع کارخانه محتوا');
 await p.setInputFiles('#wiz-file','tests/fixtures/voice-sample.wav');
 await p.click('#wiz-voice-create');                    // creates project + transcription job
 await p.waitForSelector('#wiz-jobbox',{timeout:15000});
 const tjob=await waitJob(base,'transcribe_audio',['completed','failed'],180000);
 if(tjob.status!=='completed')throw Error('transcription failed: '+tjob.error);
 await p.waitForSelector('.stepper',{timeout:20000});   // redirected to project workspace

 // 3) transcript tab shows timestamped segments
 await p.click('[data-ptab="transcript"]');await p.waitForSelector('.segrow');
 await p.screenshot({path:'docs/images/project-transcript.png',fullPage:true});

 // 4) script tab: write + save + approve
 await p.click('[data-ptab="script"]');await p.waitForSelector('#proj-script');
 await p.fill('#proj-script','سناریوی تست: در این ویدیو تنظیمات مودم را باز می‌کنیم و تغییرات را ذخیره می‌کنیم.');
 await p.click('#proj-script-save');await p.waitForSelector('#proj-approve-script:not([disabled])');
 await p.click('#proj-approve-script');await p.waitForFunction(()=>document.querySelector('#projbody')?.innerText.includes('تأیید سناریو برای ضبط')===false||document.querySelector('#projbody')?.innerText.includes('تأیید شد'));
 await p.screenshot({path:'docs/images/project.png',fullPage:true});

 // 5) media tab: upload screen fixture
 await p.click('[data-ptab="media"]');await p.waitForSelector('#pm-drop');
 await p.setInputFiles('#pm-file','tests/fixtures/screen-sample.mp4');
 await p.waitForFunction(()=>document.querySelectorAll('[data-mediadetail]').length>=2,null,{timeout:60000});

 // 6) manual transcript for the screen fixture (deterministic editing input)
 await p.click('[data-mediadetail]');await p.waitForSelector('#media-player');
 await p.locator('#media-detail details').first().evaluate(d=>{d.open=true;});
 await p.fill('#transcript-edit','0:10 برای شروع تنظیمات مودم را باز کنید\n1:05 این بخش سکوت است\n2:30 تنظیمات را ذخیره کنید\n3:20 تنظیمات را ذخیره کنید');
 await p.click('#transcript-save');await p.waitForSelector('#media-detail .segrow');
 await p.screenshot({path:'docs/images/editing.png',fullPage:true});
 await p.click('[data-close="media-dialog"]');

 // 7) edit tab: run analysis, check report, restore one cut
 await p.click('[data-ptab="edit"]');await p.waitForSelector('[data-editdetect]');
 await p.click('[data-editdetect]');
 await p.waitForSelector('#proj-edit-report [data-decision-state]',{timeout:90000});
 await p.screenshot({path:'docs/images/project-edit.png',fullPage:true});
 const restoreBtn=p.locator('#proj-edit-report [data-decision-state][data-state="restored"]').first();
 await restoreBtn.click();
 await p.waitForFunction(()=>document.querySelector('#proj-edit-report')?.innerText.includes('بازگردانده شد'));

 // 8) preview render -> job completes
 await p.click('[data-renderkind="preview"]');
 await waitJob(base,'render_cut',['completed','failed'],180000).then(j=>{if(j.status!=='completed')throw Error('preview failed: '+j.error);});

 // 9) play preview through ranged request
 const renders=await (await fetch(base+'/api/renders')).json();
 const prev=renders.find(r=>r.kind==='preview');
 if(!prev)throw Error('no preview render row');
 const rng=await fetch(base+'/api/renders/file?id='+prev.id,{headers:{Range:'bytes=0-99'}});
 if(rng.status!==206)throw Error('ranged playback failed: '+rng.status);

 // 10) final render -> approval center -> approve -> FINAL exists
 await p.click('[data-ptab="edit"]');await p.waitForSelector('[data-renderkind="final"]');
 await p.click('[data-renderkind="final"]');
 const fj=await waitJob(base,'render_cut',['waiting_approval'],60000);
 await p.click('#nav a[href="#/approvals"]');
 await p.waitForSelector('[data-jobaction="approve"]');
 await p.screenshot({path:'docs/images/approvals.png',fullPage:true});
 await p.click('[data-jobaction="approve"]');
 await waitJob(base,'render_cut',['completed'],180000).then(async()=>{
  const rs=await (await fetch(base+'/api/renders')).json();
  if(!rs.some(r=>r.kind==='final'))throw Error('FINAL version missing after approval');
 });

 // 11) publish approval -> dry run package
 await p.click('#nav a[href="#/approvals"]');
 await p.waitForSelector('[data-decide2]');
 await p.locator('[data-decide2][data-gate="publish"][data-status="approved"]').first().click();
 await waitJob(base,'publish_dryrun',['completed'],60000);
 await p.click('#nav a[href="#/publishing"]');
 await p.waitForFunction(()=>document.querySelector('#view').innerText.includes('بسته‌های dry-run'));

 // 12) jobs / storage / services pages render with real data
 await p.click('#nav a[href="#/jobs"]');await p.waitForSelector('.table');
 await p.screenshot({path:'docs/images/jobs.png',fullPage:true});
 await p.click('#nav a[href="#/storage"]');await p.waitForFunction(()=>document.querySelector('#view').innerText.includes('My Passport'));
 await p.screenshot({path:'docs/images/storage.png',fullPage:true});
 await p.click('#nav a[href="#/services"]');await p.waitForFunction(()=>document.querySelector('#view').innerText.includes('NVENC'));
 await p.screenshot({path:'docs/images/health.png',fullPage:true});

 // 13) mobile viewport sanity (Poco X7 Pro ~ 1220x2712 css 393px)
 await p.setViewportSize({width:393,height:851});
 await p.goto(base+'/#/approvals');await p.waitForSelector('.rows');
 await p.screenshot({path:'docs/images/mobile.png',fullPage:true});

 if(errors.length)throw Error('browser errors:\n'+errors.join('\n'));
 console.log('PASS: full user journey via UI — wizard+voice upload, real transcription, transcript with timestamps, script save+approve, media upload, manual transcript, edit analysis, restore, preview render (206 ranged playback), final render approval, publish dry-run, jobs/storage/health pages, mobile layout, no console errors.');
 await browser.close();await stop();
})().catch(async e=>{console.error(e);if(browser)await browser.close();if(server&&!server.killed)server.kill();process.exit(1);});
