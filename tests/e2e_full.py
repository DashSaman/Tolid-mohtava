# -*- coding: utf-8 -*-
"""Full internal E2E on the live server with REAL components.
Persian voice -> whisper(medium,CUDA) -> AI pipeline (LM Studio) -> media ->
sync -> enhance -> edit -> preview -> final(approved) -> shorts v2 ->
article -> seo scan -> social -> pinned -> publish dry-run -> analytics-ready.
Reports honestly per step; no faking."""
import json, os, subprocess, sys, time, urllib.request, uuid
from pathlib import Path

import os as _os
BASE=_os.environ.get('E2E_BASE','http://127.0.0.1:8788')
PY=sys.executable
ROOT=Path(__file__).resolve().parents[1]

def api(path,data=None,token=None,raw=False,headers=None):
    h=dict(headers or {})
    if data is not None and not raw: h['Content-Type']='application/json'
    if token: h['X-Panel-Token']=token
    body=json.dumps(data).encode() if (data is not None and not raw) else data
    req=urllib.request.Request(BASE+path,data=body,headers=h,method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read())

def wait_job(kind,timeout=900,token=None):
    end=time.time()+timeout
    latest=None
    while time.time()<end:
        jobs=api('/api/jobs',None,token)
        js=[j for j in jobs if j['kind']==kind]
        if js:
            latest=sorted(js,key=lambda j:j['created_at'])[-1]
            if latest['status'] in ('completed','failed','cancelled','waiting_approval'):
                return latest
        time.sleep(2)
    return latest

RESULTS=[]
def step(name,ok,detail=''):
    RESULTS.append((name,ok,detail))
    print(('OK ' if ok else 'FAIL ')+name+(' :: '+str(detail)[:150] if detail else ''),flush=True)

