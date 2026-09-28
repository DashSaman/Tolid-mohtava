"""Persistent local job queue: Panel -> Job -> Worker -> Result.

Stdlib only. Jobs live in SQLite so a panel restart never clears history.
Running jobs found at startup are honestly marked failed (restart interruption),
queued jobs are re-dispatched. No fake success: engine absence is a real failure.
"""
import json, sqlite3, threading, uuid, traceback
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
from queue import Queue, Empty

STATES=('queued','running','waiting_approval','completed','failed','cancelled')
ACTIVE=('queued','running','waiting_approval')

def now(): return datetime.now(timezone.utc).isoformat()

class JobCancelled(Exception): pass

class DependencyMissing(Exception):
    """A required local engine (faster-whisper, FFmpeg, ...) is not available."""

class Ctx:
    """Handler view of a running job: logging, progress, cancel checks, services."""
    def __init__(self,mgr,jid,job):
        self.id=jid; self.payload=job['payload']; self._m=mgr; self.services=mgr.services
    def log(self,msg): self._m.log(self.id,msg)
    def progress(self,pct):
        try: pct=max(0,min(100,int(pct)))
        except (TypeError,ValueError): return
        self._m._update(self.id,progress=pct)
    def cancelled(self): return self._m.cancel_requested(self.id)

