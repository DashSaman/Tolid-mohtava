# -*- coding: utf-8 -*-
"""پروکسی خصوصی Tolid-Mohtava روی Tailscale — فقط برای حالت جایگزین (بدون HTTPS Serve).

connection:  http://<TAILSCALE_IP>:<panel_port>   ← فقط همین آدرس bind می‌شود (هرگز 0.0.0.0)
forwards to: http://127.0.0.1:<panel_port>         ← پنل همان‌طور که هست loopback می‌ماند

امنیت:
- تنها هدرهای Host/Origin که دقیقاً به آدرسِ همین پروکسی اشاره دارند به شکل loopback
  بازنویسی می‌شوند (همان‌-origin واقعی)؛ هر Host/Origin دیگری دست‌نخورده عبور می‌کند و
  دروازه‌های خود پنل (whitelist لوکال/.ts.net + CSRF) آن را رد می‌کنند.
- احراز هویت ADMIN پنل روی این مسیر هم اجباری است (همان process rules).
- این مسیر HTTPS نیست؛ رمزنگاری لایهٔ انتقال را خود tailnet تأمین می‌کند.
"""
import http.client,os,socket,sys,urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def tailscale_ip():
    out=sys.stdout
    try:
        import subprocess,json
        r=subprocess.run([r'C:\Program Files\Tailscale\tailscale.exe','ip','-4'],
                         capture_output=True,text=True,timeout=10)
        ip=r.stdout.strip().splitlines()[0].strip() if r.stdout.strip() else ''
        return ip if ip.startswith('100.') else ''
    except Exception:
        return ''

def panel_port():
    for p in (8766,8767,8768):
        try:
            r=urllib.request.urlopen(f'http://127.0.0.1:{p}/api/session',timeout=2)
            import json as _j
            if _j.loads(r.read()).get('app')=='tehnet-content-panel': return p
        except Exception: pass
    return None

TS_IP=tailscale_ip()
PORT=panel_port()
HOP=[('Host',f'127.0.0.1:{PORT}'),('Origin',f'http://127.0.0.1:{PORT}')]

class Proxy(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def _relay(self,include_body=True):
        n=int(self.headers.get('Content-Length','0') or 0)
        body=self.rfile.read(n) if include_body and n>0 else None
        hop=self.headers.get('Host','')
        own=f'{TS_IP}:{PORT}'
        # rewrite ONLY the exact same-origin-to-this-proxy forms; everything else passes verbatim
        if hop==own: host_hdr=HOP[0][1]
        else: host_hdr=hop
        conn=http.client.HTTPConnection('127.0.0.1',PORT,timeout=120)
        headers={}
        for k,v in self.headers.items():
            if k.lower()=='host': headers['Host']=host_hdr
            elif k.lower()=='origin':
                origin=self.headers.get('Origin')
                headers['Origin']=HOP[1][1] if origin==f'http://{own}' else origin or ''
            else: headers[k]=v
        headers.pop('Accept-Encoding',None)  # keep identity so relay is byte-exact
        try:
            conn.request(self.command,self.path,body=body,headers=headers)
            resp=conn.getresponse()
            self.send_response_only(resp.status)
            for k,v in resp.getheaders():
                if k.lower() in ('transfer-encoding','connection','keep-alive'): continue
                self.send_header(k,v)
            self.send_header('Connection','close')
            self.end_headers()
            while True:
                chunk=resp.read(65536)
                if not chunk: break
                try: self.wfile.write(chunk);self.wfile.flush()
                except (BrokenPipeError,ConnectionResetError): break
        except Exception as e:
            try:
                self.send_response_only(502);self.send_header('Content-Length','0');self.end_headers()
            except Exception: pass
        finally: conn.close()
    def do_GET(self): self._relay(include_body=False)
    def do_HEAD(self): self._relay(include_body=False)
    def do_POST(self): self._relay(include_body=True)
    def do_PUT(self): self._relay(include_body=True)
    def do_DELETE(self): self._relay(include_body=True)
    def log_message(self,*a): pass

if __name__=='__main__':
    if not TS_IP: print('✗ آدرس Tailscale پیدا نشد (tailscale ip -4)');sys.exit(1)
    if not PORT: print('✗ پنل محلی پیدا نشد؛ اول Open-Panel.cmd را اجرا کنید.');sys.exit(1)
    srv=ThreadingHTTPServer((TS_IP,PORT),Proxy)
    print(f'✓ پروکسی خصوصی روی http://{TS_IP}:{PORT} → 127.0.0.1:{PORT} (فقط tailnet؛ بدون HTTPS)',flush=True)
    srv.serve_forever()
