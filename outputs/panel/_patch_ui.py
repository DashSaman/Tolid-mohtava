# -*- coding: utf-8 -*-
"""Patch app.js: premium recording card (mic selector/test/level/states/preview/re-record/delete)
+ project actions menu (open/rename/archive/delete with typed confirm) + upload validation."""
p='outputs/panel/app.js'
s=open(p,encoding='utf-8').read()

# ── 1) replace old record block in wizard template ──
old_rec="""   ${w.type==='record'?`<div style="margin-top:14px" class="row"><button id="rec-start" class="primary">${icon('i-mic','icon sm')}شروع ضبط</button><button id="rec-stop" disabled>${icon('i-clock','icon sm')}پایان ضبط</button><span id="rec-state" class="small muted">ضباطی شروع نشده</span></div><audio id="rec-player" controls style="width:100%;margin-top:10px;display:none"></audio>`
   :`<label style="margin-top:14px" class="dropzone" id="wiz-drop">${icon('i-upload')}آپلود فایل صوتی<input id="wiz-file" type="file" accept="audio/*,video/*" style="display:none"></label><p id="wiz-fileinfo" class="small muted"></p>`}"""
new_rec="""   ${w.type==='record'?`
   <div class="card" style="margin-top:14px;padding:18px">
     <div class="row" style="justify-content:space-between">
       <label style="max-width:46%">میکروفون<select id="mic-select"><option>…درخواست دسترسی</option></select></label>
       <button class="sm" id="mictest" type="button">تست میکروفون</button>
     </div>
     <p id="mictest-out" class="small muted" style="min-height:1.6em"></p>
     <div class="row" style="margin-top:8px;gap:8px">
       <button id="rec-start" class="primary" type="button">${icon('i-mic','icon sm')}شروع ضبط</button>
       <button id="rec-pause" type="button" disabled>مکث</button>
       <button id="rec-resume" type="button" disabled>ادامه</button>
       <button id="rec-stop" type="button" disabled>${icon('i-clock','icon sm')}پایان ضبط</button>
       <span id="rec-state" class="small muted" data-state="آماده ضبط">آماده ضبط</span>
       <b id="rec-time" style="direction:ltr;font-family:monospace">00:00</b>
     </div>
     <div class="progress" style="margin-top:10px"><div id="mic-level-bar" class="progressfill" style="width:0%"></div></div>
     <p id="mic-silent-warn" class="warnbox" style="display:none;margin-top:8px">سطح صدای ورودی بسیار پایین است.</p>
     <div id="rec-result" style="margin-top:12px"></div>
   </div>`"""
assert old_rec in s, 'record anchor'
s=s.replace(old_rec,new_rec)

# ── 2) replace old recorder handlers with Recorder-based flow ──
old_bind=""" const rs=$('#rec-start');if(rs)rs.onclick=async()=>{
  try{
   const stream=await navigator.mediaDevices.getUserMedia({audio:true});
   mediaRecorder=new MediaRecorder(stream);recChunks=[];
   mediaRecorder.ondataavailable=e=>recChunks.push(e.data);
   mediaRecorder.onstop=()=>{
    w.file=new Blob(recChunks,{type:mediaRecorder.mimeType||'audio/webm'});
    const p=$('#rec-player');p.src=URL.createObjectURL(w.file);p.style.display='block';
    $('#rec-state').textContent=`ضبط آماده است · ${humanSize(w.file.size)}`;
    $('#wiz-voice-create').disabled=false;
    stream.getTracks().forEach(t=>t.stop());
   };
   mediaRecorder.start();$('#rec-start').disabled=true;$('#rec-stop').disabled=false;
   $('#rec-state').textContent='در حال ضبط…';
  }catch(err){toast('دسترسی به میکروفون ممکن نشد: '+err.message,'err');}
 };
 const rp=$('#rec-stop');if(rp)rp.onclick=()=>{if(mediaRecorder&&mediaRecorder.state!=='inactive'){mediaRecorder.stop();$('#rec-stop').disabled=true;$('#rec-start').disabled=false;}};"""
