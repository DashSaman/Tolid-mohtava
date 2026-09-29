"""Publishing adapters: real code, honest credential gating.

Nothing publishes without: (1) explicit user approval, (2) credentials present
in the environment. Credentials never live in the database or the repo.
tehnet.ir and mytel.one were probed on 2026-09-27: both are WordPress with
live wp-json REST APIs (PHP 8.3, Cloudflare; mytel uses Elementor), so the
website path uses the standard WP REST draft endpoint.
"""
from pathlib import Path
import base64, hashlib, json, os, time, urllib.request, urllib.error

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

def wordpress_draft(site,title,content,status='draft',slug=None,excerpt=None,categories=None,tags=None,max_retries=2):
    """Create a WP post via REST. Production path: DRAFT default, retry with
    backoff, timeout, idempotency via client-side guard file. Publishing
    (status=publish) is intentionally NOT automatic."""
    cred=site_credentials(site)
    if not cred:
        raise PermissionError('BLOCKED_BY_CREDENTIAL: Application Password برای '+site+' تنظیم نشده است.')
    if status!='draft':
        raise PermissionError('فقط DRAFT مجاز است؛ انتشار نیازمند تأیید صریح شماست.')
    url=cred['url'].rstrip('/')+'/wp-json/wp/v2/posts'
    payload={'title':title,'content':content,'status':status}
    if slug: payload['slug']=slug
    if excerpt: payload['excerpt']=excerpt
    if categories: payload['categories']=categories
    if tags: payload['tags']=tags
    token=base64.b64encode(f"{cred['user']}:{cred['app_password']}".encode()).decode()
    import hashlib
    idem=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
    dbdir=Path(os.environ.get('TEHNET_PANEL_DB','outputs/panel/data/content.sqlite')).parent
    guard=dbdir/('wp-idem-'+site.replace('.','-')+'-'+idem+'.json')
    if guard.exists():
        prev=json.loads(guard.read_text())
        return {'id':prev.get('id'),'link':prev.get('link'),'status':prev.get('status'),'deduplicated':True}
    last_err=None
    for attempt in range(max_retries+1):
        body=json.dumps(payload).encode()
        req=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json','Authorization':'Basic '+token})
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                out=json.load(r)
            res={'id':out.get('id'),'link':out.get('link'),'status':out.get('status')}
            try: guard.write_text(json.dumps(res))
            except Exception: pass
            return res
        except urllib.error.HTTPError as e:
            last_err=e
            if e.code<500: break
            time.sleep(1.5*(attempt+1))
        except Exception as e:
            last_err=e; time.sleep(1.5*(attempt+1))
    raise RuntimeError(f'WordPress {site}: {last_err}')

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