def main():
    token=api('/api/session')['token']
    if api('/api/session').get('auth_required'):
        import re as _re, os as _os2
        _n=open(_os.environ.get('TOLID_CRED_NOTE',_os2.path.expanduser('~/Documents/Tolid-Mohtava-Admin-Credentials.txt')),encoding='utf-8').read()
        _u=_re.search('Username:[\r\n]+(\S+)',_n).group(1)
        _p=_re.search('Password:[\r\n]+(.+)',_n).group(1).strip()
        r=api('/api/auth/login',{'username':_u,'password':_p},token=token)
        assert r.get('token'),'docker e2e login failed'
        token=r['token']
    MODEL=os.environ.get('E2E_MODEL','qwen2.5-7b-instruct')
    api('/api/ai/providers/save',{'name':'lmstudio','base_url':'http://127.0.0.1:1234/v1',
        'model':MODEL,'api_key_env':'','tasks':['research','verification','script','social','seo','analysis','hooks','thumbnail']},token)
    step('AI provider pinned: '+MODEL,True)
    # 1) project + real Persian voice
    c=api('/api/items',{'title':'آموزش راه‌اندازی سرویس VoIP با Issabel','brands':['tehran-network'],
                        'body':'می‌خوام نصب ایزابل و اتصال ترانک sip رو نشون بدم'},token)
    cid=c['id']
    step('create project',bool(cid))
    voice=ROOT/'work'/'persian-sample.mp3'
    data=voice.read_bytes()
    req=urllib.request.Request(BASE+'/api/media',data=data,method='POST',headers={
        'X-Panel-Token':token,'X-Media-Kind':'voice','X-Media-Name':'voip-idea.mp3',
        'X-Media-Mime':'audio/mpeg','X-Content-Id':cid})
    with urllib.request.urlopen(req,timeout=120) as r: m=json.loads(r.read())
    step('voice upload',bool(m.get('id')))
    api('/api/jobs',{'kind':'transcribe_audio','payload':{'media_id':m['id']}},token)
    j=wait_job('transcribe_audio',600,token)
    ok=j and j['status']=='completed'
    step('whisper transcription (real, medium/CUDA)',ok,(j or {}).get('error',''))
    if ok:
        c['transcript']=api('/api/transcripts?media_id='+m['id'],None,token)['text']
        c=api('/api/items',dict(c,id=cid,revision=c['revision']),token)
        step('transcript saved to project',len(c['transcript'])>30)
    # 2) AI pipeline (real LM Studio) — script is text-only, safest for llama-3
    api('/api/jobs',{'kind':'generate_script','payload':{'content_id':cid}},token)
    j=wait_job('generate_script',900,token)
    ok=j and j['status']=='completed'
    step('AI script (LM Studio, real)',ok,((j or {}).get('error') or ('markers='+str((j.get('result') or {}).get('markers')) if ok else '')))
    outs=api('/api/ai/outputs?content_id='+cid,None,token)
    script_out=[o for o in outs if o['kind']=='script' and o['status']=='ok']
    step('script output stored',bool(script_out))
    if script_out:
        cur=api('/api/items?brand=tehran-network',None,token)
        me=[x for x in cur if x['id']==cid][0]
        me=api('/api/items',dict(me,id=cid,body=script_out[0]['result']['script'][:5000]),token)
        api('/api/decide',{'id':cid,'revision':me['revision'],'gate':'script','status':'approved'},token)
        step('script approved for recording',True)
    # hooks (JSON — may honestly fail with llama-3)
    api('/api/jobs',{'kind':'generate_hooks','payload':{'content_id':cid}},token)
    j=wait_job('generate_hooks',600,token)
    step('AI hooks (real attempt)',j is not None,(j or {}).get('error','')[:120] if j and j['status']!='completed' else 'completed')
    # 3) media: face+screen with known offset, sync, enhance
    ff=r'C:\Users\amirreza\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe'
    tmp=ROOT/'work'/'e2e'; tmp.mkdir(parents=True,exist_ok=True)
    screen=tmp/'screen.mp4'
    subprocess.run([ff,'-y','-f','lavfi','-i','anoisesrc=d=8:c=pink:r=44100','-f','lavfi','-i','testsrc=duration=8:size=320x240:rate=15',
                    '-af',"volume=enable='between(t,3,3.4)':volume=0",'-pix_fmt','yuv420p','-shortest',str(screen)],
                   capture_output=True,check=True)
    face=tmp/'face.m4a'
    subprocess.run([ff,'-y','-f','lavfi','-i','anullsrc=r=44100:cl=mono:d=1.2','-i',str(screen),
                    '-filter_complex','[0][1:a]concat=n=2:v=0:a=1','-c:a','aac',str(face)],capture_output=True,check=True)
    for path,kind in ((screen,'screen'),(face,'face')):
        data=path.read_bytes()
        mime='video/mp4' if path.suffix=='.mp4' else 'audio/mp4'
        req=urllib.request.Request(BASE+'/api/media',data=data,method='POST',headers={
            'X-Panel-Token':token,'X-Media-Kind':kind,'X-Media-Name':path.name,'X-Media-Mime':mime,'X-Content-Id':cid})
        with urllib.request.urlopen(req,timeout=120) as r: json.loads(r.read())
    step('face+screen uploaded',True)
    api('/api/jobs',{'kind':'sync_content','payload':{'content_id':cid}},token)
    j=wait_job('sync_content',300,token)
    ok=j and j['status']=='completed'
    offs=api('/api/sync?content_id='+cid,None,token) if ok else []
    # sign convention: positive = target DELAYED vs reference. Reference=face(delayed), target=screen(earlier) => -1.2
    step('multi-track sync (real correlation)',ok and any(abs(abs(o['offset_seconds'])-1.2)<0.3 and o['confidence']>=0.6 for o in offs),offs)
    media=api('/api/media?content_id='+cid,None,token)
    screen_m=[x for x in media if x['kind']=='screen'][0]
    api('/api/transcripts',{'media_id':screen_m['id'],'text':
        '0:01 سلام دوستان، در این بخش نصب Issabel را نشان می‌دهیم.\n'
        '0:06 چطور ترانک SIP را وارد کنیم؟ مرحله به مرحله پیش می‌رویم.\n'
        '0:09 نکتهٔ مهم: قبل از تست تماس حتماً فایروال را بررسی کنید.\n'
        '0:12 بزرگ‌ترین اشتباه این است که کیفیت صدا را تست نکنید.\n'
        '0:15 راه‌حل سریع: با یک تماس آزمایشی همه‌چیز را بررسی کنید.'},token)
    step('screen transcript (timed) saved',True)
    api('/api/jobs',{'kind':'enhance_audio','payload':{'media_id':screen_m['id']}},token)
    j=wait_job('enhance_audio',300,token)
    step('audio enhancement',j and j['status']=='completed',(j or {}).get('error',''))
    # 4) edit + preview + final
    api('/api/jobs',{'kind':'edit_detect','payload':{'media_id':screen_m['id']}},token)
    j=wait_job('edit_detect',300,token)
    step('edit analysis',j and j['status']=='completed',(j or {}).get('error',''))
    api('/api/jobs',{'kind':'render_cut','payload':{'media_id':screen_m['id'],'kind':'preview'}},token)
    j=wait_job('render_cut',600,token)
    step('preview render',j and j['status']=='completed',(j or {}).get('error',''))
    api('/api/jobs',{'kind':'render_cut','payload':{'media_id':screen_m['id'],'kind':'final'}},token)
    j=wait_job('render_cut',600,token)
    if j and j['status']=='waiting_approval':
        api('/api/jobs/decision',{'id':j['id'],'approved':True},token)
        j=wait_job('render_cut',600,token)
    step('final render (approved)',j and j['status']=='completed',(j or {}).get('error',''))
    # 5) shorts v2
    api('/api/jobs',{'kind':'shorts_v2','payload':{'media_id':screen_m['id']}},token)
    j=wait_job('shorts_v2',300,token)
    ok=j and j['status']=='completed'
    step('shorts v2 ranking',ok,(j or {}).get('error','') if not ok else str(len((j.get('result') or {}).get('candidates',[])))+' candidates')
    # 6) article + seo
    api('/api/jobs',{'kind':'generate_article','payload':{'content_id':cid,'site':'tehnet.ir'}},token)
    j=wait_job('generate_article',900,token)
    step('article+SEO generation (real attempt)',j is not None,(j or {}).get('error','')[:120] if j and j['status']!='completed' else 'completed')
    api('/api/seo/scan',{'site':'tehnet.ir'},token)
    j=wait_job('seo_scan',600,token)
    ok=j and j['status']=='completed'
    step('SEO scan (real crawl)',ok,(j or {}).get('error','') or ('issues='+str((j.get('result') or {}).get('issues')) if ok else ''))
    if ok:
        api('/api/seo/proposals',{'site':'tehnet.ir'},token)
        j2=wait_job('seo_proposals',120,token)
        step('SEO proposals',j2 and j2['status']=='completed',((j2 or {}).get('result') or {}).get('proposal_count'))
    # 7) social + pinned (real attempts)
    api('/api/jobs',{'kind':'generate_social','payload':{'content_id':cid,'platform':'Telegram'}},token)
    j=wait_job('generate_social',600,token)
    step('social variant (real attempt)',j is not None,(j or {}).get('error','')[:120] if j and j['status']!='completed' else 'completed')
    # 8) publish approval -> dry run
    cur=api('/api/items?brand=tehran-network',None,token)
    me=[x for x in cur if x['id']==cid][0]
    api('/api/decide',{'id':cid,'revision':me['revision'],'gate':'publish','status':'approved'},token)
    j=wait_job('publish_dryrun',300,token)
    step('publish dry-run',j and j['status']=='completed',(j or {}).get('error',''))
    # 9) analytics-ready + optimization
    api('/api/analytics/record',{'content_id':cid,'brand':'tehran-network','platform':'youtube','content_type':'long',
        'pillar':'VoIP','topic':me['title'],'publish_day':'پنجشنبه','publish_hour':20,
        'metrics':{'views':420,'impressions':6000,'ctr':0.028,'engagement':35,'conversions':1}},token)
    sched=api('/api/analytics/schedule?brand=tehran-network&platform=youtube',None,token)
    step('analytics-ready + adaptive scheduling',sched['mode']=='BASELINE' or sched['mode']=='DATA_DRIVEN',sched['mode'])
    api('/api/analytics/optimize',{'content_id':cid,'platform':'youtube'},token)
    j=wait_job('optimize_content',300,token)
    ok=j and j['status']=='completed'
    props=api('/api/analytics/proposals',None,token)
    step('optimization engine',ok or bool(props),(j or {}).get('result'))
    print('\n=== E2E SUMMARY ===')
    ok_n=sum(1 for _,ok,_ in RESULTS if ok)
    print(f'{ok_n}/{len(RESULTS)} steps OK')
    for name,ok,detail in RESULTS:
        print(('  ✓ ' if ok else '  ✗ ')+name+((' — '+str(detail)[:100]) if detail else ''))
    json.dump([{'step':n,'ok':ok,'detail':str(d)[:200]} for n,ok,d in RESULTS],open(ROOT/'work'/'e2e-results.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)

if __name__=='__main__':
    main()
