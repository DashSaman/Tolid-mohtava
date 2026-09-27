"""Publishing adapters: real code, honest credential gating.

Nothing publishes without: (1) explicit user approval, (2) credentials present
in the environment. Credentials never live in the database or the repo.
tehnet.ir and mytel.one were probed on 2026-09-27: both are WordPress with
live wp-json REST APIs (PHP 8.3, Cloudflare; mytel uses Elementor), so the
website path uses the standard WP REST draft endpoint.
"""
import base64, json, os, urllib.request

SITES={'tehnet.ir':{'env_prefix':'WP_TEHNET','kind':'wordpress'},
       'mytel.one':{'env_prefix':'WP_MYTEL','kind':'wordpress'}}

def site_credentials(site):
    cfg=SITES.get(site)
    if not cfg: return None
    p=cfg['env_prefix']
    url=os.environ.get(p+'_URL') or ('https://'+site if site in SITES else None)
    user=os.environ.get(p+'_USER')
    app=os.environ.get(p+'_APP_PASSWORD')
    return {'url':url,'user':user,'app_password':app} if user and app else None

def status():
    """Per-destination status for the publishing page. Honest states only."""
    rows=[]
    for name in ('YouTube','Instagram','Telegram','Facebook','LinkedIn'):
        rows.append({'destination':name,'state':'credential',
                     'detail':'OAuth حساب متصل نیست؛ فقط بسته dry-run ساخته می‌شود.'})
    for site,cfg in SITES.items():
        cred=site_credentials(site)
        rows.append({'destination':'Website · '+site,
                     'state':'ready' if cred else 'credential',
                     'detail':'WordPress REST تشخیص داده شد (wp-json فعال). Application Password در environment ثبت شده؛ پیش‌نویس قابل ساخت است.' if cred
                              else 'WordPress REST تشخیص داده شد. برای ساخت پیش‌نویس، '+cfg['env_prefix']+'_USER و '+cfg['env_prefix']+'_APP_PASSWORD در environment تنظیم شود.'})
    return rows

def wordpress_draft(site,title,content,status='draft'):
    """Create a WP post via REST. Returns dict with id/link. Network is called
    only when the user approved the publish job and credentials exist."""
    cred=site_credentials(site)
    if not cred:
        raise PermissionError('BLOCKED_BY_CREDENTIAL: Application Password برای '+site+' تنظیم نشده است.')
    url=cred['url'].rstrip('/')+'/wp-json/wp/v2/posts'
    body=json.dumps({'title':title,'content':content,'status':status}).encode()
    token=base64.b64encode(f"{cred['user']}:{cred['app_password']}".encode()).decode()
    req=urllib.request.Request(url,data=body,method='POST',headers={
        'Content-Type':'application/json','Authorization':'Basic '+token})
    with urllib.request.urlopen(req,timeout=30) as r:
        out=json.load(r)
    return {'id':out.get('id'),'link':out.get('link'),'status':out.get('status')}

def website_publish_handler(ctx):
    """Job handler: approved + credential-gated WordPress draft."""
    from jobs import DependencyMissing
    store=ctx.services['store']
    payload=ctx.payload
    if not payload.get('approved'):
        return {'waiting_approval':True,'question':'پیش‌نویس وردپرس برای '+payload.get('site','')+' ساخته شود؟'}
    item=store.get(payload['content_id'])
    if not item: raise ValueError('محتوا پیدا نشد.')
    if payload.get('revision')!=item['revision']:
        raise ValueError('نسخه تأییدشده با نسخه فعلی فرق دارد.')
    site=payload['site']
    try:
        res=wordpress_draft(site,item['title'],item['body'])
    except PermissionError as e:
        raise DependencyMissing(str(e))
    ctx.log('پیش‌نویس وردپرس ساخته شد: '+str(res.get('link')))
    return {'wordpress_id':res.get('id'),'link':res.get('link'),'site':site,'revision':payload['revision']}
