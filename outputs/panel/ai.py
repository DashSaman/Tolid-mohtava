"""AI provider layer: multiple OpenAI-compatible providers with task routing.

Credentials are NEVER stored in the database — only the NAME of the
environment variable holding the key. Providers that fail health checks are
reported honestly; chat() raises DependencyMissing when nothing is reachable.
"""
import json, re, sqlite3, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from jobs import DependencyMissing

TASKS=('research','verification','script','social','seo','analysis','hooks','thumbnail')
TASK_FA={'research':'تحقیق','verification':'بررسی فنی','script':'سناریو','social':'محتوای شبکه‌ها',
         'seo':'سئو','analysis':'تحلیل عملکرد','hooks':'هوک','thumbnail':'عنوان و کاور'}
DEFAULT_PROVIDERS=[
 {'name':'lmstudio','base_url':'http://127.0.0.1:1234/v1','model':'','api_key_env':'','tasks':list(TASKS)},
 {'name':'ollama','base_url':'http://127.0.0.1:11434/v1','model':'','api_key_env':'','tasks':[]},
 {'name':'remote-openai','base_url':'','model':'','api_key_env':'OPENAI_API_KEY','tasks':[]},
]

def now(): return datetime.now(timezone.utc).isoformat()

class AIStore:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS ai_providers(
                name TEXT PRIMARY KEY, base_url TEXT NOT NULL, model TEXT,
                api_key_env TEXT, tasks TEXT NOT NULL DEFAULT '[]',
                enabled INTEGER NOT NULL DEFAULT 1, last_health TEXT, last_health_detail TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS ai_outputs(
                id TEXT PRIMARY KEY, content_id TEXT, kind TEXT NOT NULL,
                status TEXT NOT NULL, payload TEXT, result TEXT, raw TEXT,
                provider TEXT, model TEXT, job_id TEXT, created_at TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS research_sources(
                id INTEGER PRIMARY KEY AUTOINCREMENT, content_id TEXT, output_id TEXT,
                claim TEXT, url TEXT, status TEXT NOT NULL, note TEXT, checked_at TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS ao_content ON ai_outputs(content_id)')
            for p in DEFAULT_PROVIDERS:
                if not c.execute('SELECT 1 FROM ai_providers WHERE name=?',(p['name'],)).fetchone():
                    c.execute('INSERT INTO ai_providers(name,base_url,model,api_key_env,tasks,enabled) VALUES(?,?,?,?,?,1)',
                              (p['name'],p['base_url'],p['model'],p['api_key_env'],json.dumps(p['tasks'])))
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def providers(self,enabled_only=False):
        with self.connect() as c:
            rows=c.execute('SELECT * FROM ai_providers'+(' WHERE enabled=1' if enabled_only else '')+' ORDER BY name').fetchall()
        keys=('name','base_url','model','api_key_env','tasks','enabled','last_health','last_health_detail')
        out=[dict(zip(keys,r)) for r in rows]
        for p in out:
            p['tasks']=json.loads(p['tasks'] or '[]')
            p['enabled']=bool(p['enabled'])
        return out
    def get_provider(self,name):
        return next((p for p in self.providers() if p['name']==name),None)
    def save_provider(self,name,base_url,model,api_key_env,tasks,enabled=True):
        if not name or not isinstance(name,str): raise ValueError('نام provider الزامی است.')
        if api_key_env and not re.fullmatch(r'[A-Z0-9_]+',api_key_env): raise ValueError('نام متغیر محیطی نامعتبر است.')
        tasks_json=json.dumps(sorted(set(t for t in (tasks or []) if t in TASKS)))
        with self.connect() as c:
            c.execute('''INSERT INTO ai_providers(name,base_url,model,api_key_env,tasks,enabled)
                         VALUES(?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET
                         base_url=?,model=?,api_key_env=?,tasks=?,enabled=?''',
                      (name,base_url,model,api_key_env,tasks_json,1 if enabled else 0,
                       base_url,model,api_key_env,tasks_json,1 if enabled else 0))
        return self.get_provider(name)
    def set_health(self,name,ok,detail):
        with self.connect() as c:
            c.execute('UPDATE ai_providers SET last_health=?,last_health_detail=? WHERE name=?',
                      (now(),('ok: '+detail) if ok else ('fail: '+detail),name))
    def provider_for_task(self,task):
        """Explicit task mapping via enabled providers' task lists; fallback: any enabled."""
        for p in self.providers(enabled_only=True):
            if task in p['tasks']: return p
        return next((p for p in self.providers(enabled_only=True)),None)
    def save_output(self,oid,content_id,kind,status,payload,result,raw,provider,model,job_id):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO ai_outputs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                      (oid,content_id,kind,status,json.dumps(payload or {},ensure_ascii=False),
                       json.dumps(result,ensure_ascii=False) if result is not None else None,
                       (raw or '')[:60000],provider,model,job_id,now()))
    def outputs(self,content_id=None,kind=None,limit=60):
        q='SELECT * FROM ai_outputs'; conds=[]; args=[]
        if content_id: conds.append('content_id=?'); args.append(content_id)
        if kind: conds.append('kind=?'); args.append(kind)
        if conds: q+=' WHERE '+' AND '.join(conds)
        q+=' ORDER BY created_at DESC LIMIT ?'; args.append(limit)
        with self.connect() as c:
            cur=c.execute(q,args); keys=[d[0] for d in cur.description]
            rows=[dict(zip(keys,r)) for r in cur.fetchall()]
        for r in rows:
            r['payload']=json.loads(r['payload'] or '{}')
            r['result']=json.loads(r['result']) if r['result'] else None
        return rows
    def get_output(self,oid):
        return next((o for o in self.outputs(limit=500) if o['id']==oid),None)
    def add_source(self,content_id,output_id,claim,url,status,note=''):
        with self.connect() as c:
            cur=c.execute('''INSERT INTO research_sources(content_id,output_id,claim,url,status,note,checked_at)
                             VALUES(?,?,?,?,?,?,?)''',(content_id,output_id,claim[:500],url,status,note[:300],now()))
            return cur.lastrowid
    def sources(self,content_id):
        with self.connect() as c:
            cur=c.execute('SELECT * FROM research_sources WHERE content_id=? ORDER BY id DESC',(content_id,))
            keys=[d[0] for d in cur.description]
            return [dict(zip(keys,r)) for r in cur.fetchall()]

def _request(url,payload,timeout,api_key):
    headers={'Content-Type':'application/json'}
    if api_key: headers['Authorization']='Bearer '+api_key
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.load(r)

def api_key_for(provider):
    import os
    if not provider.get('api_key_env'): return None
    key=os.environ.get(provider['api_key_env'])
    if not key:
        raise DependencyMissing(f"متغیر محیطی {provider['api_key_env']} تنظیم نشده؛ provider آماده است ولی Credential لازم دارد (BLOCKED_BY_CREDENTIAL).")
    return key

def provider_health(store,name,timeout=6):
    p=store.get_provider(name)
    if not p: raise ValueError('پرووایدر پیدا نشد.')
    if not p['base_url']:
        store.set_health(name,False,'نشانی پایه تنظیم نشده'); return {'ok':False,'detail':'بدون نشانی'}
    key=None
    if p.get('api_key_env'):
        import os
        if not os.environ.get(p['api_key_env']):
            store.set_health(name,False,f"نیازمند {p['api_key_env']}")
            return {'ok':False,'detail':'BLOCKED_BY_CREDENTIAL: '+p['api_key_env']}
        key=os.environ[p['api_key_env']]
    try:
        req=urllib.request.Request(p['base_url'].rstrip('/')+'/models',headers={'Authorization':'Bearer '+key} if key else {})
        with urllib.request.urlopen(req,timeout=timeout) as r:
            data=json.load(r)
        models=[m.get('id') for m in data.get('data',[])][:10]
        store.set_health(name,True,(', '.join(models) or 'پاسخ داد'))
        return {'ok':True,'detail':', '.join(models) if models else 'پاسخ داد','models':models}
    except Exception as e:
        detail=str(e)[:200]
        store.set_health(name,False,detail)
        return {'ok':False,'detail':detail}

def chat(store,task,messages,max_tokens=900,temperature=0.6,timeout=600,provider_name=None):
    """One completion via the provider mapped to `task`. Honest failure if none."""
    p=store.get_provider(provider_name) if provider_name else store.provider_for_task(task)
    if not p: raise DependencyMissing('هیچ پرووایدر AI فعالی یافت نشد؛ در تنظیمات، یک provider سالم ثبت کنید.')
    if not p['base_url']:
        raise DependencyMissing(f"پرووایدر {p['name']} نشانی ندارد (BLOCKED_BY_CREDENTIAL/CONFIG).")
    key=api_key_for(p)
    model=p['model'] or None
    payload={'messages':messages,'max_tokens':max_tokens,'temperature':temperature}
    if model: payload['model']=model
    try:
        out=_request(p['base_url'].rstrip('/')+'/chat/completions',payload,timeout,key)
    except urllib.error.HTTPError as e:
        detail=e.read().decode('utf-8','replace')[:160]
        hint='مدل بارگذاری نشده یا درخواست نامعتبر است' if e.code in (400,404) else ('مهلت پاسخ سرویس هوش مصنوعی تمام شد' if e.code==504 else 'خطای سرویس هوش مصنوعی')
        raise DependencyMissing(f"سرویس هوش مصنوعی ({p['name']}) پاسخ داد: {e.code} — {hint}. جزئیات فنی در لاگ.")
    except TimeoutError:
        raise DependencyMissing('مهلت پاسخ سرویس هوش مصنوعی تمام شد (timeout). جزئیات فنی در لاگ.')
    except (ConnectionRefusedError,ConnectionResetError,OSError) as e:
        raise DependencyMissing(f'سرویس هوش مصنوعی ({p["name"]}) در دسترس نیست — LM Studio/پرووایدر خاموش است؟ (BLOCKED_BY_DEPENDENCY)')
    content=(out.get('choices') or [{}])[0].get('message',{}).get('content','')
    return {'content':content,'provider':p['name'],'model':out.get('model') or model or ''}

def _balanced_json(t):
    """Largest balanced {...} or [...] block (string/escape aware)."""
    for opener,closer in (('{','}'),('[',']')):
        start=t.find(opener)
        while start!=-1:
            depth=0; in_str=False; esc=False
            for i in range(start,len(t)):
                ch=t[i]
                if in_str:
                    if esc: esc=False
                    elif ch=='\\': esc=True
                    elif ch=='"': in_str=False
                    continue
                if ch=='"': in_str=True
                elif ch==opener: depth+=1
                elif ch==closer:
                    depth-=1
                    if depth==0:
                        cand=t[start:i+1]
                        try: return json.loads(cand)
                        except Exception: break
            start=t.find(opener,start+1)
    return None

def _close_opens(frag):
    """Append the exact closers (stack order) for unclosed openers."""
    pair={'{':'}','[':']'}
    stack=[]; in_str=False; esc=False
    for ch in frag:
        if in_str:
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch=='"': in_str=False
            continue
        if ch=='"': in_str=True
        elif ch in pair: stack.append(ch)
        elif ch in pair.values():
            if stack: stack.pop()
    return frag+''.join(pair[c] for c in reversed(stack))

def _repair_json(t):
    """Common small-model JSON defects, fixed conservatively."""
    x=re.sub(r'<think>.*?</think>','',t,flags=re.S)
    x=x.replace('\u201c','"').replace('\u201d','"').replace('\u2018',"'").replace('\u2019',"'")
    x=re.sub(r',\s*([}\]])',r'\1',x)              # trailing commas
    s=re.search(r'[{[]',x)
    if s:
        start=s.start()
        e=x.rfind('}')
        e2=x.rfind(']')
        end=max(e,e2)
        frag=x[start:end+1] if end>=start else x[start:]
        try: return json.loads(frag)
        except Exception: pass
        try: return json.loads(_close_opens(frag))
        except Exception: pass
    return None

def parse_markdown_kv(text):
    """Small models sometimes answer with '**Key:** value' lines — an honest,
    non-fabricating fallback that maps them to a dict. Arrays via ' - ' bullets."""
    if not text or ('**' not in text and ':' not in text): return None
    out={}
    lines=text.replace('\u201c','"').replace('\u201d','"').splitlines()
    cur_key=None
    for ln in lines:
        m=re.match(r'\s*\*{0,2}([^*:\n]{1,40})\*{0,2}\s*[:：]\s*(.*)$',ln)
        if m and m.group(2).strip()!='' or (m and m.group(1).strip()):
            key=re.sub(r'[^\w\u0600-\u06FF ]','_',m.group(1).strip().strip('*').strip()).strip('_').lower().replace(' ','_')
            val=m.group(2).strip().lstrip('*').strip()
            if not key or len(key)>45: continue
            cur_key=key
            if val:
                out[key]=val
            continue
        b=re.match(r'\s*[-*•]\s+(.*)$',ln)
        if b and cur_key:
            if isinstance(out.get(cur_key),list): out[cur_key].append(b.group(1).strip())
            elif cur_key in out: out[cur_key]=[out[cur_key],b.group(1).strip()]
            else: out[cur_key]=[b.group(1).strip()]
            continue
        if cur_key and ln.strip() and cur_key in out and isinstance(out[cur_key],str) and len(ln.strip())>60:
            out[cur_key]+=' '+ln.strip()
    return out or None

def extract_json(text):
    """Layered extraction: direct → fences → balanced → repaired → markdown-KV.
    Only reorganizes what the model actually wrote; never invents fields."""
    if not text: return None
    t=re.sub(r'<think>.*?</think>','',text,flags=re.S)
    candidates=[]
    m=re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```',t,flags=re.S)
    if m: candidates.append(m.group(1))
    s=t.find('{'); e=t.rfind('}')
    if s>=0 and e>s: candidates.append(t[s:e+1])
    for cand in candidates:
        try: return json.loads(cand)
        except Exception: pass
    r=_repair_json(t)
    if r is not None: return r
    b=_balanced_json(t)
    if b is not None: return b
    return parse_markdown_kv(t)

def validate_schema(data,required=None,list_fields=None,min_list=1):
    """Return list of problems (empty list = valid). Honest, no coercion."""
    problems=[]
    if not isinstance(data,dict):
        problems.append('خروجی شیء JSON نیست')
        return problems
    for k in (required or []):
        v=data.get(k)
        if v is None or (isinstance(v,str) and not v.strip()):
            problems.append('فیلد '+k+' خالی/غایب است')
    for k in (list_fields or []):
        v=data.get(k)
        if not isinstance(v,list) or len(v)<min_list:
            problems.append('فیلد '+k+' باید فهرستی با حداقل '+str(min_list)+' مورد باشد')
        elif not all(isinstance(x,dict) for x in v):
            problems.append('اعضای '+k+' باید شیء باشند')
    return problems


STATUS_KIND_FA={'research':'تحقیق','verification':'بررسی فنی','script':'سناریوی کامل','hooks':'هوک‌ها',
 'title_packages':'بسته‌های عنوان/کاور','social':'نسخهٔ شبکه‌ها','article_seo':'مقاله و سئو',
 'pinned_comment':'کامنت پین','content_matrix':'ماتریس محتوا','niche_research':'تحقیق نیچ',
 'post_score':'امتیازدهی پست','pipeline':'خط تولید کامل','intent':'درک موضوع'}
