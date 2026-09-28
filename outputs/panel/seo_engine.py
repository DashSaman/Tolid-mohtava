"""Site-wide SEO engine for tehnet.ir / mytel.one.

A small stdlib crawler: sitemap + homepage crawl (bounded), per-page checks
(status, title, meta description, H1, canonical, robots, sitemap presence),
duplicate-title/description detection, sampled broken links. Every scan is a
historical row — previous scans are never overwritten.
"""
import json, re, sqlite3, subprocess, urllib.request, urllib.error
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import urlsplit, urljoin
from jobs import DependencyMissing

SITES={'tehnet.ir':'https://tehnet.ir','mytel.one':'https://mytel.one'}
UA='Mozilla/5.0 (content-factory SEO audit)'

def now(): return datetime.now(timezone.utc).isoformat()

class SEOStore:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS seo_scans(
                id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT NOT NULL,
                summary TEXT NOT NULL, pages TEXT NOT NULL, issues INTEGER NOT NULL,
                ok INTEGER NOT NULL, created_at TEXT)''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def add_scan(self,site,summary,pages,issues,ok):
        with self.connect() as c:
            c.execute('INSERT INTO seo_scans(site,summary,pages,issues,ok,created_at) VALUES(?,?,?,?,?,?)',
                      (site,json.dumps(summary,ensure_ascii=False),json.dumps(pages,ensure_ascii=False)[:400000],issues,ok,now()))
    def scans(self,site,limit=10):
        with self.connect() as c:
            cur=c.execute('SELECT id,site,summary,issues,ok,created_at FROM seo_scans WHERE site=? ORDER BY id DESC LIMIT ?',(site,limit))
            keys=[d[0] for d in cur.description]
            return [dict(zip(keys,r)) for r in cur.fetchall()]
    def scan_pages(self,scan_id):
        with self.connect() as c:
            cur=c.execute('SELECT pages FROM seo_scans WHERE id=?',(scan_id,))
            r=cur.fetchone()
        return json.loads(r[0]) if r else []

def _fetch(url,timeout=20):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.status, r.read(300000).decode('utf-8','replace')

def _meta(html,pattern):
    m=re.search(pattern,html,flags=re.I|re.S)
    return m.group(1).strip()[:300] if m else None

def check_page(url):
    """Fetch one page and run the on-page checks. Real network, real parsing."""
    import html as htmlmod
    res={'url':url}
    try:
        status,html=_fetch(url)
    except urllib.error.HTTPError as e:
        return {'url':url,'status':e.code,'error':'HTTP error'}
    except Exception as e:
        return {'url':url,'status':None,'error':str(e)[:120]}
    res['status']=status
    res['title']=(_meta(html,r'<title[^>]*>(.*?)</title>'))
    res['meta_description']=_meta(html,r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']')
    res['canonical']=_meta(html,r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']')
    res['h1_count']=len(re.findall(r'<h1[\s>]',html,re.I))
    res['has_schema']='application/ld+json' in html
    imgs=re.findall(r'<img[^>]*>',html,re.I)[:40]
    noalt=[i for i in imgs if not re.search(r'alt=["\'][^"\']+["\']',i,re.I)]
    res['images']=len(imgs); res['images_missing_alt']=len(noalt)
    links=re.findall(r'<a[^>]+href=["\'](.*?)["\']',html,re.I)
    internal=[]
    host=urlsplit(url).netloc
    for l in links:
        if l.startswith('#') or l.startswith('mailto:') or l.startswith('tel:'): continue
        full=urljoin(url,l)
        if urlsplit(full).netloc==host: internal.append(full.split('#')[0])
    res['internal_links']=len(set(internal))
    res['_sample_links']=sorted(set(internal))[:12]
    return res

