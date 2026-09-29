"""Multi-track recording sync (face cam / screen / external audio) and
conservative audio enhancement.

Sync strategy (layered, per master requirements): envelope correlation via
numpy (ships with faster-whisper), clap/transient detection for confirmation,
and always a manual offset fallback. RAW files are never modified; offsets are
project metadata. Enhancement renders a NEW file through FFmpeg with a
conservative chain — natural speech must stay natural.
"""
import json, sqlite3, subprocess, uuid, wave, struct, math
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
import avtools
from jobs import DependencyMissing

def now(): return datetime.now(timezone.utc).isoformat()

ENVELOPE_HZ=100      # envelope resolution
SEARCH_SECONDS=12    # ± search window
CLAP_JUMP=6.0        # RMS jump factor that counts as a clap/transient

class SyncStore:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS sync_offsets(
                id INTEGER PRIMARY KEY AUTOINCREMENT, content_id TEXT NOT NULL,
                media_id TEXT NOT NULL, reference_media_id TEXT,
                offset_seconds REAL NOT NULL, method TEXT NOT NULL,
                confidence REAL NOT NULL, created_at TEXT,
                UNIQUE(media_id))''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def save(self,content_id,media_id,reference_media_id,offset,method,confidence):
        if abs(offset)>SEARCH_SECONDS+30: raise ValueError('افست خارج از محدودهٔ معقول است.')
        if not 0<=confidence<=1: raise ValueError('اطمینان باید بین ۰ و ۱ باشد.')
        with self.connect() as c:
            c.execute('''INSERT INTO sync_offsets(content_id,media_id,reference_media_id,offset_seconds,method,confidence,created_at)
                         VALUES(?,?,?,?,?,?,?) ON CONFLICT(media_id) DO UPDATE SET
                         reference_media_id=?,offset_seconds=?,method=?,confidence=?,created_at=?''',
                      (content_id,media_id,reference_media_id,offset,method,confidence,now(),
                       reference_media_id,offset,method,confidence,now()))
    def for_content(self,content_id):
        with self.connect() as c:
            cur=c.execute('SELECT * FROM sync_offsets WHERE content_id=? ORDER BY confidence DESC',(content_id,))
            keys=[d[0] for d in cur.description]
            return [dict(zip(keys,r)) for r in cur.fetchall()]
    def clear(self,media_id):
        with self.connect() as c:
            c.execute('DELETE FROM sync_offsets WHERE media_id=?',(media_id,))

