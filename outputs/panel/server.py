from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json, mimetypes, os, secrets, socket, uuid, sqlite3, subprocess
from store import Store
from registry import skill_registry
from jobs import JobManager
from media import MediaLibrary, KINDS as MEDIA_KINDS
from transcribe import Transcripts
from editing import EditDecisions, report_lines
from render import Renders
from triggers import on_publish_approved
from transcribe import parse_timed_text
from shorts import shorts_candidates, render_short_handler
from system import health_payload, gpu_probe, drives, dir_size
from publishing import status as publishing_status, SITES as PUBLISH_SITES
from ai import AIStore, provider_health, TASKS as AI_TASKS, TASK_FA
from skill_router import classification_table, STAGE_SKILLS
from notifications import Notifications, telegram_send, KIND_FA
from whisper_config import WhisperSettings, benchmark_handler, WHISPER_MODELS
from sync import SyncStore, sync_content_handler, enhance_audio_handler
from seo_engine import SEOStore, seo_scan_handler, SITES as SEO_SITES
from ops import Auth, ArchiveStore, archive_copy_handler, hash_password
from analytics import (AnalyticsStore, adapter_status, health_check as adapter_health,
    analytics_sync_handler, optimize_content_handler, recommend_slot, detect_anomalies, PLATFORMS, PLATFORM_FA)
from intelligence import weekly_plan_handler, seo_proposals_handler, shorts_v2_handler
from integrations import all_optional_integrations, KeywordStore, ga4_fetch, screaming_frog_status, ruflo_status, normalize_sf_export
from providers import OAuthStore, OAUTH_PROVIDERS, oauth_start_url, oauth_callback, oauth_status, gemini_image_handler, gsc_search_analytics
from analytics import gsc_ingest_handler
import urllib.parse as uparse
from knowledge import KnowledgeBase, index_project
from content_intel import check_topic, refresh_candidates, optimize_content
from handlers import build_handlers
import handlers as HandlersMod

ROOT=Path(__file__).resolve().parent
PORT=int(os.environ.get('TEHNET_PANEL_PORT','8766'))
DB=Store(os.environ.get('TEHNET_PANEL_DB',str(ROOT/'data/content.sqlite')))
DATA=Path(DB.path).parent
MEDIA=MediaLibrary(DB.path,DATA/'media')
TRANSCRIPTS=Transcripts(DB.path)
DECISIONS=EditDecisions(DB.path)
RENDERS=Renders(DB.path,DATA/'renders')
AISTORE=AIStore(DB.path)
WSSET=WhisperSettings(DB.path)
SYNCSTORE=SyncStore(DB.path)
SEOSTORE=SEOStore(DB.path)
ARCHIVE=ArchiveStore(DB.path)
ANALYTICS=AnalyticsStore(DB.path)
KWSTORE=KeywordStore(DB.path)
OAUTH=OAuthStore(DB.path)
services_oauth={'oauth':OAUTH}
KB=KnowledgeBase(DB.path)
AUTH=Auth()
NOTIF=Notifications(DB.path)
POLICY_TEXT=(ROOT.parent/'content-policy.fa.md').read_text(encoding='utf-8')
JM=JobManager(DB.path,handlers=build_handlers()|{
  'whisper_benchmark':benchmark_handler,'sync_content':sync_content_handler,
  'enhance_audio':enhance_audio_handler,'seo_scan':seo_scan_handler,'archive_copy':archive_copy_handler,
  'analytics_sync':analytics_sync_handler,'optimize_content':optimize_content_handler,
  'weekly_plan':weekly_plan_handler,'seo_proposals':seo_proposals_handler,'shorts_v2':shorts_v2_handler},workers=2,
              services={'media':MEDIA,'transcripts':TRANSCRIPTS,'decisions':DECISIONS,'renders':RENDERS,
                        'store':DB,'dryrun_root':str(DATA/'dryrun'),
                        'ai':AISTORE,'policy':POLICY_TEXT,
                        'whisper_settings':WSSET,'sync':SYNCSTORE,'seo':SEOSTORE,'archive':ARCHIVE,
                        'analytics':ANALYTICS,'keywords':KWSTORE,'kb':KB})
MAX_UPLOAD=20*1024*1024*1024
TOKEN=secrets.token_urlsafe(32)
def brand_default(): return 'tehran-network'


def audio_rms_stats(path):
    """Decode via ffmpeg to s16le; compute RMS/peak/duration. Real silence check."""
    import struct, math
    import avtools as _av
    ff=_av.ffmpeg_path()
    if not ff: return {'error':'FFmpeg موجود نیست'}
    out=subprocess.run([ff,'-hide_banner','-i',str(path),'-ac','1','-ar','16000','-f','s16le','-'],
                       capture_output=True,timeout=300)
    b=out.stdout
    if len(b)<3200: return {'valid':False,'reason':'دادهٔ صوتی کوتاه‌تر از حد است','bytes':len(b)}
    n=len(b)//2
    take=min(n,800000)
    vals=struct.unpack('<%dh'%take,b[:take*2])
    peak=max(abs(v) for v in vals) if vals else 0
    rms=math.sqrt(sum(v*v for v in vals)/len(vals)) if vals else 0
    dur=n/16000.0
    silent=(rms<60 and peak<400)
    return {'valid':(not silent) and dur>=0.8,'duration':round(dur,2),'rms':int(rms),'peak':peak,
            'reason':('سکوت مؤثر — صدایی تشخیص داده نشد' if silent else ('کوتاه‌تر از ۰.۸ ثانیه' if dur<0.8 else ''))}

