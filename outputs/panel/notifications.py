"""Notification center: real events recorded locally; Telegram is
credential-gated (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in environment).
No spam: meaningful events only, and every event is shown in the dashboard.
"""
import json, sqlite3, os, time, urllib.request
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

def telegram_send(text,link=None,max_retries=2,disable_notification=False):
    """Real Telegram send (production): caption+link support, timeout, retry
    with backoff, idempotent per content-hash guard. Never sends without the
    user's approval flow (tests call with explicit test content only)."""
    import hashlib
    token=os.environ.get('TELEGRAM_BOT_TOKEN'); chat=os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        return {'ok':False,'blocked':'BLOCKED_BY_CREDENTIAL: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID در environment تنظیم نشده است.'}
    payload={'chat_id':chat,'text':(text+((chr(10)+link) if link else ''))[:3800],
             'parse_mode':'HTML','disable_notification':disable_notification}
    guard_name='tg-'+hashlib.sha256(payload['text'].encode()).hexdigest()[:16]+'.json'
    guard=Path(os.environ.get('TEHNET_PANEL_DB','outputs/panel/data/content.sqlite')).parent/'tg-sent'
    guard.mkdir(parents=True,exist_ok=True)
    gfile=guard/guard_name
    if gfile.exists(): return {'ok':True,'deduplicated':True,'detail':'قبلاً همین پیام ارسال شد (idempotent).'}
    last=None
    for attempt in range(max_retries+1):
        try:
            req=urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
                data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=20) as r:
                out=json.load(r)
            if out.get('ok'):
                try: gfile.write_text(json.dumps({'at':now(),'message_id':out['result']['message_id']}))
                except Exception: pass
                return {'ok':True,'detail':'ارسال شد'}
            last=out.get('description','')
            if 'retry after' in str(last).lower(): time.sleep(3)
        except Exception as e:
            last=str(e)
        if attempt<max_retries: time.sleep(1.5*(attempt+1))
    return {'ok':False,'detail':str(last)[:200]}