class JobManager:
    def __init__(self,path,handlers=None,workers=2,services=None):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.handlers=dict(handlers or {}); self.services=dict(services or {})
        self._q=Queue(); self._stop=threading.Event()
        self._cancels=set(); self._cancels_lock=threading.Lock()
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS jobs(
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
                status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
                logs TEXT NOT NULL DEFAULT '[]', created_at TEXT, started_at TEXT,
                finished_at TEXT, retry_count INTEGER NOT NULL DEFAULT 0,
                error TEXT, result TEXT, idempotency_key TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS jobs_key ON jobs(idempotency_key)')
        self._recover()
        self._threads=[]
        for i in range(max(0,workers)):
            t=threading.Thread(target=self._worker,daemon=True,name=f'job-worker-{i}')
            t.start(); self._threads.append(t)
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def _recover(self):
        with self.connect() as c:
            for (jid,) in c.execute("SELECT id FROM jobs WHERE status='running'").fetchall():
                c.execute("UPDATE jobs SET status='failed',error=?,finished_at=? WHERE id=?",
                          ('پنل در حین اجرای این کار بازراه‌اندازی شد؛ برای تلاش دوباره Retry بزنید.',now(),jid))
            queued=[r[0] for r in c.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created_at").fetchall()]
        for jid in queued: self._q.put(jid)
    def enqueue(self,kind,payload=None,idempotency_key=None):
        if kind not in self.handlers: raise ValueError('نوع کار پشتیبانی نمی‌شود.')
        if idempotency_key:
            with self.connect() as c:
                row=c.execute('SELECT id FROM jobs WHERE idempotency_key=? ORDER BY created_at DESC LIMIT 1',
                              (idempotency_key,)).fetchone()
            # strict dedupe: same key always maps to the same job, regardless of
            # status. A re-run requires explicit retry() or a different key.
            if row: return self.get(row[0])
        jid=uuid.uuid4().hex
        with self.connect() as c:
            c.execute('INSERT INTO jobs(id,kind,payload,status,logs,created_at,idempotency_key) VALUES(?,?,?,?,?,?,?)',
                      (jid,kind,json.dumps(payload or {},ensure_ascii=False),'queued','[]',now(),idempotency_key))
        self._q.put(jid)
        return self.get(jid)
    def _row(self,row):
        keys=('id','kind','payload','status','progress','logs','created_at','started_at','finished_at','retry_count','error','result','idempotency_key')
        j=dict(zip(keys,row))
        j['payload']=json.loads(j['payload']); j['logs']=json.loads(j['logs'])
        j['result']=json.loads(j['result']) if j['result'] else None
        return j
    def get(self,jid):
        with self.connect() as c:
            row=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
        return self._row(row) if row else None
    def list(self,status=None,limit=100):
        q='SELECT * FROM jobs'
        args=()
        if status:
            if status not in STATES: raise ValueError('وضعیت نامعتبر است.')
            q+=' WHERE status=?'; args=(status,)
        q+=' ORDER BY created_at DESC LIMIT ?'; args+=(limit,)
        with self.connect() as c:
            return [self._row(r) for r in c.execute(q,args).fetchall()]
    def _update(self,jid,**fields):
        sets=[]; args=[]
        for k,v in fields.items(): sets.append(f'{k}=?'); args.append(v)
        args.append(jid)
        with self.connect() as c:
            c.execute(f'UPDATE jobs SET {",".join(sets)} WHERE id=?',args)
    def log(self,jid,msg):
        job=self.get(jid)
        if not job: return
        lines=job['logs']
        lines.append({'time':now(),'message':str(msg)[:500]})
        if len(lines)>500: lines=lines[-500:]
        self._update(jid,logs=json.dumps(lines,ensure_ascii=False))
    def progress(self,jid,pct): self._update(jid,progress=max(0,min(100,int(pct))))
    def cancel(self,jid):
        job=self.get(jid)
        if not job: raise ValueError('کار پیدا نشد.')
        if job['status']=='queued':
            self._update(jid,status='cancelled',error='در صف لغو شد.',finished_at=now())
        elif job['status']=='running':
            with self._cancels_lock: self._cancels.add(jid)
            self.log(jid,'درخواست لغو ثبت شد؛ در نخستین نقطه امن اعمال می‌شود.')
        else: raise ValueError('این کار در حالت قابل لغو نیست.')
        return self.get(jid)
    def cancel_requested(self,jid):
        with self._cancels_lock: return jid in self._cancels
    def retry(self,jid):
        job=self.get(jid)
        if not job: raise ValueError('کار پیدا نشد.')
        if job['status'] not in ('failed','cancelled','completed'):
            raise ValueError('کار در حال اجرا یا صف قابل تلاش دوباره نیست.')
        with self._cancels_lock: self._cancels.discard(jid)
        self._update(jid,status='queued',error=None,finished_at=None,started_at=None,
                     retry_count=job['retry_count']+1)
        self._q.put(jid)
        return self.get(jid)
    def decide(self,jid,approved):
        job=self.get(jid)
        if not job: raise ValueError('کار پیدا نشد.')
        if job['status']!='waiting_approval': raise ValueError('این کار منتظر تأیید نیست.')
        if not approved:
            self._update(jid,status='cancelled',error='تأیید رد شد.',finished_at=now())
            return self.get(jid)
        job['payload']['approved']=True
        self._update(jid,status='queued',payload=json.dumps(job['payload'],ensure_ascii=False))
        self._q.put(jid)
        return self.get(jid)
    def _worker(self):
        while not self._stop.is_set():
            try: jid=self._q.get(timeout=0.5)
            except Empty: continue
            try:
                self._run(jid)
            except Exception:
                pass
            finally: self._q.task_done()
    def _run(self,jid):
        job=self.get(jid)
        if not job or job['status']!='queued': return
        if job['kind'] not in self.handlers:
            self._update(jid,status='failed',error='نوع کار پشتیبانی نمی‌شود.',finished_at=now()); return
        self._update(jid,status='running',started_at=now())
        ctx=Ctx(self,jid,job)
        try:
            result=self.handlers[job['kind']](ctx) or {}
            if self.cancel_requested(jid): raise JobCancelled()
            if result.get('waiting_approval'):
                self._update(jid,status='waiting_approval',result=json.dumps(result,ensure_ascii=False),finished_at=None)
            else:
                self._update(jid,status='completed',result=json.dumps(result,ensure_ascii=False),finished_at=now(),progress=100)
        except JobCancelled:
            self._update(jid,status='cancelled',error='به درخواست شما لغو شد.',finished_at=now())
        except DependencyMissing as e:
            self._update(jid,status='failed',error=f'BLOCKED_BY_DEPENDENCY: {e}',finished_at=now())
            self.log(jid,'وابستگی محلی موجود نیست؛ هیچ نتیجه جعلی ساخته نشد.')
        except Exception as e:
            self._update(jid,status='failed',error=(str(e) or e.__class__.__name__)[:1000],finished_at=now())
            self.log(jid,traceback.format_exc(limit=6))
        finally:
            with self._cancels_lock: self._cancels.discard(jid)
    def stop(self):
        self._stop.set()
        for t in self._threads:
            if t.is_alive(): t.join(timeout=3)
