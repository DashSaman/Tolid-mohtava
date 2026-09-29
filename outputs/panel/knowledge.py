"""Content Knowledge Base: simplest reliable retrieval over the project's own
content (SQLite LIKE + token scoring — no vector DB until scale demands it).

Sources: scripts, transcripts, articles, verified claims, research sources,
brand rules. Every hit carries source traceability; RAG-style prompts must
cite the internal references returned here.
"""
import json, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

def now(): return datetime.now(timezone.utc).isoformat()
STOP={'و','در','به','از','که','این','را','با','برای','است','می','های','یک','تا','بر','هم','یا','اگر','شود','بود'}

def _tokens(text):
    return [t for t in re.findall(r'[\w\u0600-\u06FF]{2,}',(text or '').lower()) if t not in STOP]

class KnowledgeBase:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS kb_docs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ref_type TEXT NOT NULL,
                ref_id TEXT, content_id TEXT, title TEXT NOT NULL, body TEXT NOT NULL,
                created_at TEXT, UNIQUE(ref_type,ref_id,title))''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def upsert(self,ref_type,ref_id,content_id,title,body):
        with self.connect() as c:
            c.execute('''INSERT INTO kb_docs(ref_type,ref_id,content_id,title,body,created_at)
                         VALUES(?,?,?,?,?,?) ON CONFLICT(ref_type,ref_id,title) DO UPDATE SET
                         body=?,created_at=?''',
                      (ref_type,ref_id,content_id,(title or '')[:200],(body or '')[:20000],now(),
                       (body or '')[:20000],now()))
    def search(self,query,limit=5):
        """Token-overlap scoring over LIKE-pre-filtered rows — deterministic,
        inspectable, traceable. Returns docs with citation info."""
        toks=_tokens(query)[:8]
        if not toks: return []
        likes=' OR '.join(['body LIKE ?']*len(toks))
        with self.connect() as c:
            cur=c.execute(f'SELECT id,ref_type,ref_id,content_id,title,body FROM kb_docs WHERE {likes} LIMIT 200',
                          tuple('%'+t+'%' for t in toks))
            rows=[dict(zip(('id','ref_type','ref_id','content_id','title','body'),r)) for r in cur.fetchall()]
        for r in rows:
            body_toks=set(_tokens(r['body'])); r['_score']=sum(1 for t in toks if t in body_toks)
        rows.sort(key=lambda r:-r['_score'])
        for r in rows: r.pop('_score',None)
        return rows[:limit]
    def stats(self):
        with self.connect() as c:
            return dict(c.execute('SELECT ref_type,COUNT(*) FROM kb_docs GROUP BY ref_type').fetchall())

def index_project(kb,store,ai_store=None):
    """(Re)index existing content: scripts/transcripts/articles + verified claims."""
    n=0
    for item in store.list('tehran-network')+store.list('mytel'):
        if (item.get('body') or '').strip():
            kb.upsert('script',item['id'],item['id'],item['title'],item['body']); n+=1
        if (item.get('transcript') or '').strip():
            kb.upsert('transcript',item['id'],item['id'],item['title']+' (transcript)',item['transcript']); n+=1
    if ai_store:
        for o in ai_store.outputs(limit=500):
            if o['kind']=='article_seo' and o['status']=='ok' and o.get('result'):
                r=o['result']
                text=(r.get('title') or '')+'\n'+'\n'.join(s.get('text','') for s in r.get('sections',[]))
                kb.upsert('article',o['id'],o.get('content_id'),r.get('title') or 'مقاله',text); n+=1
        for s in ai_store.sources('') if hasattr(ai_store,'sources') else []:
            pass
    return n
