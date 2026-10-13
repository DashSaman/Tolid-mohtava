"""One-video educational editing, immutable review snapshots and real previews."""
import json,sqlite3,uuid,hashlib,time,threading
from datetime import datetime,timezone
from pathlib import Path
from contextlib import contextmanager
from jobs import DependencyMissing,JobCancelled
from video_edit import plan_fingerprint

DEFAULT_OPTIONS={'semantic':True,'zooms':True,'subtitles':True,'denoise':True,'shorts':True}

class AutoEditPlans:
    def __init__(self,db_path):
        self.path=db_path
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS auto_edit_plans(id TEXT PRIMARY KEY,media_id TEXT NOT NULL,document TEXT NOT NULL,created_at TEXT NOT NULL)')
            c.execute('CREATE INDEX IF NOT EXISTS auto_plans_media ON auto_edit_plans(media_id,created_at)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c:yield c
        finally:c.close()
    def save(self,plan):
        row=dict(plan);row.setdefault('id',uuid.uuid4().hex)
        row['created_at']=datetime.now(timezone.utc).isoformat()
        row['fingerprint']=plan_fingerprint(row['raw_sha'],row['transcript_revision'],row['cuts'],row['options'],row['zooms'])
        with self.connect() as c:c.execute('INSERT INTO auto_edit_plans VALUES(?,?,?,?)',(row['id'],row['media_id'],json.dumps(row,ensure_ascii=False),row['created_at']))
        return row
    def get(self,pid):
        with self.connect() as c:row=c.execute('SELECT document FROM auto_edit_plans WHERE id=?',(pid,)).fetchone()
        return json.loads(row[0]) if row else None
    def latest(self,mid):
        with self.connect() as c:row=c.execute('SELECT document FROM auto_edit_plans WHERE media_id=? ORDER BY created_at DESC LIMIT 1',(mid,)).fetchone()
        return json.loads(row[0]) if row else None

def validate_plan(plan,media,transcript,cuts):
    if not plan or not media or not transcript:raise ValueError('پیش‌نمایش یا متن منبع پیدا نشد.')
    if plan['media_id']!=media['id'] or plan['raw_sha']!=media['sha256']:raise ValueError('منبع پیش‌نمایش تغییر کرده است.')
    fingerprint=plan_fingerprint(media['sha256'],transcript['revision'],cuts,plan['options'],plan['zooms'])
    if fingerprint!=plan['fingerprint']:raise ValueError('متن یا برش‌ها پس از پیش‌نمایش تغییر کرده‌اند؛ پیش‌نمایش تازه بسازید.')

_locks={};_guard=threading.Lock()
def _media_mutex(mid):
    with _guard:return _locks.setdefault(mid,threading.Lock())
@contextmanager
def edit_mutation(mid):
    lock=_media_mutex(mid)
    if not lock.acquire(blocking=False):raise ValueError('تدوین این ویدیو در حال اجراست؛ پس از پایان یا لغو، تغییر را ذخیره کنید.')
    try:yield
    finally:lock.release()
@contextmanager
def media_lock(ctx,mid):
    lock=_media_mutex(mid)
    while not lock.acquire(timeout=.5):
        if ctx.cancelled():raise JobCancelled()
    try:yield
    finally:lock.release()

def locked_handler(handler):
    def run(ctx):
        with media_lock(ctx,ctx.payload.get('media_id')):return handler(ctx)
    return run

def options(payload):
    supplied=payload.get('options') or {}
    if not isinstance(supplied,dict) or any(k not in DEFAULT_OPTIONS for k in supplied):raise ValueError('تنظیم تدوین ناشناخته است.')
    if any(type(v)!=bool for v in supplied.values()):raise ValueError('تنظیمات تدوین باید روشن یا خاموش باشند.')
    return DEFAULT_OPTIONS|supplied

def auto_edit_video_handler(ctx):
    from transcribe import transcribe_audio_handler
    from editing import scan_silences
    from video_edit import educational_silence_cuts,semantic_decisions
    from visual_edit import screen_activity,semantic_proposals,zoom_proposals
    from video_render import probe_streams,render_educational
    from types import SimpleNamespace
    mid=ctx.payload.get('media_id');s=ctx.services
    with media_lock(ctx,mid):
        media=s['media'].get(mid)
        if not media or not media.get('exists',Path(media['path']).is_file()):raise ValueError('ویدیوی منبع موجود نیست.')
        info=probe_streams(media['path'])
        if not info['video'] or not info['audio']:raise ValueError('تدوین خودکار به ویدیوی دارای صدا نیاز دارد.')
        if not s['media'].verify(mid):raise ValueError('Checksum فایل RAW با نسخهٔ ثبت‌شده یکسان نیست.')
        opts=options(ctx.payload);plans=AutoEditPlans(s['store'].path)
        old=plans.latest(mid)
        refresh=bool(ctx.payload.get('refresh'))
        if refresh and not old:raise ValueError('ابتدا تدوین خودکار اولیه را اجرا کنید.')
        transcript=s['transcripts'].get(mid)
        if not transcript:
            ctx.log('تبدیل گفتار فارسی و ثبت زمان واژه‌ها');ctx.progress(3)
            sub=SimpleNamespace(id=ctx.id,payload={'media_id':mid},services=s,log=ctx.log,progress=lambda n:ctx.progress(3+n*.22),cancelled=ctx.cancelled)
            transcribe_audio_handler(sub);transcript=s['transcripts'].get(mid)
        if ctx.cancelled():raise JobCancelled()
        segments=transcript['segments'];duration=info['duration'];report=[]
        if not refresh:
            ctx.progress(26);ctx.log('تحلیل سکوت، حرکت صفحه و بخش‌های آموزشی')
            silences=scan_silences(media['path'])
            if silences is None:raise DependencyMissing('تشخیص سکوت FFmpeg اجرا نشد؛ پیش‌نمایش ساخته نشد.')
            activity=screen_activity(media['path'],silences,ctx)
            cuts=educational_silence_cuts(silences,segments,duration,activity)
            dec=s['decisions'];dec.drop_active_auto(mid)
            for a,b in cuts:
                if dec.user_had_verdict(mid,a,b,'long_pause') is None:dec.add(mid,a,b,'long_pause',.95,'automatic','active',transcript['revision'],reason='سکوت بدون فعالیت صفحه؛ مکث خواندن و انتظار آموزشی حفظ شد.')
            report.append({'step':'silence','detected':len(silences),'active':len(cuts),'screen_activity_windows':len(activity)})
            if opts['semantic']:
                ctx.log('بررسی برداشت‌های تکراری با مدل محلی');ctx.progress(38)
                proposals=semantic_proposals(segments,s['ai'],ctx)
                accepted=semantic_decisions(proposals,segments,duration,existing_cuts=dec.timeline(mid))
                # One shared removal budget for acoustic and semantic cuts.
                applied=0
                for d in accepted:
                    existing=dec.timeline(mid)
                    from render import keep_ranges
                    candidate=existing+[(d['start'],d['end'])]
                    kept=sum(b-a for a,b in keep_ranges(candidate,duration))
                    if duration-kept>duration*.2:continue
                    if dec.user_had_verdict(mid,d['start'],d['end'],'repeat') is None:
                        dec.add(mid,d['start'],d['end'],'repeat',d['confidence'],'automatic','active',transcript['revision'],reason=d['reason'])
                        applied+=1
                report.append({'step':'semantic','proposed':len(proposals),'validated':len(accepted),'applied':applied})
            ctx.progress(48)
            zooms=zoom_proposals(media['path'],duration,segments,s['ai'],ctx) if opts['zooms'] else []
            report.append({'step':'zooms','accepted':len(zooms)})
        else:
            opts=options(ctx.payload) if 'options' in ctx.payload else old['options']
            indices=ctx.payload.get('zoom_indices',list(range(len(old['zooms']))))
            if not isinstance(indices,list) or any(type(i)!=int or not 0<=i<len(old['zooms']) for i in indices):raise ValueError('انتخاب زوم معتبر نیست.')
            zooms=[z for i,z in enumerate(old['zooms']) if i in indices] if opts['zooms'] else []
            report=old.get('report',[])+[{'step':'refresh','note':'برش‌های فعلی و متن فعلی بدون تحلیل مجدد استفاده شدند.'}]
        cuts=s['decisions'].timeline(mid)
        plan={'id':uuid.uuid4().hex,'media_id':mid,'raw_sha':media['sha256'],'transcript_revision':transcript['revision'],
              'cuts':cuts,'options':opts,'zooms':zooms,'report':report,'source_duration':duration}
        plan['fingerprint']=plan_fingerprint(media['sha256'],transcript['revision'],cuts,opts,zooms)
        ctx.log('ساخت پیش‌نمایش یکپارچه با صدا، زیرنویس و زوم');ctx.progress(60)
        check=lambda:validate_plan(plan,s['media'].get(mid),s['transcripts'].get(mid),s['decisions'].timeline(mid))
        result=render_educational(ctx,media,transcript,plan,'preview',before_register=check)
        plan['preview_id']=result['render_id'];plan['duration']=result['duration']
        row=plans.save(plan)
        ctx.log('پیش‌نمایش آماده است؛ نسخهٔ نهایی به تأیید همین برش‌ها نیاز دارد.')
        return {'plan_id':row['id'],**result,'report':report,'zooms':zooms,'fingerprint':row['fingerprint']}

def auto_edit_final_handler(ctx):
    from video_render import render_educational
    s=ctx.services;plan=AutoEditPlans(s['store'].path).get(ctx.payload.get('plan_id'))
    if not plan:raise ValueError('پیش‌نمایش تدوین خودکار پیدا نشد.')
    with media_lock(ctx,plan['media_id']):
        media=s['media'].get(plan['media_id']);transcript=s['transcripts'].get(plan['media_id'])
        validate_plan(plan,media,transcript,s['decisions'].timeline(plan['media_id']))
        if not ctx.payload.get('approved'):
            return {'waiting_approval':True,'question':'نسخهٔ نهایی همین پیش‌نمایش، با زیرنویس، بهبود صدا و زوم‌های بررسی‌شده ساخته شود؟','plan_id':plan['id'],'preview_id':plan['preview_id']}
        if not s['media'].verify(media['id']):raise ValueError('فایل RAW تغییر کرده است؛ تأیید قبلی معتبر نیست.')
        check=lambda:validate_plan(plan,s['media'].get(media['id']),s['transcripts'].get(media['id']),s['decisions'].timeline(media['id']))
        final=render_educational(ctx,media,transcript,plan,'final',before_register=check)
        shorts=[]
        if plan['options']['shorts']:
            from captions import retime_captions
            from render import keep_ranges
            from shorts import shorts_candidates,render_short_handler
            from types import SimpleNamespace
            cues=retime_captions(transcript['segments'],keep_ranges(plan['cuts'],plan['source_duration']))
            # The complete edited video is used as source, so Shorts inherit all reviewed cuts.
            candidates=shorts_candidates(cues,final['duration'],count=2,target=30)
            source_media=dict(media,path=s['renders'].get(final['render_id'])['path'],duration=final['duration'])
            class FinalSource:
                def get(self,mid):return source_media if mid==media['id'] else None
            for candidate in candidates:
                if ctx.cancelled():raise JobCancelled()
                sub=SimpleNamespace(id=ctx.id,payload={'media_id':media['id'],'start':candidate['start'],'end':candidate['end']},
                    services=s|{'media':FinalSource()},log=ctx.log,progress=lambda _:None,cancelled=ctx.cancelled)
                shorts.append(render_short_handler(sub))
        return {**final,'plan_id':plan['id'],'shorts':shorts,'privacy':'local_only'}
