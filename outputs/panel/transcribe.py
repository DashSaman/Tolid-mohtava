"""Persian speech-to-text worker. Local-first, faster-whisper when available.

No fake transcripts: without a real engine the job fails BLOCKED_BY_DEPENDENCY.
Transcripts are versioned per media record; edits never overwrite history.
"""
import json, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from jobs import DependencyMissing
import media as media_mod

LANG='fa'

def engine_available():
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False

def engine_info():
    try:
        import faster_whisper
        import ctranslate2
        return {'name':'faster-whisper','version':getattr(faster_whisper,'__version__','?'),
                'ctranslate2':getattr(ctranslate2,'__version__','?')}
    except Exception as e:
        return {'name':'faster-whisper','error':str(e)}

def detect_device():
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count()>0: return 'cuda'
    except Exception:
        pass
    return 'cpu'

def _ensure_cuda_dlls():
    """Make pip-installed CUDA wheels (cublas/cudnn) loadable on Windows.

    ctranslate2 loads cublas64_12.dll with plain LoadLibrary semantics, so
    add_dll_directory alone is not enough — the dirs must also be on PATH.
    """
    import sys, os
    tried=[]
    added=[]
    for base in list(sys.path):
        if not base or 'site-packages' not in base: continue
        nvidia=Path(base)/'nvidia'
        if not nvidia.is_dir(): continue
        for sub in ('cublas','cudnn','cuda_nvrtc'):
            d=nvidia/sub/'bin'
            if d.is_dir() and str(d) not in added:
                added.append(str(d))
                try: os.add_dll_directory(str(d))
                except Exception: pass
                os.environ['PATH']=str(d)+os.pathsep+os.environ.get('PATH','')
                tried.append(str(d))
    return tried

def load_model(model_size='small'):
    from faster_whisper import WhisperModel
    device=detect_device()
    if device=='cuda': _ensure_cuda_dlls()
    compute='float16' if device=='cuda' else 'int8'
    try:
        return WhisperModel(model_size,device=device,compute_type=compute),device
    except Exception:
        if device=='cuda':
            return WhisperModel(model_size,device='cpu',compute_type='int8'),'cpu'
        raise

def _transcribe_with(model,path,segments_cb=None):
    seg_iter,info=model.transcribe(str(path),language=LANG,vad_filter=True)
    segments=[]; last=time.time()
    for s in seg_iter:
        segments.append({'start':round(s.start,3),'end':round(s.end,3),'text':s.text.strip()})
        if segments_cb and time.time()-last>2:
            segments_cb(min(99,int(s.end/max(info.duration,0.001)*100))); last=time.time()
    return segments,info

def run_engine(path,segments_cb=None,model_size='small'):
    """Real transcription. Returns dict with segments and metadata."""
    if not engine_available():
        raise DependencyMissing('faster-whisper نصب نیست. برای تبدیل گفتار به متن، این بسته را نصب کنید یا متن را دستی وارد کنید.')
    model,device=load_model(model_size)
    try:
        segments,info=_transcribe_with(model,path,segments_cb)
    except RuntimeError as e:
        msg=str(e).lower()
        gpu_broken=device=='cuda' and any(k in msg for k in ('cublas','cudnn','cuda'))
        if not gpu_broken: raise
        from faster_whisper import WhisperModel
        model=WhisperModel(model_size,device='cpu',compute_type='int8'); device='cpu'
        segments,info=_transcribe_with(model,path,segments_cb)
    return {'engine':dict(engine_info(),device=device,model=model_size),
            'language':info.language,'duration':round(info.duration,3),
            'segments':segments,'text':'\n'.join(s['text'] for s in segments if s['text'])}

