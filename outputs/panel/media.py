"""Immutable media ingest: originals are never modified or auto-deleted.

Files live under data/media (gitignored). The database stores metadata and
the sha256 so any later copy/archive step can be verified against it.
"""
import hashlib, json, os, re, sqlite3, uuid
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

KINDS=('voice','screen','face','external_audio','broll','thumbnail')
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
            try: c.execute('ALTER TABLE media ADD COLUMN duration REAL')
            except sqlite3.OperationalError: pass
            c.execute('''CREATE TABLE IF NOT EXISTS assets(
                media_id TEXT PRIMARY KEY, state TEXT NOT NULL DEFAULT 'pending',
                label TEXT, updated_at TEXT)''')
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

        duration=None
        try:
            import avtools
            if avtools.ffprobe_path() and not (mime or '').startswith('image/'):
                duration=round(__import__('render').probe_duration(dest),3)
        except Exception: duration=None
        row=dict(id=mid,content_id=content_id,kind=kind,orig_name=name,path=str(dest),
                 size=size,sha256=h.hexdigest(),mime=mime or '',created_at=now(),duration=duration)
        with self.connect() as c:
            cols=','.join(row.keys()); qs=','.join('?'*len(row))
            c.execute(f'INSERT INTO media({cols}) VALUES({qs})',tuple(row.values()))
        return row
    def get(self,mid):
        with self.connect() as c:
            cur=c.execute('SELECT * FROM media WHERE id=?',(mid,))
            keys=[d[0] for d in cur.description]; r=cur.fetchone()
        row=dict(zip(keys,r)) if r else None
        if row: row['exists']=os.path.exists(row['path'])
        return row
    def list(self,content_id=None,kind=None):
        q='SELECT * FROM media'; conds=[]; args=[]
        if content_id is not None: conds.append('content_id=?'); args.append(content_id)
        if kind is not None:
            if kind not in KINDS: raise ValueError('نوع رسانه معتبر نیست.')
            conds.append('kind=?'); args.append(kind)
        if conds: q+=' WHERE '+' AND '.join(conds)
        q+=' ORDER BY created_at DESC'
        with self.connect() as c:
            cur=c.execute(q,args); keys=[d[0] for d in cur.description]
            out=[dict(zip(keys,r)) for r in cur.fetchall()]
        for r in out: r['exists']=os.path.exists(r['path'])
        return out
    def set_asset_state(self,media_id,state,label=None):
        if state not in ('pending','approved','rejected'): raise ValueError('وضعیت معتبر نیست.')
        if not self.get(media_id): raise ValueError('رسانه پیدا نشد.')
        with self.connect() as c:
            c.execute('INSERT INTO assets(media_id,state,label,updated_at) VALUES(?,?,?,?) '
                      'ON CONFLICT(media_id) DO UPDATE SET state=?,label=?,updated_at=?',
                      (media_id,state,label,now(),state,label,now()))
        return self.get_asset(media_id)
        # exists flag per row
    def get_asset(self,media_id):
        with self.connect() as c:
            cur=c.execute('SELECT * FROM assets WHERE media_id=?',(media_id,))
            keys=[d[0] for d in cur.description]; r=cur.fetchone()
        return dict(zip(keys,r)) if r else None
    def list_assets(self,state=None):
        q='SELECT a.media_id,a.state,a.label,a.updated_at,m.orig_name,m.mime,m.size FROM assets a JOIN media m ON m.id=a.media_id'
        args=()
        if state: q+=' WHERE a.state=?'; args=(state,)
        q+=' ORDER BY a.updated_at DESC'
        with self.connect() as c:
            cur=c.execute(q,args); keys=[d[0] for d in cur.description]
            return [dict(zip(keys,r)) for r in cur.fetchall()]
    def verify(self,mid):
        m=self.get(mid)
        if not m: raise ValueError('رسانه پیدا نشد.')
        h=hashlib.sha256()
        with open(m['path'],'rb') as f:
            for chunk in iter(lambda: f.read(1024*1024),b''): h.update(chunk)
        return h.hexdigest()==m['sha256']
