"""Notification center: real events recorded locally; Telegram is
credential-gated (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in environment).
No spam: meaningful events only, and every event is shown in the dashboard.
"""
import json, sqlite3, os, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

KIND_FA={'approval_needed':'نیاز به تأیید شما','job_failed':'کار ناموفق','render_done':'رندر کامل شد',
         'ai_done':'کار هوشمند کامل شد','storage_warning':'هشدار فضای ذخیره‌سازی','seo_critical':'مشکل بحرانی سئو'}

def now(): return datetime.now(timezone.utc).isoformat()

class Notifications:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS notifications(
                id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
                title TEXT NOT NULL, body TEXT, ref TEXT, read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT)''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def add(self,kind,title,body='',ref=None):
        with self.connect() as c:
            cur=c.execute('INSERT INTO notifications(kind,title,body,ref,read,created_at) VALUES(?,?,?,?,0,?)',
                          (kind,title[:200],body[:500],ref,now()))
            return cur.lastrowid
    def list(self,unread_only=False,limit=50):
        q='SELECT * FROM notifications'
        if unread_only: q+=' WHERE read=0'
        q+=' ORDER BY id DESC LIMIT ?'
        with self.connect() as c:
            cur=c.execute(q,(limit,)); keys=[d[0] for d in cur.description]
            rows=[dict(zip(keys,r)) for r in cur.fetchall()]
        for r in rows: r['read']=bool(r['read'])
        return rows
    def unread_count(self):
        with self.connect() as c:
            return c.execute('SELECT COUNT(*) FROM notifications WHERE read=0').fetchone()[0]
    def mark_read(self,nid=None):
        with self.connect() as c:
            if nid: c.execute('UPDATE notifications SET read=1 WHERE id=?',(nid,))
            else: c.execute('UPDATE notifications SET read=1')

def telegram_send(text):
    """Real Telegram send; honest credential gate. Returns dict result."""
    token=os.environ.get('TELEGRAM_BOT_TOKEN'); chat=os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        return {'ok':False,'blocked':'BLOCKED_BY_CREDENTIAL: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID در environment تنظیم نشده است.'}
    try:
        req=urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
            data=json.dumps({'chat_id':chat,'text':text[:3500]}).encode(),
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=20) as r:
            out=json.load(r)
        return {'ok':bool(out.get('ok')),'detail':('ارسال شد' if out.get('ok') else str(out.get('description'))[:200])}
    except Exception as e:
        return {'ok':False,'detail':str(e)[:200]}