class Transcripts:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS transcripts(
                id INTEGER PRIMARY KEY AUTOINCREMENT, media_id TEXT NOT NULL,
                revision INTEGER NOT NULL, text TEXT NOT NULL, segments TEXT NOT NULL,
                source TEXT NOT NULL, engine TEXT, job_id TEXT, created_at TEXT,
                UNIQUE(media_id,revision))''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def add(self,media_id,text,segments,source,engine=None,job_id=None):
        if not isinstance(text,str) or not text.strip(): raise ValueError('متن خالی قابل ذخیره نیست.')
        with self.connect() as c:
            row=c.execute('SELECT MAX(revision) FROM transcripts WHERE media_id=?',(media_id,)).fetchone()
            rev=(row[0] or 0)+1
            c.execute('INSERT INTO transcripts(media_id,revision,text,segments,source,engine,job_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
                      (media_id,rev,text.strip(),json.dumps(segments,ensure_ascii=False),source,
                       json.dumps(engine,ensure_ascii=False) if engine else None,job_id,datetime.now(timezone.utc).isoformat()))
        return self.get(media_id,rev)
    def list(self,media_id):
        with self.connect() as c:
            rows=c.execute('SELECT revision FROM transcripts WHERE media_id=? ORDER BY revision DESC',(media_id,)).fetchall()
        return [self.get(media_id,r[0]) for r in rows]
    def get(self,media_id,revision=None):
        with self.connect() as c:
            if revision is None:
                r=c.execute('SELECT * FROM transcripts WHERE media_id=? ORDER BY revision DESC LIMIT 1',(media_id,)).fetchone()
            else:
                r=c.execute('SELECT * FROM transcripts WHERE media_id=? AND revision=?',(media_id,revision)).fetchone()
        if not r: return None
        keys=('id','media_id','revision','text','segments','source','engine','job_id','created_at')
        d=dict(zip(keys,r))
        d['segments']=json.loads(d['segments'])
        d['engine']=json.loads(d['engine']) if d['engine'] else None
        return d

def transcribe_audio_handler(ctx):
    """Job handler: media_id -> versioned Persian transcript with timestamps."""
    mlib=ctx.services['media']; store=ctx.services['transcripts']
    m=mlib.get(ctx.payload.get('media_id'))
    if not m: raise ValueError('رسانه پیدا نشد.')
    if not Path(m['path']).exists(): raise ValueError('فایل اصلی روی دیسک پیدا نشد.')
    ctx.log(f"شروع تبدیل گفتار به متن برای {m['orig_name']}")
    ctx.progress(5)
    if not engine_available():
        raise DependencyMissing('faster-whisper نصب نیست؛ هیچ متن جعلی ساخته نمی‌شود.')
    def cb(pct): ctx.progress(pct)
    result=run_engine(m['path'],segments_cb=cb,model_size=ctx.payload.get('model_size','small'))
    t=store.add(m['id'],result['text'],result['segments'],'automatic',engine=result['engine'],job_id=ctx.id)
    ctx.log(f"پردازش کامل شد: {len(result['segments'])} قطعه، زبان {result['language']}")
    return {'transcript_id':t['id'],'media_id':m['id'],'revision':t['revision'],
            'segments':len(result['segments']),'language':result['language'],
            'duration':result['duration'],'engine':result['engine']}

TS_LINE=__import__('re').compile(r'^\s*((?P<h>\d{1,2}):)?(?P<m>[0-5]?\d):(?P<s>[0-5]\d)\s+(?P<t>.*)$')

def parse_timed_text(text):
    """Lines like '1:23 متن' or '01:02:03 متن' become segments; plain lines keep order."""
    segs=[]
    for line in (text or '').splitlines():
        m=TS_LINE.match(line)
        if m:
            start=int(m.group('h') or 0)*3600+int(m.group('m'))*60+int(m.group('s'))
            segs.append({'start':float(start),'end':None,'text':m.group('t').strip()})
        elif segs and line.strip():
            segs[-1]['text']+='\n'+line.strip()
        elif line.strip():
            segs.append({'start':None,'end':None,'text':line.strip()})
    for i,seg in enumerate(segs):
        if seg['start'] is None: seg['start']=0.0
        nxt=segs[i+1]['start'] if i+1<len(segs) else None
        seg['end']=nxt if nxt is not None else seg['start']+5.0
    return segs
