"""Conservative non-destructive automatic editing.

Raw media is never touched. Every suggestion is an EditDecision row
(start, end, reason, confidence, origin, state). Clear defects (long
silence, standalone filler) auto-activate; anything ambiguous is only
proposed for review. Restoring a cut is a state change, not a file edit.
"""
import json, re, sqlite3, subprocess, uuid, difflib
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
import avtools

STATES=('active','restored','proposed','dismissed')
ORIGINS=('automatic','manual')
FILLERS=('اِ','اِم','آه','اُه','امم','اهه','خبِ')
SIL_RANGE=(0.8,10.0)     # auto-cut window for silences (seconds)
PAUSE_RANGE=(0.45,0.8)   # borderline -> proposed
FILLER_CONF=0.85
SIL_CONF=0.9
PAUSE_CONF=0.5
REPEAT_CONF=0.6

def now(): return datetime.now(timezone.utc).isoformat()

def fa_time(sec):
    sec=int(round(sec)); h,rem=divmod(sec,3600); m,s=divmod(rem,60)
    core=f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'
    return core.translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹'))

REASON_FA={
 'silence':'سکوت حذف شد',
 'long_pause':'سکوت طولانی حذف شد',
 'pause':'مکث مرزی؛ نیاز به بررسی',
 'filler':'حرف اضافه («اِ»/«اِم») حذف شد',
 'repeat':'تکرار جمله؛ نسخه دوم کامل‌تر است',
 'manual':'حذف دستی توسط شما',
}