def validate_audio(media_id,media_lib=None):
    lib=media_lib or MEDIA
    m=lib.get(media_id)
    if not m: raise ValueError('رسانه پیدا نشد.')
    p=Path(m['path'])
    if not p.exists() or p.stat().st_size==0:
        return {'status':'INVALID_AUDIO','reason':'فایل صوتی خالی یا ناموجود است'}
    st=audio_rms_stats(p)
    if st.get('error'): return {'status':'UNKNOWN','reason':st['error']}
    if not st.get('valid'):
        return {'status':'INVALID_AUDIO','reason':st.get('reason') or 'صدای قابل استفاده نیست',
                'duration':st.get('duration'),'rms':st.get('rms'),'peak':st.get('peak')}
    return {'status':'OK','duration':st['duration'],'rms':st['rms'],'peak':st['peak']}

def delete_media_row(mid,lib,ts,dec,rd):
    """Shared safe recording delete: related rows + file (path-verified)."""
    m=lib.get(mid)
    if not m: raise ValueError('رسانه پیدا نشد.')
    path=Path(m['path']).resolve()
    root=(Path(lib.path).parent/'media').resolve()
    if root not in path.parents: raise ValueError('مسیر فایل خارج از فضای امن است.')
    import sqlite3 as sq
    with sq.connect(lib.path) as c:
        for tbl in ('edit_decisions','transcripts','renders','sync_offsets','assets'):
            try: c.execute(f'DELETE FROM {tbl} WHERE media_id=?',(mid,))
            except Exception: pass
        c.execute('DELETE FROM media WHERE id=?',(mid,))
    try: path.unlink()
    except OSError: pass

def project_dependencies(pid,jm):
    """Count and clean related rows; cancel active jobs; collect verified media paths."""
    import sqlite3 as sq
    counts={}; paths=[]
    with sq.connect(DB.path) as c:
        rows=c.execute("SELECT id,path FROM media WHERE content_id=?",(pid,)).fetchall()
        paths=[r[1] for r in rows]
        counts['media']=len(rows)
        mids=[r[0] for r in rows] or ['-']
        qmarks=','.join('?'*len(mids))
        for tbl,key in (('transcripts','media_id'),('edit_decisions','media_id'),
                        ('renders','media_id'),('sync_offsets','media_id')):
            try: counts[tbl]=c.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {key} IN ({qmarks})",mids).fetchone()[0]
            except Exception: counts[tbl]=0
        try: counts['ai_outputs']=c.execute("SELECT COUNT(*) FROM ai_outputs WHERE content_id=?",(pid,)).fetchone()[0]
        except Exception: counts['ai_outputs']=0
    for j in jm.list(limit=300):
        if (j.get('payload') or {}).get('content_id')==pid and j['status'] in ('queued','running','waiting_approval'):
            try: jm.cancel(j['id'])
            except Exception: pass
    return {'counts':counts,'paths':paths}

