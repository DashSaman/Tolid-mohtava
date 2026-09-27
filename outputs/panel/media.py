"""Immutable media ingest: originals are never modified or auto-deleted.

Files live under data/media (gitignored). The database stores metadata and
the sha256 so any later copy/archive step can be verified against it.
"""
import hashlib, json, re, sqlite3, uuid
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

KINDS=('voice','screen','face','external_audio','broll')
MAX_NAME=180

def now(): return datetime.now(timezone.utc).isoformat()

class MediaLibrary:
    def __init__(self,db_path,root):
        self.path=Path(db_path); self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS media(
                id TEXT PRIMARY KEY, content_id TEXT, kind TEXT NOT NULL,
                orig_name TEXT, path TEXT NOT NULL, size INTEGER NOT NULL,
                sha256 TEXT NOT NULL, mime TEXT, created_at TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS media_content ON media(content_id)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def ingest(self,reader,orig_name,kind,content_id=None,size_limit=None,mime=''):
        """reader: callable(chunk_size)->bytes until b''. Streams to disk."""
        if kind not in KINDS: raise ValueError('نوع رسانه معتبر نیست.')
        if content_id is not None:
            with self.connect() as c:
                if not c.execute('SELECT 1 FROM content WHERE id=?',(content_id,)).fetchone():
                    raise ValueError('محتوای مقصود پیدا نشد.')
        name=re.sub(r'[^\w.\-؟آ-ی ]','_',(orig_name or 'file').strip())[:MAX_NAME] or 'file'
        mid=uuid.uuid4().hex
        dest=self.root/f'{mid}_{name}'
        h=hashlib.sha256(); size=0
        with open(dest,'wb') as f:
            while True:
                chunk=reader(1024*1024)
                if not chunk: break
                size+=len(chunk)
                if size_limit is not None and size>size_limit:
                    f.close(); dest.unlink(missing_ok=True)
                    raise ValueError('حجم فایل از حد مجاز بیشتر است.')
                h.update(chunk); f.write(chunk)
        if size==0:
            dest.unlink(missing_ok=True); raise ValueError('فایل خالی است.')
        row=dict(id=mid,content_id=content_id,kind=kind,orig_name=name,path=str(dest),
                 size=size,sha256=h.hexdigest(),mime=mime or '',created_at=now())
        with self.connect() as c:
            c.execute('INSERT INTO media(id,content_id,kind,orig_name,path,size,sha256,mime,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                      tuple(row[k] for k in ('id','content_id','kind','orig_name','path','size','sha256','mime','created_at')))
        return row
    def _row(self,r):
        keys=('id','content_id','kind','orig_name','path','size','sha256','mime','created_at')
        return dict(zip(keys,r))
    def get(self,mid):
        with self.connect() as c:
            r=c.execute('SELECT * FROM media WHERE id=?',(mid,)).fetchone()
        return self._row(r) if r else None
    def list(self,content_id=None,kind=None):
        q='SELECT * FROM media'; conds=[]; args=[]
        if content_id is not None: conds.append('content_id=?'); args.append(content_id)
        if kind is not None:
            if kind not in KINDS: raise ValueError('نوع رسانه معتبر نیست.')
            conds.append('kind=?'); args.append(kind)
        if conds: q+=' WHERE '+' AND '.join(conds)
        q+=' ORDER BY created_at DESC'
        with self.connect() as c:
            return [self._row(r) for r in c.execute(q,args).fetchall()]
    def verify(self,mid):
        m=self.get(mid)
        if not m: raise ValueError('رسانه پیدا نشد.')
        h=hashlib.sha256()
        with open(m['path'],'rb') as f:
            for chunk in iter(lambda: f.read(1024*1024),b''): h.update(chunk)
        return h.hexdigest()==m['sha256']