class EditDecisions:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS edit_decisions(
                id TEXT PRIMARY KEY, media_id TEXT NOT NULL, transcript_revision INTEGER,
                start REAL NOT NULL, end REAL NOT NULL, reason_code TEXT NOT NULL,
                reason TEXT NOT NULL, confidence REAL NOT NULL, origin TEXT NOT NULL,
                state TEXT NOT NULL, created_at TEXT, decided_at TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS ed_media ON edit_decisions(media_id)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def _row(self,r):
        keys=('id','media_id','transcript_revision','start','end','reason_code','reason','confidence','origin','state','created_at','decided_at')
        return dict(zip(keys,r))
    def add(self,media_id,start,end,reason_code,confidence,origin,state,transcript_revision=None,reason=None):
        if start<0 or end<=start: raise ValueError('بازه زمانی معتبر نیست.')
        if origin not in ORIGINS or state not in STATES: raise ValueError('مقادیر تصمیم معتبر نیست.')
        row=dict(id=uuid.uuid4().hex,media_id=media_id,transcript_revision=transcript_revision,
                 start=round(start,3),end=round(end,3),reason_code=reason_code,
                 reason=reason or REASON_FA.get(reason_code,reason_code),confidence=confidence,
                 origin=origin,state=state,created_at=now(),decided_at=None)
        with self.connect() as c:
            c.execute('INSERT INTO edit_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                      tuple(row[k] for k in ('id','media_id','transcript_revision','start','end','reason_code','reason','confidence','origin','state','created_at','decided_at')))
        return row
    def list(self,media_id,state=None):
        q='SELECT * FROM edit_decisions WHERE media_id=?'; args=[media_id]
        if state:
            if state not in STATES: raise ValueError('وضعیت معتبر نیست.')
            q+=' AND state=?'; args.append(state)
        q+=' ORDER BY start'
        with self.connect() as c:
            return [self._row(r) for r in c.execute(q,args).fetchall()]
    def get(self,did):
        with self.connect() as c:
            r=c.execute('SELECT * FROM edit_decisions WHERE id=?',(did,)).fetchone()
        return self._row(r) if r else None
    def set_state(self,did,state):
        if state not in STATES: raise ValueError('وضعیت معتبر نیست.')
        d=self.get(did)
        if not d: raise ValueError('تصمیم پیدا نشد.')
        if state==d['state']: return d
        with self.connect() as c:
            c.execute('UPDATE edit_decisions SET state=?,decided_at=? WHERE id=?',(state,now(),did))
        return self.get(did)
    def user_had_verdict(self,media_id,start,end,reason_code):
        """Respect earlier restore/dismiss when re-analysing the same spot."""
        with self.connect() as c:
            r=c.execute('''SELECT state FROM edit_decisions WHERE media_id=? AND reason_code=?
                           AND ABS(start-?)<0.05 AND ABS(end-?)<0.05 AND state IN ('restored','dismissed')
                           ORDER BY created_at DESC LIMIT 1''',(media_id,reason_code,start,end)).fetchone()
        return r[0] if r else None
    def drop_active_auto(self,media_id):
        """Re-analysis replaces still-unreviewed automatic decisions only."""
        with self.connect() as c:
            c.execute('''DELETE FROM edit_decisions WHERE media_id=? AND origin='automatic'
                         AND state IN ('active','proposed')''',(media_id,))
    def timeline(self,media_id):
        """Merged active cuts in seconds — the render contract."""
        cuts=sorted([(d['start'],d['end']) for d in self.list(media_id,'active')],key=lambda x:x[0])
        merged=[]
        for s,e in cuts:
            if merged and s<=merged[-1][1]+0.01: merged[-1][1]=max(merged[-1][1],e)
            else: merged.append([s,e])
        return [(s,e) for s,e in merged]

def scan_silences(path,noise='-35dB',min_d=0.45):
    """FFmpeg silencedetect -> [(start,end,duration)]. Empty list if no ffmpeg."""
    ff=avtools.ffmpeg_path()
    if not ff: return None
    try:
        proc=subprocess.run([ff,'-hide_banner','-i',str(path),'-af',
                             f'silencedetect=noise={noise}:d={min_d}','-f','null','-'],
                            capture_output=True,timeout=1800)
    except Exception:
        return None
    err=proc.stderr.decode('utf-8','replace')
    out=[]
    start=None
    for line in err.splitlines():
        m=re.search(r'silence_start:\s*([0-9.]+)',line)
        if m: start=float(m.group(1)); continue
        m=re.search(r'silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)',line)
        if m and start is not None:
            out.append((start,float(m.group(1)),float(m.group(2)))); start=None
    return out

def detect_fillers_and_repeats(segments):
    """Transcript-based suggestions. Returns (filler_ranges, repeat_ranges)."""
    fillers=[]; repeats=[]
    norm=lambda t:re.sub(r'[\s‌.,!?؟،؛:«»\-]+','',t or '')
    for seg in segments:
        text=(seg.get('text') or '').strip()
        if text in FILLERS or re.fullmatch(r'(ا|اِ|اُ)ه?م{1,2}|آ+ه*',text):
            fillers.append((seg['start'],seg['end']))
    for a,b in zip(segments,segments[1:]):
        ta,tb=norm(a.get('text')),norm(b.get('text'))
        if len(ta)>6 and len(tb)>6 and difflib.SequenceMatcher(None,ta,tb).ratio()>=0.8:
            repeats.append((b['start'],b['end']))
    return fillers,repeats

def analyze(media,segments,transcript_revision,decisions):
    """Create decisions for one media. Returns summary dict."""
    decisions.drop_active_auto(media['id'])
    made=[]; silence_scan='skipped'
    sil=scan_silences(media['path'])
    if sil is not None:
        silence_scan='ffmpeg'
        for s,e,d in sil:
            if d>=SIL_RANGE[0]:
                if decisions.user_had_verdict(media['id'],s,e,'long_pause') is None:
                    made.append(decisions.add(media['id'],s,e,'long_pause',SIL_CONF,'automatic','active',transcript_revision))
            elif PAUSE_RANGE[0]<=d<PAUSE_RANGE[1]:
                prior=decisions.user_had_verdict(media['id'],s,e,'pause')
                if prior is None:
                    made.append(decisions.add(media['id'],s,e,'pause',PAUSE_CONF,'automatic','proposed',transcript_revision))
    else:
        silence_scan='unavailable'
    fillers,repeats=detect_fillers_and_repeats(segments)
    for s,e in fillers:
        prior=decisions.user_had_verdict(media['id'],s,e,'filler')
        if prior is None:
            made.append(decisions.add(media['id'],s,e,'filler',FILLER_CONF,'automatic','active',transcript_revision))
    for s,e in repeats:
        prior=decisions.user_had_verdict(media['id'],s,e,'repeat')
        if prior is None:
            made.append(decisions.add(media['id'],s,e,'repeat',REPEAT_CONF,'automatic','proposed',transcript_revision))
    return {'media_id':media['id'],'created':len(made),'silence_scan':silence_scan,
            'transcript_revision':transcript_revision}

def report_lines(decisions,media_id):
    """Persian review report. States: active/restored/proposed/dismissed."""
    label={'active':'حذف شد','restored':'بازگردانده شد','proposed':'نیاز به بررسی','dismissed':'نگه داشته شد'}
    lines=[]
    for d in sorted(decisions.list(media_id),key=lambda x:x['start']):
        lines.append({'start':d['start'],'end':d['end'],'span':f"{fa_time(d['start'])}–{fa_time(d['end'])}",
                      'reason':d['reason'],'state':d['state'],'state_fa':label[d['state']],
                      'confidence':d['confidence'],'origin':d['origin'],'id':d['id']})
    return lines

def edit_detect_handler(ctx):
    """Job handler: media_id -> conservative decisions from transcript + audio."""
    mlib=ctx.services['media']; ts=ctx.services['transcripts']; decisions=ctx.services['decisions']
    m=mlib.get(ctx.payload.get('media_id'))
    if not m: raise ValueError('رسانه پیدا نشد.')
    t=ts.get(m['id'])
    segments=t['segments'] if t else []
    ctx.log(f"تحلیل تدوین برای {m['orig_name']}؛ {len(segments)} قطعه متن، بررسی سکوت با FFmpeg")
    summary=analyze(m,segments,t['revision'] if t else None,decisions)
    ctx.log(f"{'سکوت‌یاب FFmpeg' if summary['silence_scan']=='ffmpeg' else 'سکوت‌یاب در دسترس نبود'}؛ {summary['created']} تصمیم جدید")
    return summary