def _pcm_mono(path,ar=8000):
    """Normalize ANY input (AAC/MP4/phone m4a/44.1k/stereo) to one common
    analysis format: mono s16le @ 8kHz with mild band-pass, before correlation.
    RAW files are never touched — this is a temp decode to memory/stdout."""
    ff=avtools.ffmpeg_path()
    if not ff: raise DependencyMissing(avtools.ffmpeg_missing())
    out=subprocess.run([ff,'-hide_banner','-i',str(path),'-ac','1','-ar',str(ar),
                        '-af','highpass=f=60,lowpass=f=3000,speechnorm=e=6.25:r=0.00001:l=1',
                        '-f','s16le','-'],
                       capture_output=True,timeout=1800)
    if out.returncode!=0 or len(out.stdout)<8000:
        raise ValueError('استخراج صوت برای همگام‌سازی ناموفق بود.')
    import array
    return array.array('h',out.stdout[:len(out.stdout)//2*2]), ar

def envelope(samples,ar,rate=ENVELOPE_HZ):
    w=max(1,ar//rate)   # window sized so envelope rate == `rate` Hz exactly
    n=len(samples)//w
    if n<10: raise ValueError('تراک صوتی برای همگام‌سازی خیلی کوتاه است.')
    out=[]
    for i in range(n):
        chunk=samples[i*w:(i+1)*w]
        rms=math.sqrt(sum(x*x for x in chunk)/w)
        out.append(rms)
    peak=max(out) or 1.0
    return [v/peak for v in out]

def find_claps(env,hz=ENVELOPE_HZ):
    """Indices of sharp transient jumps (clap-like)."""
    claps=[]
    for i in range(2,len(env)-1):
        prev=max(env[i-2],env[i-1],1e-6)
        if env[i]>prev*CLAP_JUMP and env[i]>0.25:
            claps.append(i)
    # collapse neighbors
    merged=[]
    for i in claps:
        if not merged or i-merged[-1]>hz//2: merged.append(i)
    return merged

def correlate(env_ref,env_off,hz=ENVELOPE_HZ):
    """Best offset (seconds, off relative to ref) within ±SEARCH_SECONDS."""
    import numpy as np
    a=np.asarray(env_ref,dtype='float32'); b=np.asarray(env_off,dtype='float32')
    a=a-a.mean(); b=b-b.mean()
    maxlag=hz*SEARCH_SECONDS
    best=(None,-2.0)
    la,lb=len(a),len(b)
    if la<20 or lb<20: return None,0.0
    denom=(math.sqrt(float((a*a).sum())*float((b*b).sum())) or 1.0)
    def corr_at(lag):
        """Windowed Pearson (normalized) — robust to per-track loudness."""
        n=min(la,lb)-abs(lag)
        if n<10: return 0.0
        if lag>=0: x=a[lag:lag+n]; y=b[:n]
        else: x=a[:n]; y=b[-lag:-lag+n]
        xm=float(x.mean()); ym=float(y.mean())
        x=x-xm; y=y-ym
        d=math.sqrt(float((x*x).sum())*float((y*y).sum()))
        return float((x*y).sum())/d if d>1e-9 else 0.0
    for lag in range(-maxlag,maxlag+1,hz//10):          # coarse 100ms→10ms step
        c=corr_at(lag)
        if c>best[1]: best=(lag,c)
    if best[0] is None: return None,0.0
    lag0=best[0]
    for lag in range(lag0-hz//10,lag0+hz//10+1):        # fine ±100ms at 10ms step
        c=corr_at(lag)
        if c>best[1]: best=(lag,c)
    lag,conf=best
    # positive offset = the second track is DELAYED relative to the reference
    return -lag/hz, max(0.0,min(1.0,conf))

def sync_pair(ref_path,off_path):
    """Returns (offset_seconds, confidence, method)."""
    sref,ar=_pcm_mono(ref_path)
    soff,_=_pcm_mono(off_path)
    env_ref=envelope(sref,ar); env_off=envelope(soff,ar)
    offset,conf=correlate(env_ref,env_off)
    if offset is None: return None,0.0,'failed'
    method='waveform'
    claps_r=find_claps(env_ref); claps_o=find_claps(env_off)
    if claps_r and claps_o:
        # do transients land at the aligned position in both tracks?
        target_r=int(offset*ENVELOPE_HZ)
        aligned=any(abs(cr-(co+target_r))<ENVELOPE_HZ//4 for cr in claps_r for co in claps_o)
        if aligned:
            method='clap+waveform'; conf=min(1.0,conf+0.25)
    return round(offset,3), round(conf,2), method

def sync_content_handler(ctx):
    """Job: sync all content media against the longest track."""
    from jobs import DependencyMissing
    if not avtools.ffmpeg_path(): raise DependencyMissing(avtools.ffmpeg_missing())
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    media=[m for m in services['media'].list(content_id) if m['kind']!='thumbnail']
    if len(media)<2: raise ValueError('برای همگام‌سازی حداقل دو تراک لازم است.')
    store=services['sync']
    ref=max(media,key=lambda m:m.get('duration') or 0)
    ctx.log(f"تراک مرجع: {ref['orig_name']}")
    results=[]
    others=[m for m in media if m['id']!=ref['id']]
    for i,m in enumerate(others):
        if ctx.cancelled(): raise JobCancelled()
        offset,conf,method=sync_pair(ref['path'],m['path'])
        if offset is None:
            results.append({'media':m['orig_name'],'status':'failed'})
            ctx.log(f"همگام‌سازی {m['orig_name']} ناموفق بود — افست دستی لازم است")
        else:
            store.save(content_id,m['id'],ref['id'],offset,method,conf)
            low=' · نیاز به بازبینی' if conf<0.6 else ''
            ctx.log(f"{m['orig_name']}: افست {offset:+.2f}s ({method}، اطمینان {int(conf*100)}٪){low}")
            results.append({'media':m['orig_name'],'offset':offset,'confidence':conf,'method':method})
        ctx.progress(int((i+1)/len(others)*100))
    return {'reference':ref['orig_name'],'tracks':results}

JSON_ENH=None
def enhance_audio_handler(ctx):
    """Conservative enhancement: new file, RAW untouched, chain is mild."""
    from jobs import DependencyMissing
    services=ctx.services
    if not avtools.ffmpeg_path(): raise DependencyMissing(avtools.ffmpeg_missing())
    m=services['media'].get(ctx.payload.get('media_id'))
    if not m: raise ValueError('رسانه پیدا نشد.')
    rd=services['renders']
    outdir=rd.root/m['id']; outdir.mkdir(parents=True,exist_ok=True)
    n=sum(1 for r in rd.list(m['id']) if r['kind']=='enhanced')
    out=outdir/f"ENHANCED_V{n+1}_{uuid.uuid4().hex[:6]}.wav"
    ff=avtools.ffmpeg_path()
    cmd=[ff,'-y','-hide_banner','-i',m['path'],'-ac','1',
         '-af','highpass=f=80,afftdn=nf=-25,acompressor=threshold=-18dB:ratio=2:attack=20:release=250,loudnorm=I=-16:TP=-1.5:LRA=11',
         '-ar','44100',str(out)]
    ctx.log('بهبود محافظه‌کارانه صوت (نویزگیر ملایم + نرمال‌سازی بلندی)')
    ctx.progress(30)
    proc=subprocess.run(cmd,capture_output=True,timeout=3600)
    if proc.returncode!=0 or not out.exists() or out.stat().st_size==0:
        out.unlink(missing_ok=True)
        raise RuntimeError('بهبود صوت ناموفق بود: '+proc.stderr.decode('utf-8','replace')[-300:])
    row=rd.add(m['id'],f'ENHANCED V{n+1}','enhanced',out,out.stat().st_size,0,
               m.get('duration') or 0,'ffmpeg afftdn+loudnorm',ctx.id)
    ctx.log('نسخهٔ بهبودیافته ساخته شد؛ فایل اصلی دست‌نخورده ماند.')
    return {'render_id':row['id'],'label':row['label']}

from jobs import JobCancelled
