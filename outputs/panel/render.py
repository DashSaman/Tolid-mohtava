"""Preview and final rendering of active edit cuts. FFmpeg-based, NVENC when usable.

Non-destructive: renders always write a NEW file; originals untouched.
"""
import json, sqlite3, subprocess, uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
import avtools

def now(): return datetime.now(timezone.utc).isoformat()

def probe_duration(path):
    fp=avtools.ffprobe_path()
    if not fp: raise RuntimeError('ffprobe در دسترس نیست.')
    out=subprocess.run([fp,'-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],
                       capture_output=True,timeout=120)
    try: return float(out.stdout.decode().strip())
    except ValueError: raise RuntimeError('خواندن مدت رسانه ناموفق بود.')

def keep_ranges(cuts,duration):
    """Complement of merged cuts within [0,duration]."""
    keep=[]; cur=0.0
    for s,e in sorted(cuts):
        s=max(0,min(s,duration)); e=max(0,min(e,duration))
        if s>cur+0.01: keep.append((cur,s))
        cur=max(cur,e)
    if cur<duration-0.01: keep.append((cur,duration))
    return keep

def build_filter(keep,has_video=True):
    """trim/concat filter keeping only `keep` ranges."""
    parts=[]; vlabels=[]; alabels=[]
    for i,(s,e) in enumerate(keep):
        if has_video:
            parts.append(f'[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}]'); vlabels.append(f'[v{i}]')
        parts.append(f'[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}]'); alabels.append(f'[a{i}]')
    if has_video:
        parts.append(''.join(vlabels)+f'concat=n={len(keep)}:v=1:a=0[vout]')
        parts.append(''.join(alabels)+f'concat=n={len(keep)}:v=0:a=1[aout]')
    else:
        parts.append(''.join(alabels)+f'concat=n={len(keep)}:v=0:a=1[aout]')
    return ';'.join(parts)

def video_args(kind,nvenc):
    if kind=='final':
        if nvenc: return ['-c:v','h264_nvenc','-preset','p5','-rc','vbr','-cq','21','-b:v','0','-maxrate','12M','-bufsize','24M']
        return ['-c:v','libx264','-preset','medium','-crf','20']
    if nvenc: return ['-c:v','h264_nvenc','-preset','p1','-rc','vbr','-cq','30','-b:v','0']
    return ['-c:v','libx264','-preset','veryfast','-crf','28']

def build_cmd(src,dst,cuts,kind='preview',nvenc=False,has_video=True,progress=False):
    dur=probe_duration(src)
    keep=keep_ranges(cuts,dur)
    cmd=[avtools.ffmpeg_path(),'-y','-hide_banner','-nostats','-i',str(src)]
    if not keep: raise ValueError('همه بازه‌ها حذف شده‌اند؛ برش خروجی خالی می‌شود.')
    cmd+=['-filter_complex',build_filter(keep,has_video)]
    cmd+=['-map','[aout]','-c:a','aac','-b:a','160k']
    if has_video:
        cmd+=['-map','[vout]']+video_args(kind,nvenc)
        if kind=='final': cmd+=['-movflags','+faststart']
    else:
        cmd+=['-vn']
    if progress: cmd+=['-progress','pipe:1']
    cmd+=[str(dst)]
    return cmd,keep,dur

class Renders:
    def __init__(self,db_path,root):
        self.path=Path(db_path); self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS renders(
                id TEXT PRIMARY KEY, media_id TEXT NOT NULL, label TEXT NOT NULL,
                kind TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL,
                cuts INTEGER NOT NULL, duration REAL, encoder TEXT,
                job_id TEXT, created_at TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS renders_media ON renders(media_id)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def _row(self,r):
        keys=('id','media_id','label','kind','path','size','cuts','duration','encoder','job_id','created_at')
        return dict(zip(keys,r))
    def add(self,media_id,label,kind,path,size,cuts,duration,encoder,job_id=None):
        row=dict(id=uuid.uuid4().hex,media_id=media_id,label=label,kind=kind,path=str(path),
                 size=size,cuts=cuts,duration=duration,encoder=encoder,job_id=job_id,created_at=now())
        with self.connect() as c:
            c.execute('INSERT INTO renders VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                      tuple(row[k] for k in ('id','media_id','label','kind','path','size','cuts','duration','encoder','job_id','created_at')))
        return row
    def list(self,media_id=None):
        with self.connect() as c:
            if media_id is None:
                cur=c.execute('SELECT * FROM renders ORDER BY created_at DESC')
            else:
                cur=c.execute('SELECT * FROM renders WHERE media_id=? ORDER BY created_at',(media_id,))
            keys=[d[0] for d in cur.description]
            return [dict(zip(keys,r)) for r in cur.fetchall()]
    def media_names(self):
        with self.connect() as c:
            return dict(c.execute('SELECT id,orig_name FROM media').fetchall())
    def get(self,rid):
        with self.connect() as c:
            r=c.execute('SELECT * FROM renders WHERE id=?',(rid,)).fetchone()
        return self._row(r) if r else None
    def next_label(self,media_id,kind):
        rows=self.list(media_id)
        if kind=='final':
            n=sum(1 for r in rows if r['kind']=='final')
            return 'FINAL' if n==0 else f'FINAL V{n+1}'
        if kind=='short':
            n=sum(1 for r in rows if r['kind']=='short')
            return f'SHORT V{n+1}'
        n=sum(1 for r in rows if r['kind']=='preview')
        return f'EDIT V{n+1}'

def render_cut_handler(ctx):
    """Job handler: media_id + kind -> rendered new version with active cuts."""
    from jobs import DependencyMissing, JobCancelled
    mlib=ctx.services['media']; dec=ctx.services['decisions']; rd=ctx.services['renders']
    if not avtools.ffmpeg_path(): raise DependencyMissing(avtools.ffmpeg_missing())
    m=mlib.get(ctx.payload.get('media_id'))
    if not m: raise ValueError('رسانه پیدا نشد.')
    kind=ctx.payload.get('kind','preview')
    if kind not in ('preview','final'): raise ValueError('نوع رندر معتبر نیست.')
    if kind=='final' and not ctx.payload.get('approved'):
        return {'waiting_approval':True,'question':'رندر نهایی اجرا شود؟ خروجی نسخه FINAL با برش‌های فعال ساخته می‌شود.'}
    cuts=dec.timeline(m['id'])
    has_video=not (m['orig_name'].lower().endswith(('.wav','.mp3','.m4a','.ogg','.flac')) or (m['mime'] or '').startswith('audio/'))
    nvenc=has_video and avtools.nvenc_available()
    label=rd.next_label(m['id'],kind)
    outdir=rd.root/m['id']; outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/f"{label.replace(' ','_')}_{uuid.uuid4().hex[:8]}.mp4"
    ctx.log(f"رندر {label} با {len(cuts)} برش{' · NVENC' if nvenc else ''}")
    cmd,keep,dur=build_cmd(m['path'],out,cuts,kind,nvenc,has_video,progress=True)
    ctx.progress(3)
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    encoder=f"{'h264_nvenc' if (has_video and nvenc) else ('libx264' if has_video else 'aac')}"
    for line in proc.stdout:
        text=line.decode('ascii','replace').strip()
        if text.startswith('out_time_ms=') or text.startswith('out_time_us='):
            try:
                done=float(text.split('=',1)[1])/1_000_000
                if dur>0: ctx.progress(3+done/dur*95)
            except ValueError: pass
        if ctx.cancelled():
            proc.kill(); raise JobCancelled()
    code=proc.wait()
    if code!=0:
        err=proc.stderr.read().decode('utf-8','replace')[-500:]
        out.unlink(missing_ok=True)
        raise RuntimeError('رندر ناموفق بود: '+err)
    if not out.exists() or out.stat().st_size==0: raise RuntimeError('خروجی رندر ساخته نشد.')
    total=sum(e-s for s,e in keep)
    row=rd.add(m['id'],label,kind,out,out.stat().st_size,len(cuts),round(total,3),encoder,ctx.id)
    ctx.log(f"خروجی آماده شد: {label} ({row['size']//1024} کیلوبایت، {total:.1f} ثانیه)")
    return {'render_id':row['id'],'label':label,'kind':kind,'cuts':len(cuts),
            'duration':round(total,3),'size':row['size'],'encoder':encoder}
