"""Local authentication (optional but recommended before any remote access)
and archive-to-external-disk workflow with checksum verification and explicit
approval before any deletion. RAW files are never silently removed.
"""
import hashlib, hmac, json, os, re, secrets, shutil, sqlite3, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

def now(): return datetime.now(timezone.utc).isoformat()

def hash_password(password,salt=None):
    salt=salt or secrets.token_hex(16)
    dk=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),120000)
    return salt+':'+dk.hex()

def verify_password(password,stored):
    try:
        salt,digest=stored.split(':')
        return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),120000).hex(),digest)
    except Exception:
        return False

class Auth:
    """Env-based single admin: ADMIN_USER + ADMIN_PASSWORD (plain, read at
    startup) or ADMIN_PASSWORD_HASH (salted hex format from hash_password).
    If not configured, panel stays loopback-open exactly as before."""
    def __init__(self):
        self.user=os.environ.get('ADMIN_USER')
        self.hash=os.environ.get('ADMIN_PASSWORD_HASH')
        self.password=os.environ.get('ADMIN_PASSWORD')
        if self.user and self.password and not self.hash:
            self.hash=hash_password(self.password); self.password=None
        self.sessions={}   # token -> expiry timestamp
        self.attempts=[]   # (ip, timestamp) for login rate limiting
    @property
    def enabled(self): return bool(self.user and self.hash)
    def login(self,username,password,ip='local'):
        if not self.enabled: return {'ok':True,'token':None,'note':'auth disabled'}
        nowt=time.time()
        self.attempts=[a for a in self.attempts if nowt-a[1]<300]
        if sum(1 for a in self.attempts if a[0]==ip)>=8:
            return {'ok':False,'error':'تلاش‌های زیاد؛ ۵ دقیقه صبر کنید.'}
        self.attempts.append((ip,nowt))
        if username!=self.user or not verify_password(password,self.hash):
            return {'ok':False,'error':'نام کاربری یا رمز درست نیست.'}
        token=secrets.token_urlsafe(32)
        self.sessions[token]=nowt+12*3600
        return {'ok':True,'token':token}
    def check(self,token):
        if not self.enabled: return True
        exp=self.sessions.get(token)
        if not exp or exp<time.time():
            self.sessions.pop(token,None)
            return False
        return True
    def logout(self,token): self.sessions.pop(token,None)

class ArchiveStore:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS archive_jobs(
                id TEXT PRIMARY KEY, content_id TEXT, media_id TEXT,
                state TEXT NOT NULL, passport_path TEXT, checksum_ok INTEGER,
                created_at TEXT, updated_at TEXT)''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def set(self,aid,content_id,media_id,state,passport_path=None,checksum_ok=None):
        with self.connect() as c:
            c.execute('''INSERT INTO archive_jobs VALUES(?,?,?,?,?,?,?,?)
                         ON CONFLICT(id) DO UPDATE SET state=?,passport_path=?,checksum_ok=?,updated_at=?''',
                      (aid,content_id,media_id,state,passport_path,checksum_ok,now(),now(),
                       state,passport_path,checksum_ok,now()))
    def list(self):
        with self.connect() as c:
            cur=c.execute('SELECT * FROM archive_jobs ORDER BY updated_at DESC LIMIT 100')
            keys=[d[0] for d in cur.description]
            return [dict(zip(keys,r)) for r in cur.fetchall()]

def archive_copy_handler(ctx):
    """Step 1 (approval-gated): COPY project media to passport + verify checksums.
    Never deletes anything."""
    from jobs import DependencyMissing
    services=ctx.services
    if not ctx.payload.get('approved'):
        return {'waiting_approval':True,'question':'کپی پروژه روی دیسک آرشیو اجرا شود؟ (هیچ فایلی حذف نمی‌شود)'}
    store=services['store']; media=services['media']; arch=services['archive']
    passport=ctx.payload.get('passport_path')
    if not passport or not Path(passport).exists():
        raise DependencyMissing('دیسک آرشیو (My Passport) در دسترس نیست.')
    content_id=ctx.payload.get('content_id')
    item=store.get(content_id)
    if not item: raise ValueError('محتوا پیدا نشد.')
    items=media.list(content_id)
    if not items: raise ValueError('این پروژه رسانه‌ای برای آرشیو ندارد.')
    safe=re.sub(r'[^\w\-]','_',item['title'])[:60]
    dest=Path(passport)/'content-factory'/f"{content_id}_{safe}"
    dest.mkdir(parents=True,exist_ok=True)
    import hashlib as hl
    copied=[]
    for i,m in enumerate(items):
        if ctx.cancelled(): raise JobCancelled()
        src=Path(m['path'])
        if not src.exists():
            arch.set(uuid.uuid4().hex,content_id,m['id'],'source_missing'); continue
        dst=dest/src.name
        shutil.copy2(src,dst)
        h1=hl.sha256(src.read_bytes()).hexdigest()
        h2=hl.sha256(dst.read_bytes()).hexdigest()
        ok=h1==h2 and h1==m['sha256']
        arch.set(uuid.uuid4().hex,content_id,m['id'],'copied_verified' if ok else 'checksum_mismatch',str(dst),1 if ok else 0)
        copied.append({'media':m['orig_name'],'verified':ok})
        ctx.progress(int((i+1)/len(items)*100))
        ctx.log(f"{m['orig_name']} کپی و checksum تأیید شد" if ok else f"{m['orig_name']} کپی شد ولی checksum مطابقت ندارد!")
    if any(not c['verified'] for c in copied): raise RuntimeError('بعضی فایل‌ها checksum مطابقت ندارند؛ حذفی انجام نشد.')
    return {'destination':str(dest),'files':len(copied),'next_step':'حذف نسخهٔ SSD فقط با تأیید جداگانهٔ شما انجام می‌شود.'}

from jobs import JobCancelled
