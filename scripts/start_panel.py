"""Start only this panel; never start or reconfigure GrowthOS services."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time,urllib.request,webbrowser
ROOT=Path(__file__).resolve().parents[1]

def is_panel(url):
    try:
        with urllib.request.urlopen(url+'/api/session',timeout=1) as r:
            return json.load(r).get('app')=='tehnet-content-panel'
    except (OSError,ValueError):return False

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--no-browser',action='store_true')
    a=p.parse_args()
    port=int(os.environ.get('TEHNET_PANEL_PORT','8766'))
    url=f'http://127.0.0.1:{port}'
    if not is_panel(url):
        kwargs={'cwd':str(ROOT),'stdin':subprocess.DEVNULL,'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL}
        if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
        else:kwargs['start_new_session']=True
        child=subprocess.Popen([sys.executable,str(ROOT/'outputs/panel/server.py')],**kwargs)
        for _ in range(30):
            if is_panel(url):break
            if child.poll() is not None:raise SystemExit('Panel failed to start. Check the port and run outputs/panel/server.py for diagnostics.')
            time.sleep(.2)
        else:raise SystemExit('Panel readiness timed out. Run outputs/panel/server.py for diagnostics.')
    print(url)
    if not a.no_browser:webbrowser.open(url)
