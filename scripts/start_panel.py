"""Start only this panel; never start or reconfigure GrowthOS services.
If the preferred port is occupied by a FOREIGN service (e.g. a leftover
proxy tool answering with a non-panel body), fall back to the next port
so the user always gets a working panel automatically."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time,urllib.request,urllib.error,webbrowser
ROOT=Path(__file__).resolve().parents[1]

def is_panel(url):
    try:
        with urllib.request.urlopen(url+'/api/session',timeout=1.5) as r:
            return json.load(r).get('app')=='tehnet-content-panel'
    except Exception:
        return False

def free_port_for_binding(host,port):
    """True if we can probably bind (nothing on it at all)."""
    import socket
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,0)
        try:
            s.bind((host,port)); return True
        except OSError:
            return False

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--no-browser',action='store_true')
    a=p.parse_args()
    base=int(os.environ.get('TEHNET_PANEL_PORT','8766'))
    url=None
    for port in (base,base+1,base+2):
        cand=f'http://127.0.0.1:{port}'
        if is_panel(cand):
            url=cand; break                      # our panel already running there
        if free_port_for_binding('127.0.0.1',port):
            kwargs={'cwd':str(ROOT),'stdin':subprocess.DEVNULL,'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL}
            if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
            else:kwargs['start_new_session']=True
            child=subprocess.Popen([sys.executable,str(ROOT/'outputs/panel/server.py')],**kwargs,
                                   env=dict(os.environ,TEHNET_PANEL_PORT=str(port)))
            for _ in range(40):
                if is_panel(cand):break
                if child.poll() is not None:break
                time.sleep(.2)
            if is_panel(cand):
                url=cand
                if port!=base:
                    print(f'توجه: پورت {base} توسط سرویس دیگری اشغال است؛ پنل روی {port} بالا آمد.')
                break
    if not url:
        raise SystemExit(f'پورت‌های {base}-{base+2} در دسترس نیستند. اگر ابزار قدیمی (مثل AutoClaw) روی {base} نشسته، آن را با دسترسی Administrator ببندید یا TEHNET_PANEL_PORT را عوض کنید.')
    print(url)
    if not a.no_browser:webbrowser.open(url)
