// Audio recording UX v2: device selector, mic test, live level, states, preview, re-record.
// Mounted into wizard step-3 record mode. Exposed as window.Recorder for tests.
(function(){
const LS_KEY='tn-preferred-mic';
const SILENT_MS=6000, LEVEL_WARN=0.035;
let audioCtx,analyser,rafId,stream,recorder,chunks=[],level=0,silentSince=0,timerId=null;
let state='آماده ضبط'; // آماده ضبط | در حال ضبط | مکث | متوقف شد | ذخیره شد | خطای میکروفون | بدون صدای قابل تشخیص
let deviceIds=[],deviceId=localStorage.getItem(LS_KEY)||'',startedAt=0,elapsed=0;

async function ensurePermission(){
  try{
    const st=await navigator.mediaDevices.getUserMedia({audio:true});
    st.getTracks().forEach(t=>t.stop());
    return {granted:true};
  }catch(e){
    const n=(e&&e.name)||'';
    if(n==='NotAllowedError'||n==='SecurityError') return {granted:false,msg:'دسترسی میکروفون رد شد؛ از تنظیمات مرورگر اجازه دهید.'};
    if(n==='NotFoundError'||n==='DevicesNotFoundError') return {granted:false,msg:'هیچ میکروفونی پیدا نشد.'};
    if(n==='NotReadableError'||n==='TrackStartError') return {granted:false,msg:'میکروفون اشغال دستگاه دیگری است (device busy).'};
    if(n==='OverconstrainedError') return {granted:false,msg:'میکروفون انتخاب‌شده در دسترس نیست.'};
    return {granted:false,msg:'خطای مرورگر در باز کردن میکروفون: '+(e.message||n)};
  }
}
async function listMics(){
  const p=await ensurePermission();
  if(!p.granted){return {err:p.msg,devices:[]};}
  const devs=await navigator.mediaDevices.enumerateDevices();
  return {devices:devs.filter(d=>d.kind==='audioinput')};
}
async function openStream(){
  const c={audio:true};
  if(deviceId)c.audio={deviceId:{exact:deviceId}};
  try{return await navigator.mediaDevices.getUserMedia(c);}
  catch(e){
    if(deviceId&&(e.name==='OverconstrainedError'||e.name==='NotFoundError')){
      throw new Error('میکروفون انتخاب‌شده در دسترس نیست.');
    }
    throw e;
  }
}
function attachMeter(st){
  audioCtx=audioCtx||new (window.AudioContext||window.webkitAudioContext)();
  const src=audioCtx.createMediaStreamSource(st);
  analyser=audioCtx.createAnalyser();analyser.fftSize=1024;
  src.connect(analyser);
  const buf=new Uint8Array(analyser.frequencyBinCount);
  const tick=()=>{
    analyser.getByteTimeDomainData(buf);
    let sum=0;for(let i=0;i<buf.length;i++){const v=(buf[i]-128)/128;sum+=v*v;}
    level=Math.sqrt(sum/buf.length);
    const bar=document.getElementById('mic-level-bar');
    if(bar){bar.style.width=Math.min(100,Math.round(level*260))+'%';}
    const t=document.getElementById('rec-time');
    if(t&&state==='در حال ضبط'){elapsed=Date.now()-startedAt;t.textContent=fmt(elapsed);}
    const warn=document.getElementById('mic-silent-warn');
    if(warn){
      if(state==='در حال ضبط'){
        if(level<LEVEL_WARN){ if(!silentSince)silentSince=Date.now();
          if(Date.now()-silentSince>SILENT_MS)warn.style.display='block';
        } else {silentSince=0;warn.style.display='none';}
      } else warn.style.display='none';
    }
    rafId=requestAnimationFrame(tick);
  };
  cancelAnimationFrame(rafId);tick();
}
function fmt(ms){const s=Math.floor(ms/1000);return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function setState(st,detail){
  state=st;const el=document.getElementById('rec-state');
  if(el){el.textContent=st+(detail?' · '+detail:'');el.dataset.state=st;}
}
async function micTest(){
  const out=document.getElementById('mictest-out');
  out.textContent='در حال تست… (صحبت کنید)';out.style.color='';
  let st;try{st=await openStream();}catch(e){out.textContent=e.message||'دسترسی میکروفون ممکن نشد.';out.style.color='#fca5a5';return;}
  attachMeter(st);
  const t0=Date.now();let peakAll=0;
  const iv=setInterval(()=>{peakAll=Math.max(peakAll,level);},100);
  setTimeout(()=>{
    clearInterval(iv);cancelAnimationFrame(rafId);
    st.getTracks().forEach(t=>t.stop());
    if(peakAll>LEVEL_WARN){out.textContent='میکروفون فعال است (سطح ورودی دیده شد)';out.style.color='#a7f3d0';}
    else{out.textContent='صدایی از میکروفون دریافت نمی‌شود.';out.style.color='#fca5a5';}
  },4000);
}
async function startRec(){
  if(state==='در حال ضبط'||state==='مکث')return; // prevent double-start
  let st;try{st=await openStream();}catch(e){setState('خطای میکروفون',e.message);alertPersian(e.message);return;}
  stream=st;chunks=[];
  try{recorder=new MediaRecorder(st);}catch(e){setState('خطای میکروفون','MediaRecorder: '+e.message);st.getTracks().forEach(t=>t.stop());return;}
  recorder.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data);};
  recorder.onstop=()=>finish(st);
  recorder.start(250);
  startedAt=Date.now()-elapsed;silentSince=0;
  attachMeter(st);
  setState('در حال ضبط');
  document.getElementById('rec-start').disabled=true;
  document.getElementById('rec-pause').disabled=false;
  document.getElementById('rec-stop').disabled=false;
}
function pauseRec(){
  if(!recorder||recorder.state!=='recording')return;
  recorder.pause();elapsed=Date.now()-startedAt;setState('مکث');
  document.getElementById('rec-pause').disabled=true;
  document.getElementById('rec-resume').disabled=false;
}
function resumeRec(){
  if(!recorder||recorder.state!=='paused')return;
  recorder.resume();startedAt=Date.now()-elapsed;setState('در حال ضبط');
  document.getElementById('rec-pause').disabled=false;
  document.getElementById('rec-resume').disabled=true;
}
function stopRec(){
  if(recorder&&recorder.state!=='inactive'){setState('در حال ذخیره');recorder.stop();}
}
function alertPersian(m){const el=document.getElementById('rec-state');if(el){setState('خطای میکروفون',m);}}
async function finish(st){
  cancelAnimationFrame(rafId);
  st.getTracks().forEach(t=>t.stop());
  const blob=new Blob(chunks,{type:(recorder&&recorder.mimeType)||'audio/webm'});
  document.getElementById('rec-start').disabled=false;
  document.getElementById('rec-pause').disabled=true;
  document.getElementById('rec-stop').disabled=true;
  if(blob.size<1000){setState('بدون صدای قابل تشخیص','فایل خالی');window.__recInvalid('فایل ضبط شد اما داده‌ای ندارد.');return;}
  setState('ذخیره شد',Math.round(blob.size/1024)+'KB');
  window.__recDone(blob,deviceId);
}
window.Recorder={listMics,micTest,startRec,pauseRec,resumeRec,stopRec,
  setDevice:id=>{deviceId=id;localStorage.setItem(LS_KEY,id);},
  getDevice:()=>deviceId,getState:()=>state,getLevel:()=>level,
  _states:()=>({SILENT_MS,LEVEL_WARN})};
})();
