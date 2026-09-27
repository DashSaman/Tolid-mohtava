from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json, mimetypes, os, secrets, socket
from store import Store
from registry import skill_registry
from jobs import JobManager

ROOT=Path(__file__).resolve().parent
PORT=int(os.environ.get('TEHNET_PANEL_PORT','8766'))
DB=Store(os.environ.get('TEHNET_PANEL_DB',str(ROOT/'data/content.sqlite')))
JM=JobManager(DB.path,workers=2)
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
    def do_GET(self):
        if not self.valid_host(): return self.respond({'error':'میزبان مجاز نیست.'},403)
        url=urlsplit(self.path); q=parse_qs(url.query)
        try:
            if url.path=='/api/session': return self.respond({'token':TOKEN,'app':'tehnet-content-panel'})
            if url.path=='/api/skills': return self.respond(skill_registry())
            if url.path=='/api/items': return self.respond(DB.list(q.get('brand',['tehran-network'])[0]))
            if url.path=='/api/jobs': return self.respond(JM.list(q.get('status',[None])[0]))
            if url.path=='/api/job':
                job=JM.get(q.get('id',[''])[0])
                if not job: return self.respond({'error':'کار پیدا نشد.'},404)
                return self.respond(job)
            if url.path=='/api/history': return self.respond(DB.history(q.get('id',[''])[0]))
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
        if self.headers.get_content_type()!='application/json': return self.respond({'error':'قالب درخواست معتبر نیست.'},415)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>1500000: raise ValueError('حجم درخواست معتبر نیست.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError('درخواست معتبر نیست.')
            if self.path=='/api/items': return self.respond(DB.save(data))
            if self.path=='/api/decide': return self.respond(DB.decide(data.get('id'),data.get('revision'),data.get('gate'),data.get('status')))
            if self.path=='/api/jobs': return self.respond(JM.enqueue(data.get('kind'),data.get('payload') if isinstance(data.get('payload'),dict) else {},data.get('idempotency_key')))
            if self.path=='/api/jobs/decision':
                jid=data.get('id')
                if not isinstance(jid,str) or not isinstance(data.get('approved'),bool): raise ValueError('درخواست معتبر نیست.')
                return self.respond(JM.decide(jid,data['approved']))
            if self.path=='/api/jobs/cancel': return self.respond(JM.cancel(data.get('id')))
            if self.path=='/api/jobs/retry': return self.respond(JM.retry(data.get('id')))
            self.respond({'error':'عملیات پیدا نشد.'},404)
        except (ValueError,TypeError) as e: self.respond({'error':str(e) if isinstance(e,ValueError) and not isinstance(e,json.JSONDecodeError) else 'داده درخواست معتبر نیست.'},400)
        except Exception: self.respond({'error':'ذخیره ناموفق بود. فضای دیسک و اجرای پنل را بررسی کنید.'},500)

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    print(f'Panel: http://127.0.0.1:{PORT}',flush=True)
    server.serve_forever()