def delete_project_files(deps,db):
    """Delete only files under verified media/renders roots; then orphan rows."""
    mroot=(Path(db.path).parent/'media').resolve()
    rroot=(Path(db.path).parent/'renders').resolve()
    for path in deps.get('paths',[]):
        try:
            p=Path(path).resolve()
            if mroot in p.parents: p.unlink()
        except OSError: pass
    with sqlite3.connect(db.path) as c:
        rp=[r[0] for r in c.execute("SELECT path FROM renders WHERE media_id NOT IN (SELECT id FROM media)").fetchall()]
        for path in rp:
            try:
                p=Path(path).resolve()
                if rroot in p.parents: p.unlink()
            except OSError: pass
        for tbl in ('transcripts','edit_decisions','renders','sync_offsets','assets'):
            try: c.execute(f"DELETE FROM {tbl} WHERE media_id NOT IN (SELECT id FROM media)")
            except Exception: pass
        try: c.execute("DELETE FROM ai_outputs WHERE content_id NOT IN (SELECT id FROM content)")
        except Exception: pass
        c.commit()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def respond(self,obj,status=200):
        self.send(json.dumps(obj,ensure_ascii=False).encode(),'application/json; charset=utf-8',status)
    def send(self,data,mime,status=200):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers(); self.wfile.write(data)
    def valid_host(self):
        # Unified Host whitelist (superset of both branches; still the DNS-rebinding defense):
        # loopback on ANY port (host publish 18767 -> container 8766; direct browser),
        # container service name, Tailscale .ts.net names, and tailnet addresses
        # (CGNAT 100.64.0.0/10 for the sidecar path, fd7a:115c:a1e0::/48 for its IPv6).
        import ipaddress
        h=(self.headers.get('Host') or '').strip()
        if h.startswith('[') and ']' in h: host=h.split(']')[0][1:]   # [v6]:port
        else: host=h.split(':')[0].strip('[]')
        if h in (f'127.0.0.1:{PORT}',f'localhost:{PORT}',f'[::1]:{PORT}',f'tolid-web:{PORT}'): return True
        if host in ('127.0.0.1','localhost','::1','[::1]','tolid-web'): return True
        if host.endswith('.ts.net'): return True
        try:
            a=ipaddress.ip_address(host)
            return a in ipaddress.ip_network('100.64.0.0/10') or a in ipaddress.ip_network('fd7a:115c:a1e0::/48')
        except ValueError: return False
    def stream_file(self,path,size,mime):
        rng=self.headers.get('Range')
        start,end=0,size-1
        if rng and rng.startswith('bytes='):
            part=rng[6:].split(',')[0].split('-')
            if part[0]: start=int(part[0])
            if len(part)>1 and part[1]: end=int(part[1])
            start=max(0,min(start,size-1)); end=max(start,min(end,size-1))
        with open(path,'rb') as f:
            f.seek(start); data=f.read(end-start+1)
        self.send_response(206 if rng else 200)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Accept-Ranges','bytes')
        if rng: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.end_headers(); self.wfile.write(data)
    def serve_media(self,q):
        m=MEDIA.get(q.get('id',[''])[0])
        if not m or not Path(m['path']).exists(): return self.respond({'error':'رسانه پیدا نشد.'},404)
        mime=m['mime'] or (mimetypes.guess_type(m['orig_name'])[0] or 'application/octet-stream')
        return self.stream_file(m['path'],m['size'],mime)
    def do_GET(self):
        if not self.valid_host(): return self.respond({'error':'میزبان مجاز نیست.'},403)
        url=urlsplit(self.path); q=parse_qs(url.query)
        try:
            if url.path=='/api/session': return self.respond({'token':TOKEN,'app':'tehnet-content-panel','auth_required':AUTH.enabled})
            if url.path=='/api/skills': return self.respond(skill_registry())
            if url.path=='/api/media': return self.respond(MEDIA.list(q.get('content_id',[None])[0],q.get('kind',[None])[0]))
            if url.path=='/api/assets': return self.respond(MEDIA.list_assets(q.get('state',[None])[0]))
            if url.path=='/api/shorts':
                mid=q.get('media_id',[''])[0]
                m=MEDIA.get(mid)
                if not m: return self.respond({'error':'رسانه پیدا نشد.'},404)
                t=TRANSCRIPTS.get(mid)
                segs=t['segments'] if t else []
                return self.respond({'media_id':mid,'candidates':shorts_candidates(segs,m.get('duration'))})
            if url.path=='/api/renders':
                mid=q.get('media_id',[None])[0]
                rows=RENDERS.list(mid)
                names=RENDERS.media_names()
                for r in rows: r['media_name']=names.get(r['media_id'],'')
                return self.respond(rows)
            if url.path=='/api/seo/scans':
                site=q.get('site',['tehnet.ir'])[0]
                scans=SEOSTORE.scans(site)
                if 'full' in q and scans:
                    scans[0]['pages']=SEOSTORE.scan_pages(scans[0]['id'])
                return self.respond({'site':site,'scans':scans})
            if url.path=='/api/archive': return self.respond(ARCHIVE.list())
            if url.path=='/api/sync': return self.respond(SYNCSTORE.for_content(q.get('content_id',[''])[0]))
            if url.path=='/api/analytics/status':
                rows=adapter_status()
                for r in rows:
                    snaps=ANALYTICS.snapshots(r['platform'],limit=5)
                    r['snapshots']=len(ANALYTICS.snapshots(r['platform'],limit=1000))
                    r['anomalies']=detect_anomalies(ANALYTICS,r['platform'])
                    r['last_snapshot']=snaps[0]['captured_at'] if snaps else None
                return self.respond(rows)
            if url.path=='/api/analytics/snapshots': return self.respond(ANALYTICS.snapshots(q.get('platform',['youtube'])[0]))
            if url.path=='/api/analytics/proposals': return self.respond(ANALYTICS.proposals(q.get('status',[None])[0]))
            if url.path=='/api/analytics/schedule':
                return self.respond(recommend_slot(ANALYTICS,q.get('brand',[brand_default()])[0],q.get('platform',['youtube'])[0],q.get('ctype',['long'])[0]))
            if url.path=='/api/analytics/performance': return self.respond(ANALYTICS.performance(q.get('brand',[None])[0],q.get('platform',[None])[0]))
            if url.path.startswith('/oauth/callback'):
                q=parse_qs(url.query)
                try:
                    r=oauth_callback(q.get('provider',[''])[0],OAUTH,q.get('code',[''])[0],q.get('state',[''])[0])
                    return self.respond(r)
                except Exception as e:
                    return self.respond({'error':str(e)[:200]},400)
            if url.path=='/api/oauth/start':
                prov=data.get('provider'); base='http://127.0.0.1:'+str(PORT)
                try: return self.respond({'url':oauth_start_url(prov,OAUTH,base)})
                except DependencyMissing as e: return self.respond({'error':str(e)},400)
            if url.path=='/api/oauth/status':
                return self.respond({k:oauth_status(k) for k in OAUTH_PROVIDERS})
            if url.path=='/api/integrations':
                return self.respond({'core':adapter_status(),'optional':all_optional_integrations()})
            if url.path=='/api/ops/observability':
                JM.mark_stale_running()
                return self.respond(JM.observability())
            if url.path=='/api/keywords':
                return self.respond(KWSTORE.search(q.get('q',[''])[0]))
            if url.path=='/api/kb/stats': return self.respond(KB.stats())
            if url.path=='/api/kb/search':
                return self.respond(KB.search(q.get('q',[''])[0],int(q.get('limit',['5'])[0])))
            if url.path=='/api/content/refresh':
                return self.respond(refresh_candidates(DB.list(q.get('brand',[brand_default()])[0]),ANALYTICS.performance(brand=q.get('brand',[brand_default()])[0])))
            if url.path=='/api/content/checktopic':
                return self.respond(check_topic(DB.list(q.get('brand',[brand_default()])[0]),KB,q.get('title',[''])[0],q.get('keyword',[''])[0]))
            if url.path=='/api/content/optimize':
                o=None
                try: o=ANALYTICS.proposals()
                except Exception: pass
                return self.respond(optimize_content(q.get('text',[''])[0],q.get('title',[''])[0],
                    has_faq='faq' in q,has_schema='schema' in q))
            if url.path=='':
                rows=adapter_status()
                return self.respond(rows)
            if url.path=='/api/storage':
                data=Path(DB.path).parent
                ssd=[d for d in drives() if str(data).lower().startswith(d['letter'].lower())]
                passport=[d for d in drives() if 'passport' in (d['label'] or '').lower()]
                return self.respond({'drives':drives(),
                    'data':{'media':dir_size(data/'media'),'renders':dir_size(data/'renders'),
                            'dryrun':dir_size(data/'dryrun'),'db':Path(DB.path).stat().st_size if Path(DB.path).exists() else 0},
                    'passport':{'connected':bool(passport),'detail':passport[0] if passport else 'آرشیو خارجی در دسترس نیست'}})
            if url.path=='/api/publishing': return self.respond(publishing_status())
            if url.path=='/api/notifications': return self.respond({'items':NOTIF.list(),'unread':NOTIF.unread_count()})
            if url.path=='/api/whisper/settings': return self.respond({'model':WSSET.whisper_model(),'models':list(WHISPER_MODELS),'benchmarks':WSSET.benchmarks()})
            if url.path=='/api/ai/providers':
                rows=[]
                for p in AISTORE.providers():
                    p['api_key_env']=p['api_key_env'] or ''
                    rows.append(p)
                return self.respond({'providers':rows,'tasks':TASK_FA,
                                     'classification':classification_table(),'stages':{k:v for k,v in STAGE_SKILLS.items()}})
            if url.path=='/api/ai/outputs':
                return self.respond(AISTORE.outputs(q.get('content_id',[None])[0],q.get('kind',[None])[0]))
            if url.path=='/api/ai/sources':
                return self.respond(AISTORE.sources(q.get('content_id',[''])[0]))
            if url.path=='/api/ai/output':
                o=AISTORE.get_output(q.get('id',[''])[0])
                if not o: return self.respond({'error':'خروجی پیدا نشد.'},404)
                return self.respond(o)
            if url.path=='/api/health':
                qc={}
                for st in ('queued','running','waiting_approval','completed','failed','cancelled'):
                    qc[st]=len(JM.list(status=st))
                return self.respond(health_payload(DB.path,qc,len(JM._threads)))
            if url.path=='/api/media/file': return self.serve_media(q)
            if url.path=='/api/renders': return self.respond(RENDERS.list(q.get('media_id',[''])[0]))
            if url.path=='/api/renders/file':
                r=RENDERS.get(q.get('id',[''])[0])
                if not r or not Path(r['path']).exists(): return self.respond({'error':'خروجی پیدا نشد.'},404)
                return self.stream_file(r['path'],r['size'],'video/mp4')
            if url.path=='/api/decisions': return self.respond(DECISIONS.list(q.get('media_id',[''])[0],q.get('state',[None])[0]))
            if url.path=='/api/editreport': return self.respond({'media_id':q.get('media_id',[''])[0],'lines':report_lines(DECISIONS,q.get('media_id',[''])[0])})
            if url.path=='/api/transcripts':
                mid=q.get('media_id',[''])[0]
                if not mid: return self.respond({'error':'رسانه پیدا نشد.'},404)
                if 'all' in q: return self.respond(TRANSCRIPTS.list(mid))
                t=TRANSCRIPTS.get(mid,int(q['revision'][0]) if 'revision' in q else None)
                if not t: return self.respond({'error':'متن پیدا نشد.'},404)
                return self.respond(t)
            if url.path=='/api/jobs': return self.respond(JM.list(q.get('status',[None])[0]))
            if url.path=='/api/job':
                job=JM.get(q.get('id',[''])[0])
                if not job: return self.respond({'error':'کار پیدا نشد.'},404)
                return self.respond(job)
            if url.path=='/api/history': return self.respond(DB.history(q.get('id',[''])[0]))
            if url.path=='/api/items':
                b=q.get('brand',['tehran-network'])[0]
                rows=DB.list(b)
                if 'archived' not in q: rows=[r for r in rows if not r.get('archived')]
                return self.respond(rows)
            if url.path=='/api/export': return self.respond(DB.export(q.get('brand',['tehran-network'])[0]))
            if url.path=='/api/profile':
                brand=q.get('brand',[''])[0]
                if brand not in ('tehran-network','mytel'): raise ValueError('برند معتبر نیست.')
                d=ROOT.parent/'brands'/brand
                return self.respond({k:(d/(k+'.md')).read_text(encoding='utf-8') for k in ('about-me','voice','brand-kit')})
            if url.path=='/api/policy': return self.respond({'text':(ROOT.parent/'content-policy.fa.md').read_text(encoding='utf-8')})
            allowed={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css','/recorder.js':'recorder.js',
                     '/fonts/Vazirmatn-Regular.woff2':'fonts/Vazirmatn-Regular.woff2',
                     '/fonts/Vazirmatn-Medium.woff2':'fonts/Vazirmatn-Medium.woff2',
                     '/fonts/OFL.txt':'fonts/OFL.txt',
                     '/audit':'../audit.fa.md','/guide':'../README.fa.md'}
            if url.path not in allowed: return self.respond({'error':'صفحه پیدا نشد.'},404)
            file=ROOT/allowed[url.path]
            mime={'woff2':'font/woff2','.txt':'text/plain'}.get(file.suffix.lstrip('.')) or mimetypes.guess_type(file)[0] or 'text/plain'
            if file.suffix=='.md': mime='text/plain'
            self.send(file.read_bytes(),mime+'; charset=utf-8')
        except ValueError as e: self.respond({'error':str(e)},400)
        except Exception: self.respond({'error':'خواندن اطلاعات ناموفق بود؛ فایل‌ها و اجرای پنل را بررسی کنید.'},500)
    def require_auth(self):
        """401 when auth enabled and session token invalid. Returns True if responded.
        The CSRF token equals AUTH-disabled token; when auth is enabled and the
        caller presents the process CSRF token (not a session), treat as
        unauthenticated but let the login route through."""
        if not AUTH.enabled: return False
        tok=self.headers.get('X-Panel-Token')
        if tok==TOKEN:  # CSRF-level caller, not a logged session
            if urlsplit(self.path).path=='/api/auth/login': return False
            self.respond({'error':'برای این عملیات باید وارد شوید.'},401)
            return True
        if not AUTH.check(tok or ''):
            self.respond({'error':'نشست منقضی یا نامعتبر است؛ دوباره وارد شوید.'},401)
            return True
        return False
    def do_POST(self):
        tok=self.headers.get('X-Panel-Token')
        authed_session=AUTH.enabled and AUTH.check(tok or '')
        allowed_origins=(None,'http://127.0.0.1:'+str(PORT),'http://localhost:'+str(PORT),
                         'https://127.0.0.1:'+str(PORT),'https://localhost:'+str(PORT),
                         'http://tolid-web:'+str(PORT))
        # Unified same-origin rule for private reverse proxies (tailscale serve / sidecar):
        # Origin host must equal the Host AND that host must be local (loopback, container
        # service name), a .ts.net name, or a tailnet address (CGNAT v4 / fd7a v6) —
        # DNS-rebinding origins stay rejected.
        import ipaddress as _ipa
        def _host_ok(hh):
            raw=(hh or '').strip()
            if raw.startswith('[') and ']' in raw: hname=raw.split(']')[0][1:]   # [v6]:port
            else: hname=raw.split(':')[0].strip('[]')
            if hname in ('127.0.0.1','localhost','::1','[::1]','tolid-web'): return True
            if hname.endswith('.ts.net'): return True
            try:
                a=_ipa.ip_address(hname)
                return a in _ipa.ip_network('100.64.0.0/10') or a in _ipa.ip_network('fd7a:115c:a1e0::/48')
            except ValueError: return False
        _origin=self.headers.get('Origin')
        same_origin=(_origin is not None and _origin.startswith('http')
                     and _host_ok(_origin.split('//')[-1]) and _host_ok(self.headers.get('Host') or ''))
        if not self.valid_host() or (tok!=TOKEN and not authed_session) or (_origin not in allowed_origins and not same_origin):
            return self.respond({'error':'درخواست مجاز نیست؛ پنل را دوباره باز کنید.'},403)
        path=urlsplit(self.path).path
        if path=='/api/media': return self.require_auth() or self.upload_media()
        if path=='/api/auth/logout' and self.require_auth(): return
        if self.require_auth() and path!='/api/auth/login': return
        if self.headers.get_content_type()!='application/json': return self.respond({'error':'قالب درخواست معتبر نیست.'},415)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if path=='/api/auth/logout':
                AUTH.logout(self.headers.get('X-Panel-Token')); return self.respond({'ok':True})
            if size<1 or size>1500000: raise ValueError('حجم درخواست معتبر نیست.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError('درخواست معتبر نیست.')
            if path=='/api/auth/login':
                # reachable without a session (CSRF token above already gates it)
                if not AUTH.enabled: return self.respond({'ok':True,'note':'احراز هویت فعال نیست؛ پنل فقط روی loopback است.'})
                r=AUTH.login(data.get('username'),data.get('password'),self.client_address[0])
                return self.respond(r,200 if r.get('ok') else 401)
            if self.path=='/api/items': return self.respond(DB.save(data))
            if self.path=='/api/project/archive': return self.respond(DB.set_archived(data.get('id'),bool(data.get('archived',True))))
            if self.path=='/api/project/rename': return self.respond(DB.rename(data.get('id'),data.get('title')))
            if self.path=='/api/project/delete':
                pid=data.get('id'); force=bool(data.get('confirm_published')) and data.get('typed')=='حذف'
                if not isinstance(pid,str): raise ValueError('شناسه نامعتبر است.')
                deps=project_dependencies(pid,JM)
                try: DB.delete(pid,force_published=force)
                except ValueError as e:
                    if str(e).startswith('WARN_PUBLISHED'):
                        return self.respond({'error':str(e),'warning':True,
                            'detail':'پست‌های بیرونی (وردپرس/یوتیوب/تلگرام/…) دست‌نخورده می‌مانند؛ این حذف فقط محلی است.'},409)
                    raise
                delete_project_files(deps,DB)
                return self.respond({'ok':True,'deleted':{'content':1,**deps['counts']}})
            if self.path=='/api/decide':
                before=DB.get(data.get('id')) if isinstance(data.get('id'),str) else None
                prev=before.get(data.get('gate')+'_status') if before else None
                item=DB.decide(data.get('id'),data.get('revision'),data.get('gate'),data.get('status'))
                if data.get('gate')=='publish' and data.get('status')=='approved' and prev!='approved':
                    try: on_publish_approved(JM,item['id'],item['revision'])
                    except ValueError: pass
                return self.respond(item)
            if self.path=='/api/jobs':
                kind=data.get('kind'); payload=data.get('payload') if isinstance(data.get('payload'),dict) else {}
                if kind=='transcribe_audio':
                    m=MEDIA.get(payload.get('media_id') or '')
                    if not m: raise ValueError('رسانه پیدا نشد.')
                    v=validate_audio(m['id'])
                    if v.get('status')=='INVALID_AUDIO':
                        return self.respond({'error':'INVALID_AUDIO: '+v.get('reason',''),'invalid':True,
                                             'detail':'ضبط/فایل صدای قابل استفاده ندارد؛ Whisper اجرا نشد.'},400)
                return self.respond(JM.enqueue(kind,payload,data.get('idempotency_key')))
            if self.path=='/api/jobs/decision':
                jid=data.get('id')
                if not isinstance(jid,str) or not isinstance(data.get('approved'),bool): raise ValueError('درخواست معتبر نیست.')
                return self.respond(JM.decide(jid,data['approved']))
            if self.path=='/api/transcripts':
                m=MEDIA.get(data.get('media_id'))
                if not m: raise ValueError('رسانه پیدا نشد.')
                text=data.get('text')
                if not isinstance(text,str) or not text.strip(): raise ValueError('متن خالی قابل ذخیره نیست.')
                t=TRANSCRIPTS.add(m['id'],text,parse_timed_text(text),'manual_import')
                return self.respond(t)
            if self.path=='/api/whisper/model':
                return self.respond({'model':WSSET.set_whisper_model(data.get('model'))})
            if self.path=='/api/whisper/benchmark':
                return self.respond(JM.enqueue('whisper_benchmark',data,idempotency_key='bench:'+uuid.uuid4().hex))
            if self.path=='/api/sync/save':
                SYNCSTORE.save(data.get('content_id'),data.get('media_id'),data.get('reference_media_id'),
                               float(data.get('offset_seconds')),data.get('method') or 'manual',float(data.get('confidence',1.0)))
                return self.respond({'ok':True})
            if self.path=='/api/sync/clear':
                SYNCSTORE.clear(data.get('media_id')); return self.respond({'ok':True})
            if self.path=='/api/seo/scan':
                return self.respond(JM.enqueue('seo_scan',{'site':data.get('site')},idempotency_key='seoscan:'+data.get('site','')+':'+uuid.uuid4().hex))
            if self.path=='/api/archive/copy':
                return self.respond(JM.enqueue('archive_copy',{'content_id':data.get('content_id'),'passport_path':data.get('passport_path'),'approved':data.get('approved')},
                    idempotency_key='archive:'+data.get('content_id','')+':'+uuid.uuid4().hex))
            if self.path=='/api/analytics/sync':
                return self.respond(JM.enqueue('analytics_sync',{'platform':data.get('platform')},idempotency_key='as:'+str(data.get('platform'))+':'+uuid.uuid4().hex))
            if self.path=='/api/analytics/optimize':
                return self.respond(JM.enqueue('optimize_content',data,idempotency_key='opt:'+str(data.get('content_id'))+':'+uuid.uuid4().hex))
            if self.path=='/api/analytics/record':
                ANALYTICS.upsert_performance(data.get('content_id'),data.get('brand','tehran-network'),data.get('platform','youtube'),
                    data.get('content_type','long'),data.get('pillar',''),data.get('topic',''),data.get('hook',''),data.get('title',''),
                    data.get('thumbnail',''),data.get('video_seconds'),data.get('short_seconds'),data.get('cta',''),data.get('sponsor',''),
                    data.get('publish_day',''),data.get('publish_hour'),data.get('metrics') or {})
                return self.respond({'ok':True})
            if self.path=='/api/analytics/proposal/decide':
                ANALYTICS.decide_proposal(data.get('id'),data.get('decision'))
                return self.respond({'ok':True})
            if self.path=='/api/analytics/snapshot':
                ANALYTICS.add_snapshot(data.get('platform','youtube'),data.get('brand'),data.get('external_id'),
                                       data.get('metrics') or {},data.get('source','manual'))
                return self.respond({'ok':True})
            if self.path=='/api/gsc/ingest':
                return self.respond(JM.enqueue('gsc_ingest',{'site':data.get('site'),'start':data.get('start'),'end':data.get('end')},
                    idempotency_key='gsc:'+uuid.uuid4().hex))
            if self.path=='/api/gemini/generate':
                return self.respond(JM.enqueue('gemini_image',{'prompt':data.get('prompt'),'content_id':data.get('content_id')},
                    idempotency_key='gem:'+uuid.uuid4().hex))
            if self.path=='/api/keywords/add':
                for row in (data.get('rows') or [data]):
                    KWSTORE.add(row.get('keyword'),row.get('language','fa'),row.get('country','IR'),
                                row.get('volume_monthly'),row.get('volume_range'),row.get('competition'),
                                row.get('cpc_avg'),row.get('source','manual'))
                return self.respond({'ok':True})
            if self.path=='/api/kb/reindex':
                return self.respond({'indexed':index_project(KB,DB,AISTORE)})
            if self.path=='/api/ga4/fetch':
                try:
                    metrics=ga4_fetch()
                    ANALYTICS.add_snapshot('ga4',brand,None,
                        {k:v for k,v in metrics.items()},'ga4-api')
                    return self.respond({'ok':True,'metrics':metrics})
                except DependencyMissing as e:
                    return self.respond({'error':str(e)},400)
            if self.path=='/api/integrations/test':
                return self.respond(adapter_health(data.get('platform')))
            if self.path=='/api/weekly-plan':
                return self.respond(JM.enqueue('weekly_plan',{'brand':data.get('brand',brand_default())},idempotency_key='wp:'+str(data.get('brand'))+':'+uuid.uuid4().hex))
            if self.path=='/api/seo/proposals':
                return self.respond(JM.enqueue('seo_proposals',{'site':data.get('site','tehnet.ir')},idempotency_key='sep:'+str(data.get('site'))+':'+uuid.uuid4().hex))
            if self.path=='/api/shorts/v2':
                return self.respond(JM.enqueue('shorts_v2',{'media_id':data.get('media_id')},idempotency_key='sv2:'+str(data.get('media_id'))+':'+uuid.uuid4().hex))
            if self.path=='/api/notifications/read': return self.respond({'unread':(NOTIF.mark_read(data.get('id')) or 0) or NOTIF.unread_count()})
            if self.path=='/api/notifications/telegram/test': return self.respond(telegram_send('آزمون اعلان از کارخانه محتوا'))
            if self.path=='/api/ai/providers/save':
                return self.respond(AISTORE.save_provider(data.get('name'),data.get('base_url',''),
                    data.get('model',''),data.get('api_key_env',''),data.get('tasks',[]),data.get('enabled',True)))
            if self.path=='/api/ai/health':
                return self.respond(provider_health(AISTORE,data.get('name')))
            if self.path=='/api/assets/state':
                return self.respond(MEDIA.set_asset_state(data.get('media_id'),data.get('state'),data.get('label')))
            if self.path=='/api/health/gpu':
                return self.respond(gpu_probe())
            if self.path=='/api/media/delete':
                mid=data.get('mid'); m=MEDIA.get(mid)
                if not m: raise ValueError('رسانه پیدا نشد.')
                if not data.get('confirm'): raise ValueError('تأیید حذف لازم است.')
                for j in JM.list(limit=200):
                    if (j.get('payload') or {}).get('media_id')==mid and j['status'] in ('queued','running','waiting_approval'):
                        try: JM.cancel(j['id'])
                        except Exception: pass
                delete_media_row(mid,MEDIA,TRANSCRIPTS,DECISIONS,RENDERS)
                return self.respond({'ok':True})
            if self.path=='/api/media/validate':
                return self.respond(validate_audio(data.get('media_id')))
            if self.path=='/api/decisions/manual':
                return self.respond(DECISIONS.add(data.get('media_id'),float(data.get('start')),float(data.get('end')),
                    'manual',1.0,'manual','active',reason=data.get('reason')))
            if self.path=='/api/decisions/state':
                return self.respond(DECISIONS.set_state(data.get('id'),data.get('state')))
            if self.path=='/api/jobs/cancel': return self.respond(JM.cancel(data.get('id')))
            if self.path=='/api/jobs/retry': return self.respond(JM.retry(data.get('id')))
            self.respond({'error':'عملیات پیدا نشد.'},404)
        except (ValueError,TypeError) as e: self.respond({'error':str(e) if isinstance(e,ValueError) and not isinstance(e,json.JSONDecodeError) else 'داده درخواست معتبر نیست.'},400)
        except Exception: self.respond({'error':'ذخیره ناموفق بود. فضای دیسک و اجرای پنل را بررسی کنید.'},500)
    def upload_media(self):
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>MAX_UPLOAD: raise ValueError('حجم فایل معتبر نیست.')
            kind=self.headers.get('X-Media-Kind','')
            name=self.headers.get('X-Media-Name','file')
            cid=self.headers.get('X-Content-Id') or None
            remaining=[size]
            def reader(n):
                if remaining[0]<=0: return b''
                chunk=self.rfile.read(min(n,remaining[0]))
                remaining[0]-=len(chunk)
                return chunk
            row=MEDIA.ingest(reader,name,kind,cid,size_limit=MAX_UPLOAD,mime=self.headers.get('X-Media-Mime',''))
            return self.respond(row)
        except ValueError as e: self.respond({'error':str(e)},400)
        except Exception: self.respond({'error':'ذخیره رسانه ناموفق بود؛ فضای دیسک را بررسی کنید.'},500)

_JOB_STATES={}
def _watch_jobs():
    """Record meaningful job transitions as dashboard notifications (no spam:
    only failures, waiting-approvals and finished renders/AI work)."""
    import time
    while True:
        try:
            for j in JM.list(limit=40):
                st=_JOB_STATES.get(j['id'])
                if st and st!=j['status']:
                    kind=j['kind']
                    if j['status']=='failed':
                        NOTIF.add('job_failed',(jobKinds_fa().get(kind,kind)+' ناموفق بود'),j.get('error') or '',j['id'])
                    elif j['status']=='waiting_approval':
                        NOTIF.add('approval_needed',(jobKinds_fa().get(kind,kind)+' منتظر تأیید شماست'),'',j['id'])
                    elif j['status']=='completed' and kind in ('render_cut','render_short','content_pipeline','generate_script','research_topic'):
                        NOTIF.add('render_done' if kind.startswith('render') else 'ai_done',(jobKinds_fa().get(kind,kind)+' کامل شد'),'',j['id'])
                _JOB_STATES[j['id']]=j['status']
        except Exception:
            pass
        time.sleep(8)

def jobKinds_fa():
    return {'transcribe_audio':'تبدیل گفتار به متن','edit_detect':'تحلیل تدوین','render_cut':'رندر','render_short':'رندر عمودی','publish_dryrun':'بسته انتشار','website_publish':'پیش‌نویس وردپرس','research_topic':'تحقیق','technical_verification':'بررسی فنی','generate_script':'سناریو','generate_hooks':'هوک‌ها','generate_title_packages':'بسته‌های عنوان/کاور','generate_social':'نسخهٔ شبکه‌ها','generate_article':'مقاله','generate_pinned':'کامنت پین','content_pipeline':'خط تولید'}

if __name__=='__main__':
    import threading
    threading.Thread(target=_watch_jobs,daemon=True).start()
    # bind: loopback on the host; inside Docker (TEHNET_PANEL_BIND) the container can bind all
# interfaces safely — reachability is still governed by the compose publish (127.0.0.1-only)
# and the private tolid_internal network.
    server=ThreadingHTTPServer((os.environ.get('TEHNET_PANEL_BIND','127.0.0.1'),PORT),Handler)
    print(f'Panel: http://127.0.0.1:{PORT}',flush=True)
    server.serve_forever()