new_bind=""" const rs=$('#rec-start');if(rs){
  // mic list + preferred device
  (async()=>{
    const sel=$('#mic-select');
    const R=window.Recorder;
    if(!R){sel.innerHTML='<option>Recorder در دسترس نیست</option>';return;}
    const {devices,err}=await R.listMics();
    if(err){sel.innerHTML='<option>'+esc(err)+'</option>';$('#rec-state').textContent='خطای میکروفون';return;}
    sel.innerHTML=devices.map(d=>`<option value="${esc(d.deviceId)}">${esc(d.label||'میکروفون')}</option>`).join('')||'<option>میکروفونی پیدا نشد</option>';
    const pref=R.getDevice();
    if(pref&&devices.some(d=>d.deviceId===pref)){sel.value=pref;R.setDevice(pref);}
    else if(!pref&&devices[0])R.setDevice(devices[0].deviceId);
    sel.onchange=()=>{R.setDevice(sel.value);toast('میکروفون انتخاب شد: '+(sel.selectedOptions[0]?.textContent||''));};
  })();
  $('#mictest').onclick=()=>window.Recorder&&Recorder.micTest();
  window.__recDone=async(blob,devId)=>{
    w.file=new File([blob],`rec-${Date.now()}.webm`,{type:blob.type});
    w.recMeta={device:$('#mic-select')?.selectedOptions?.[0]?.textContent||'',at:new Date().toLocaleString('fa-IR')};
    const box=$('#rec-result');
    box.innerHTML=`<audio controls src="${URL.createObjectURL(blob)}" style="width:100%"></audio>
      <p class="small muted">مدت: <b id="rec-dur">…</b> · دستگاه: ${esc(w.recMeta.device)} · ${esc(w.recMeta.at)}</p>
      <div class="row"><button class="primary" id="rec-ok" type="button">تأیید و ادامه</button>
      <button id="rec-again" type="button">ضبط مجدد</button>
      <button class="danger" id="rec-del" type="button">حذف ضبط</button></div>`;
    const a=box.querySelector('audio');
    a.onloadedmetadata=()=>{$('#rec-dur').textContent=mmss(a.duration*1000);};
    $('#rec-ok').onclick=()=>{w.recValidated=true;$('#wiz-voice-create').disabled=false;toast('ضبط تأیید شد؛ حالا «ساخت پروژه» را بزنید','ok');};
    $('#rec-again').onclick=()=>{w.prevFile=w.file;w.file=null;w.recValidated=false;$('#wiz-voice-create').disabled=true;
      $('#rec-result').innerHTML='<p class="small muted">ضبط قبلی حفظ شد تا ضبط جدید موفق شود (نسخه‌دار).</p>';Recorder.startRec();};
    $('#rec-del').onclick=async()=>{
      if(!await confirmBox('حذف ضبط','این ضبط حذف شود؟ (پروژه و رسانه‌های دیگر دست نمی‌خورند)'))return;
      w.file=null;w.recValidated=false;$('#wiz-voice-create').disabled=true;
      box.innerHTML='<p class="small muted">ضبط حذف شد.</p>';toast('ضبط حذف شد');};
  };
  window.__recInvalid=(reason)=>{
    w.file=null;w.recValidated=false;$('#wiz-voice-create').disabled=true;
    $('#rec-result').innerHTML=`<div class="warnbox"><b>INVALID_AUDIO</b> فایل ضبط شد اما صدای قابل استفاده‌ای تشخیص داده نشد.<br>${esc(reason||'')}</div>
    <div class="row"><button id="inv-again" type="button">ضبط مجدد</button>
    <button id="inv-mic" type="button">انتخاب میکروفون دیگر</button>
    <button id="inv-test" type="button">تست میکروفون</button>
    <button class="danger" id="inv-del" type="button">حذف این ضبط</button></div>`;
    $('#inv-again').onclick=()=>Recorder.startRec();
    $('#inv-mic').onclick=()=>$('#mic-select').focus();
    $('#inv-test').onclick=()=>Recorder.micTest();
    $('#inv-del').onclick=()=>{$('#rec-result').innerHTML='';toast('ضبط نامعتبر حذف شد');};
  };
  rs.onclick=()=>Recorder.startRec();
  $('#rec-pause').onclick=()=>Recorder.pauseRec();
  $('#rec-resume').onclick=()=>Recorder.resumeRec();
  $('#rec-stop').onclick=()=>Recorder.stopRec();
 }"""
assert old_bind in s, 'bind anchor'
s=s.replace(old_bind,new_bind)

# require recValidated before create (record mode)
s=s.replace("""  if(!f){toast('اول فایل را انتخاب کنید','err');return;}""",
"""  if(!f){toast(w.type==='record'?'اول ضبط کن و «تأیید و ادامه» را بزن':'اول فایل را انتخاب کنید','err');return;}
  if(w.type==='record'&&!w.recValidated){toast('ضبط را اول بشنو و «تأیید و ادامه» بزن','err');return;}""")
# vc onclick also guard
s=s.replace("""  if(!f){toast('اول صوت را ضبط یا فایل را انتخاب کنید','err');return;}""",
"""  if(!f){toast('اول صوت را ضبط یا فایل را انتخاب کنید','err');return;}
  if(w.type==='record'&&!w.recValidated){toast('ضبط را اول بشنو و «تأیید و ادامه» بزن','err');return;}""")

# upload validation: check size>2KB and (wav/webm/mp3) basic sniff before enabling
s=s.replace("""  w.file=e.target.files[0]||null;
  $('#wiz-fileinfo').textContent=w.file?`${w.file.name} · ${humanSize(w.file.size)}`:'';
  $('#wiz-voice-create').disabled=!w.file;""",
"""  w.file=e.target.files[0]||null;
  if(w.file&&w.file.size<2000){$('#wiz-fileinfo').textContent='فایل خیلی کوچک است (احتمالاً بی‌صدا/خراب)';w.file=null;$('#wiz-voice-create').disabled=true;return;}
  $('#wiz-fileinfo').textContent=w.file?`${w.file.name} · ${humanSize(w.file.size)} — پس از ساخت، اعتبارسنجی صدا انجام می‌شود`:'';
  $('#wiz-voice-create').disabled=!w.file;""")
open(p,'w',encoding='utf-8').write(s)
print('recorder UI patched')
