"""Whisper engine configuration + real benchmarking on this machine.

Model choice persists in the DB (settings table). Benchmarks run real
transcription of a given audio file per model and record device, timing and
rough word-overlap against a reference text — no guessed numbers.
"""
import json, re, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

WHISPER_MODELS=('small','medium','large-v3')
DEFAULT_MODEL='small'

def now(): return datetime.now(timezone.utc).isoformat()

class WhisperSettings:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS whisper_benchmarks(
                id INTEGER PRIMARY KEY AUTOINCREMENT, model TEXT NOT NULL,
                device TEXT, audio_seconds REAL, load_seconds REAL, transcribe_seconds REAL,
                rtf REAL, rough_overlap INTEGER, sample_name TEXT, created_at TEXT)''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def get(self,key,default=None):
        with self.connect() as c:
            r=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return r[0] if r else default
    def set(self,key,value):
        with self.connect() as c:
            c.execute('''INSERT INTO settings(key,value,updated_at) VALUES(?,?,?)
                         ON CONFLICT(key) DO UPDATE SET value=?,updated_at=?''',
                      (key,str(value),now(),str(value),now()))
    def whisper_model(self):
        m=self.get('whisper_model',DEFAULT_MODEL)
        return m if m in WHISPER_MODELS else DEFAULT_MODEL
    def set_whisper_model(self,model):
        if model not in WHISPER_MODELS: raise ValueError('مدل معتبر نیست.')
        self.set('whisper_model',model)
        return model
    def add_benchmark(self,model,device,audio_seconds,load_seconds,transcribe_seconds,rough_overlap,sample_name):
        rtf=(transcribe_seconds/audio_seconds) if audio_seconds else None
        with self.connect() as c:
            c.execute('''INSERT INTO whisper_benchmarks(model,device,audio_seconds,load_seconds,
                         transcribe_seconds,rtf,rough_overlap,sample_name,created_at) VALUES(?,?,?,?,?,?,?,?,?)''',
                      (model,device,audio_seconds,load_seconds,transcribe_seconds,rtf,rough_overlap,sample_name,now()))
    def benchmarks(self,limit=12):
        with self.connect() as c:
            cur=c.execute('SELECT * FROM whisper_benchmarks ORDER BY id DESC LIMIT ?',(limit,))
            keys=[d[0] for d in cur.description]
            return [dict(zip(keys,r)) for r in cur.fetchall()]

def rough_overlap(reference,text):
    """Word-set overlap % — a rough but real accuracy signal for benchmarks."""
    norm=lambda t:[w for w in re.sub(r'[^\wآ-ی ]',' ',(t or '')).split() if w]
    a=set(norm(reference)); b=set(norm(text))
    return int(round(100*len(a&b)/max(1,len(a))))

def run_benchmark(audio_path,reference_text,model):
    """Real transcription with one model. Returns measured record."""
    import transcribe
    from faster_whisper import WhisperModel
    import avtools
    from render import probe_duration
    device=transcribe.detect_device()
    if device=='cuda': transcribe._ensure_cuda_dlls()
    compute='float16' if device=='cuda' else 'int8'
    t0=time.time()
    try:
        wm=WhisperModel(model,device=device,compute_type=compute)
    except Exception:
        if device=='cuda':
            device='cpu'; compute='int8'
            wm=WhisperModel(model,device='cpu',compute_type=compute)
        else: raise
    load=time.time()-t0
    audio_seconds=probe_duration(audio_path) if avtools.ffprobe_path() else None
    t0=time.time()
    segs,info=wm.transcribe(str(audio_path),language='fa',vad_filter=True)
    text=' '.join(s.text.strip() for s in segs)
    tr=time.time()-t0
    return {'model':model,'device':device,'audio_seconds':round(audio_seconds,2) if audio_seconds else None,
            'load_seconds':round(load,1),'transcribe_seconds':round(tr,1),
            'rtf':round(tr/audio_seconds,2) if audio_seconds else None,
            'rough_overlap':rough_overlap(reference_text,text),'sample':Path(audio_path).name,
            'text_preview':text[:200]}

def benchmark_handler(ctx):
    """Job: benchmark one or all models against a Persian sample + reference."""
    services=ctx.services
    ws=services['whisper_settings']
    audio=ctx.payload.get('audio_path'); ref=ctx.payload.get('reference_text') or ''
    models=ctx.payload.get('models') or [ws.whisper_model()]
    if not audio or not Path(audio).exists(): raise ValueError('فایل صوتی بنچمارک پیدا نشد.')
    results=[]
    for i,m in enumerate(models):
        if m not in WHISPER_MODELS: continue
        ctx.log(f"بنچمارک مدل {m} روی صدای فارسی واقعی")
        r=run_benchmark(audio,ref,m)
        ws.add_benchmark(r['model'],r['device'],r['audio_seconds'],r['load_seconds'],
                         r['transcribe_seconds'],r['rough_overlap'],r['sample'])
        results.append(r)
        ctx.progress(int((i+1)/len(models)*100))
        ctx.log(f"{m}: {r['transcribe_seconds']}s روی {r['device']} · هم‌پوشانی ~{r['rough_overlap']}٪")
    best=sorted([r for r in results if r['device']=='cuda'] or results,
                key=lambda r:(-r['rough_overlap'],r['transcribe_seconds']))[0]
    return {'results':results,'recommended':best['model'],
            'reason':f"بهترین توازن دقت/سرعت روی {best['device']}"}
