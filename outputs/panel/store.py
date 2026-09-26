"""Local, versioned content ledger. No publishing or external connections."""
import json
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

BRANDS={'tehran-network','mytel'}
FIELDS=('title','body','transcript','sources','notes','platform','stage','due')
def now(): return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS content(id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, content_id TEXT, time TEXT, kind TEXT, payload TEXT)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=10)
        try:
            with c: yield c
        finally: c.close()
    def get(self,id):
        with self.connect() as c:
            row=c.execute('SELECT payload FROM content WHERE id=?',(id,)).fetchone()
        if not row: raise ValueError('محتوا پیدا نشد.')
        return json.loads(row[0])
    def list(self,brand):
        if brand not in BRANDS: raise ValueError('برند نامعتبر است.')
        with self.connect() as c:
            rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM content')]
        return sorted([r for r in rows if brand in r['brands']],key=lambda r:r['updated'],reverse=True)
    def history(self,id):
        self.get(id)
        with self.connect() as c:
            return [dict(time=t,kind=k,data=json.loads(p)) for t,k,p in c.execute('SELECT time,kind,payload FROM events WHERE content_id=? ORDER BY seq',(id,))]
    def event(self,c,item,kind):
        c.execute('INSERT INTO events(content_id,time,kind,payload) VALUES(?,?,?,?)',(item['id'],now(),kind,json.dumps(item,ensure_ascii=False)))
    def save(self,data):
        if not isinstance(data,dict): raise ValueError('اطلاعات محتوا معتبر نیست.')
        title=data.get('title','')
        brands=data.get('brands',[])
        if not isinstance(title,str) or not title.strip() or len(title)>200: raise ValueError('عنوان باید بین ۱ تا ۲۰۰ نویسه باشد.')
        if not isinstance(brands,list) or not brands or any(not isinstance(b,str) or b not in BRANDS for b in brands): raise ValueError('برند معتبر انتخاب کنید.')
        item={}
        for k in FIELDS:
            v=data.get(k,'')
            if not isinstance(v,str) or len(v)>200000: raise ValueError('اندازه یا نوع متن معتبر نیست.')
            item[k]=v
        item['title']=title.strip()
        item['brands']=sorted(set(brands))
        item['id']=data.get('id') or uuid.uuid4().hex
        if not isinstance(item['id'],str): raise ValueError('شناسه معتبر نیست.')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT payload FROM content WHERE id=?',(item['id'],)).fetchone()
            old=json.loads(old[0]) if old else None
            if data.get('id') and old is None: raise ValueError('محتوا پیدا نشد.')
            if old and data.get('revision')!=old['revision']: raise ValueError('نسخه تغییر کرده است؛ صفحه را تازه کنید.')
            item.update(revision=old['revision']+1 if old else 1,created=old['created'] if old else now(),updated=now(),script_status='pending',publish_status='pending')
            c.execute('INSERT OR REPLACE INTO content VALUES(?,?)',(item['id'],json.dumps(item,ensure_ascii=False)))
            self.event(c,item,'edited' if old else 'created')
        return item
    def decide(self,id,revision,gate,status):
        if gate not in ('script','publish') or status not in ('pending','approved','rejected','review'): raise ValueError('تصمیم معتبر نیست.')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT payload FROM content WHERE id=?',(id,)).fetchone()
            if not row: raise ValueError('محتوا پیدا نشد.')
            item=json.loads(row[0])
            if revision!=item['revision']: raise ValueError('تأیید نسخه قدیمی ممکن نیست؛ نسخه تازه را بررسی کنید.')
            if not item['body'].strip() and status=='approved': raise ValueError('ابتدا متن مورد تأیید را ثبت کنید.')
            key=gate+'_status'
            if item[key]==status: return item
            item[key]=status; item['updated']=now()
            c.execute('UPDATE content SET payload=? WHERE id=?',(json.dumps(item,ensure_ascii=False),id))
            self.event(c,item,gate+'_'+status)
        return item
    def export(self,brand):
        return {'schema':1,'brand':brand,'exported_at':now(),'items':[dict(item=x,history=self.history(x['id'])) for x in self.list(brand)]}