def check_robots_and_sitemap(base):
    out={'robots':None,'sitemap':None,'sitemap_urls':0}
    try:
        st,body=_fetch(base+'/robots.txt',timeout=15)
        out['robots']='ok' if st==200 else f'http {st}'
        m=re.search(r'Sitemap:\s*(\S+)',body,re.I)
        if m: out['sitemap_url']=m.group(1)
    except Exception as e:
        out['robots']='missing/'+str(e)[:60]
    sm=out.get('sitemap_url') or base+'/sitemap.xml'
    try:
        st,body=_fetch(sm,timeout=20)
        if st==200 and ('<urlset' in body or '<sitemapindex' in body):
            out['sitemap']='ok'
            out['sitemap_urls']=len(re.findall(r'<loc>',body))
        else: out['sitemap']=f'http {st}'
    except Exception as e:
        out['sitemap']='missing/'+str(e)[:60]
    return out

def _check_links_broken(links,limit=8):
    broken=[]
    for u in links[:limit]:
        try:
            req=urllib.request.Request(u,headers={'User-Agent':UA},method='HEAD')
            with urllib.request.urlopen(req,timeout=12) as r:
                if r.status>=400: broken.append((u,r.status))
        except urllib.error.HTTPError as e:
            if e.code>=400: broken.append((u,e.code))
        except Exception:
            broken.append((u,'error'))
    return broken

def crawl_site(site,max_pages=25):
    base=SITES.get(site)
    if not base: raise ValueError('سایت پشتیبانی نمی‌شود.')
    infra=check_robots_and_sitemap(base)
    pages=[]; seen=set()
    queue=deque([base+'/'])
    if infra.get('sitemap_urls'):
        try:
            st,body=_fetch(infra.get('sitemap_url') or base+'/sitemap.xml',timeout=20)
            for loc in re.findall(r'<loc>\s*(.*?)\s*</loc>',body)[:max_pages]:
                if urlsplit(loc).netloc==site and loc not in seen:
                    queue.append(loc); seen.add(loc)
        except Exception: pass
    issues=0
    all_links=[]
    while queue and len(pages)<max_pages:
        u=queue.popleft()
        if u in seen and pages: continue
        seen.add(u)
        r=check_page(u)
        sampled=r.pop('_sample_links',[])
        all_links+=sampled
        for l in sampled:
            if len(queue)<max_pages and l not in seen: queue.append(l)
        pages.append(r)
    titles={}; descs={}
    for p in pages:
        if p.get('title'): titles.setdefault(p['title'].strip().lower(),[]).append(p['url'])
        if p.get('meta_description'): descs.setdefault(p['meta_description'].strip().lower(),[]).append(p['url'])
        if p.get('status')!=200: issues+=1
        if not p.get('title'): issues+=1
        if not p.get('meta_description'): issues+=1
        if p.get('h1_count',0)!=1: issues+=1
        if not p.get('canonical'): issues+=1
        if p.get('images_missing_alt'): issues+=1
    dup_titles=[{'title':t,'pages':u} for t,u in titles.items() if len(u)>1]
    dup_descs=[{'description':d[:80],'pages':u} for d,u in descs.items() if len(u)>1]
    issues+=len(dup_titles)+len(dup_descs)
    broken=_check_links_broken(sorted(set(all_links)))
    if broken: issues+=len(broken)
    summary={'site':site,'infra':infra,'pages_scanned':len(pages),
             'duplicate_titles':dup_titles,'duplicate_descriptions':dup_descs,
             'broken_links':[{'url':u,'status':s} for u,s in broken]}
    return summary,pages,issues

def seo_scan_handler(ctx):
    site=ctx.payload.get('site') or 'tehnet.ir'
    ctx.log(f"خزش {site}: sitemap و تا ۲۵ صفحه")
    summary,pages,issues=crawl_site(site)
    ctx.progress(60)
    store=ctx.services['seo']
    store.add_scan(site,summary,pages,issues,1 if issues==0 else 0)
    ctx.log(f"اسکن ثبت شد: {summary['pages_scanned']} صفحه، {issues} مشکل")
    return {'site':site,'issues':issues,'pages':summary['pages_scanned'],
            'infra':summary['infra'],'duplicate_titles':len(summary['duplicate_titles'])}
