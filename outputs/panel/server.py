from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json, mimetypes, os, secrets, socket
from store import Store
from registry import skill_registry
from jobs import JobManager
from media import MediaLibrary, KINDS as MEDIA_KINDS
from transcribe import Transcripts
from editing import EditDecisions, report_lines
from render import Renders
from triggers import on_publish_approved
from transcribe import parse_timed_text
from handlers import build_handlers

ROOT=Path(__file__).resolve().parent
PORT=int(os.environ.get('TEHNET_PANEL_PORT','8766'))
DB=Store(os.environ.get('TEHNET_PANEL_DB',str(ROOT/'data/content.sqlite')))
DATA=Path(DB.path).parent
MEDIA=MediaLibrary(DB.path,DATA/'media')
TRANSCRIPTS=Transcripts(DB.path)
DECISIONS=EditDecisions(DB.path)
RENDERS=Renders(DB.path,DATA/'renders')
JM=JobManager(DB.path,handlers=build_handlers(),workers=2,
              services={'media':MEDIA,'transcripts':TRANSCRIPTS,'decisions':DECISIONS,'renders':RENDERS,
                        'store':DB,'dryrun_root':str(DATA/'dryrun')})
MAX_UPLOAD=20*1024*1024*1024
TOKEN=secrets.token_urlsafe(32)

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
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers(); self.wfile.write(data)
    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{PORT}',f'localhost:{PORT}')
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
            if url.path=='/api/session': return self.respond({'token':TOKEN,'app':'tehnet-content-panel'})
            if url.path=='/api/skills': return self.respond(skill_registry())
            if url.path=='/api/media': return self.respond(MEDIA.list(q.get('content_id',[None])[0],q.get('kind',[None])[0]))
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
            if url.path=='/api/items': return self.respond(DB.list(q.get('brand',['tehran-network'])[0]))
            if url.path=='/api/export': return self.respond(DB.export(q.get('brand',['tehran-network'])[0]))
            if url.path=='/api/profile':
                brand=q.get('brand',[''])[0]
                if brand not in ('tehran-network','mytel'): raise ValueError('برند معتبر نیست.')
                d=ROOT.parent/'brands'/brand
                return self.respond({k:(d/(k+'.md')).read_text(encoding='utf-8') for k in ('about-me','voice','brand-kit')})
            if url.path=='/api/policy': return self.respond({'text':(ROOT.parent/'content-policy.fa.md').read_text(encoding='utf-8')})
            allowed={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css','/audit':'../audit.fa.md','/guide':'../README.fa.md'}
            if url.path not in allowed: return self.respond({'error':'صفحه پیدا نشد.'},404)
            file=ROOT/allowed[url.path]
            mime=mimetypes.guess_type(file)[0] or 'text/plain'
            if file.suffix=='.md': mime='text/plain'
            self.send(file.read_bytes(),mime+'; charset=utf-8')
        except ValueError as e: self.respond({'error':str(e)},400)
        except Exception: self.respond({'error':'خواندن اطلاعات ناموفق بود؛ فایل‌ها و اجرای پنل را بررسی کنید.'},500)
    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-Panel-Token')!=TOKEN or self.headers.get('Origin') not in (None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
            return self.respond({'error':'درخواست مجاز نیست؛ پنل را دوباره باز کنید.'},403)
        if urlsplit(self.path).path=='/api/media': return self.upload_media()
        if self.headers.get_content_type()!='application/json': return self.respond({'error':'قالب درخواست معتبر نیست.'},415)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>1500000: raise ValueError('حجم درخواست معتبر نیست.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError('درخواست معتبر نیست.')
            if self.path=='/api/items': return self.respond(DB.save(data))
            if self.path=='/api/decide':
                item=DB.decide(data.get('id'),data.get('revision'),data.get('gate'),data.get('status'))
                if data.get('gate')=='publish' and data.get('status')=='approved':
                    try: on_publish_approved(JM,item['id'],item['revision'])
                    except ValueError: pass
                return self.respond(item)
            if self.path=='/api/jobs': return self.respond(JM.enqueue(data.get('kind'),data.get('payload') if isinstance(data.get('payload'),dict) else {},data.get('idempotency_key')))
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

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    print(f'Panel: http://127.0.0.1:{PORT}',flush=True)
    server.serve_forever()
