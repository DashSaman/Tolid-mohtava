# -*- coding: utf-8 -*-
"""دسترسی راهِ‌دور امن به پنل Tolid-Mohtava از طریق Tailscale (فقط شبکهٔ خصوصی).

مراحل:
  1) پنل محلی را پیدا/راه‌اندازی می‌کند (پورت واقعی 8766/8767/8768 تشخیص داده می‌شود).
  2) اگر احراز هویت ADMIN فعال نباشد، دستورِ راه‌انداز آن را نشان می‌دهد و متوقف می‌شود
     (هرگز سرویس را بی‌رمز در دسترس راه‌دور نمی‌گذارد).
  3) اگر Tailscale وارد نشده باشد، نشانی ورود را باز می‌کند و متوقف می‌شود.
  4) `tailscale serve` را روی همان پورت واقعی تنظیم/به‌روزرسانی می‌کند (فقط tailnet،
     بدون Funnel و بدون پورت عمومی) و نشانی خصوصی را چاپ/باز می‌کند.

اجرا:  python scripts\\remote_access.py   (یا دوبار کلیک روی Open-Panel-Remote.cmd)
"""
import json,os,socket,subprocess,sys,time,urllib.request,webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
TS=Path(r'C:\Program Files\Tailscale\tailscale.exe')
PANEL_PORTS=(8766,8767,8768)

def say(m): print(m,flush=True)

def panel_port():
    """پورت پنل واقعی را برمی‌گرداند (پاسخ /api/session با app درست، نه سرویس خارجی)."""
    for p in PANEL_PORTS:
        try:
            r=urllib.request.urlopen(f'http://127.0.0.1:{p}/api/session',timeout=2)
            d=json.loads(r.read())
            if d.get('app')=='tehnet-content-panel': return p,d
        except Exception: pass
    return None,None

def registry_admin_env():
    """ADMIN_* از رجیستری (User سپس Machine) — تا پنلِ استارت‌شده توسط این اسکریپت
    همیشه اعتبارنامهٔ تازه‌ی setx-شده را ببیند (فرزند، env والد را به‌ارث می‌برد)."""
    out={}
    try:
        import winreg
        for root,scope in ((winreg.HKEY_CURRENT_USER,'User'),(winreg.HKEY_LOCAL_MACHINE,'Machine')):
            try:
                with winreg.OpenKey(root,'Environment') as k:
                    for name in ('ADMIN_USER','ADMIN_PASSWORD','ADMIN_PASSWORD_HASH'):
                        try:
                            v,_=winreg.QueryValueEx(k,name)
                            if v and name not in out: out[name]=v
                        except FileNotFoundError: pass
            except FileNotFoundError: pass
    except Exception: pass
    return out

def start_panel():
    say('· پنل بالا نیست — راه‌اندازی…')
    py=sys.executable
    env=dict(os.environ)
    for k,v in registry_admin_env().items():
        env.setdefault(k,v)
    subprocess.Popen([py,str(ROOT/'scripts'/'start_panel.py')],
                     cwd=str(ROOT),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(20):
        time.sleep(1)
        port,d=panel_port()
        if port: return port,d
    return None,None

def ts(args,check=True):
    r=subprocess.run([str(TS)]+args,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if check and r.returncode!=0:
        say('خطای Tailscale: '+(r.stderr or r.stdout).strip()[:200]);sys.exit(1)
    return r

def main():
    say('═'*52);say('  دسترسی راه‌دور امن — Tolid-Mohtava (Tailscale)');say('═'*52)
    if not TS.exists():
        say('✗ Tailscale نصب نیست. نصب رسمی:');say('  winget install Tailscale.Tailscale');sys.exit(1)

    port,sess=panel_port() or (None,None)
    if not port: port,sess=start_panel()
    if not port: say('✗ پنل راه‌اندازی نشد؛ Open-Panel.cmd را دستی اجرا کنید.');sys.exit(1)
    say(f'✓ پنل محلی روی 127.0.0.1:{port} فعال است.')

    if not sess.get('auth_required'):
        say('')
        say('✗ احراز هویت ADMIN فعال نیست — دسترسی راه‌دور قفل می‌ماند (بدون رمز، سرویس در دسترس گذاشته نمی‌شود).')
        say('  برای فعال‌سازی، در PowerShell این دو متغیر کاربر را تنظیم و بعد پنل را یک‌بار ببندید/باز کنید:')
        say("    [Environment]::SetEnvironmentVariable('ADMIN_USER','نام‌کاربری','User')")
        say("    [Environment]::SetEnvironmentVariable('ADMIN_PASSWORD','رمز‌قوی','User')")
        say('  سپس دوباره همین فایل (Open-Panel-Remote.cmd) را اجرا کنید.')
        say('  راهنمای کامل: docs/REMOTE-ACCESS.fa.md')
        sys.exit(2)

    st=ts(['status'],check=False)
    if 'Logged out' in st.stdout or st.returncode!=0:
        login=ts(['login'],check=False)
        url=next((l.strip() for l in (login.stdout+login.stderr).splitlines() if 'https://login.tailscale.com/a/' in l),'')
        say('')
        say('USER ACTION REQUIRED: ورود به Tailscale')
        if url:
            say('  نشانی ورود: '+url)
            try: webbrowser.open(url)
            except Exception: pass
        else:
            say('  از منوی Try Tailscale گزینهٔ Log in را بزنید.')
        say('  پس از ورود، دوباره همین فایل را اجرا کنید.')
        sys.exit(3)

    try:
        me=json.loads(ts(['status','--json']).stdout).get('Self') or {}
        dns=(me.get('DNSName') or '').rstrip('.')
    except Exception: dns=''
    say('✓ Tailscale متصل است'+(f' ({dns})' if dns else ''))

    # serve: only tailnet (https 443 → local panel). Idempotent; follows the ACTUAL port.
    # First run may need one-time tailnet enablement: capture the admin-console URL for the user.
    r=ts(['serve','--bg','--https=443',f'http://127.0.0.1:{port}'],check=False)
    if r.returncode!=0 or 'not enabled' in (r.stdout+r.stderr):
        out=(r.stdout+r.stderr)
        url=next((l.strip() for l in out.splitlines() if l.strip().startswith('https://login.tailscale.com/')),'')
        say('')
        say('USER ACTION REQUIRED: فعال‌سازی یک‌بارهٔ Serve روی tailnet (اقدام ادمین کنسول Tailscale)')
        if url:
            say('  این نشانی را در مرورگر باز کنید و تأیید کنید:')
            say('  '+url)
            try: webbrowser.open(url)
            except Exception: pass
            say('  سپس همین فایل را دوباره اجرا کنید.')
        sys.exit(4)
    ts(['serve','--bg','--https=443',f'http://127.0.0.1:{port}'],check=False)
    shown=ts(['serve','status'],check=False).stdout.strip()
    say('· تنظیم serve: '+ (shown.splitlines()[0] if shown else 'ok'))
    url=('https://'+dns) if dns else '(نام دستگاه را از tailscale status ببینید)'
    say('')
    say('✓ نشانی خصوصی (فقط دستگاه‌های تأییدشدهٔ Tailscale شما):')
    say('  '+url)
    try: webbrowser.open(url)
    except Exception: pass
    say('')
    say('قطع دسترسی راه‌دور در هر زمان:')
    say('  tailscale serve off     (حذف پروکسی)     tailscale down  (قطع شبکهٔ خصوصی)')

if __name__=='__main__':
    main()
