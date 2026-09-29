"""Production-ready external provider foundations (credential-gated).

OAuth foundation: one reusable flow (state+callback+scope validation+refresh)
for YouTube/Meta/LinkedIn. WordPress/Telegram/GSC/GA4/Ads/Gemini adapters use
env credentials per project architecture. All external actions require the
existing approval semantics; DRAFT/read is the default.
"""
import base64, hashlib, json, os, secrets, sqlite3, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from jobs import DependencyMissing

def now(): return datetime.now(timezone.utc).isoformat()

# ── OAuth provider registry ───────────────────────────────────
OAUTH_PROVIDERS={
 'youtube':{
   'auth_url':'https://accounts.google.com/o/oauth2/v2/auth',
   'token_url':'https://oauth2.googleapis.com/token',
   'client_env':('YOUTUBE_CLIENT_ID','YOUTUBE_CLIENT_SECRET'),
   'scopes':['https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube.readonly'],
   'redirect_env':'OAUTH_REDIRECT_BASE'},   # e.g. http://127.0.0.1:8767
 'instagram':{
   'auth_url':'https://www.facebook.com/v19.0/dialog/oauth',
   'token_url':'https://graph.facebook.com/v19.0/oauth/access_token',
   'client_env':('META_APP_ID','META_APP_SECRET'),
   'scopes':['instagram_basic','instagram_content_publish'],
   'redirect_env':'OAUTH_REDIRECT_BASE'},
 'facebook':{
   'auth_url':'https://www.facebook.com/v19.0/dialog/oauth',
   'token_url':'https://graph.facebook.com/v19.0/oauth/access_token',
   'client_env':('META_APP_ID','META_APP_SECRET'),
   'scopes':['pages_manage_posts','pages_read_engagement'],
   'redirect_env':'OAUTH_REDIRECT_BASE'},
 'linkedin':{
   'auth_url':'https://www.linkedin.com/oauth/v2/authorization',
   'token_url':'https://www.linkedin.com/oauth/v2/accessToken',
   'client_env':('LINKEDIN_CLIENT_ID','LINKEDIN_CLIENT_SECRET'),
   'scopes':['w_member_social','r_member_social'],
   'redirect_env':'OAUTH_REDIRECT_BASE'},
}

class OAuthStore:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS oauth_states(
                state TEXT PRIMARY KEY, provider TEXT NOT NULL, created_at TEXT, used INTEGER DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS oauth_tokens(
                provider TEXT PRIMARY KEY, access_token TEXT NOT NULL,
                refresh_token TEXT, expires_at TEXT, scope TEXT, updated_at TEXT)''')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def new_state(self,provider):
        st=secrets.token_urlsafe(24)
        with self.connect() as c:
            c.execute('INSERT INTO oauth_states VALUES(?,?,?,0)',(st,provider,now()))
        return st
    def pop_state(self,state):
        with self.connect() as c:
            r=c.execute('SELECT provider FROM oauth_states WHERE state=? AND used=0',(state,)).fetchone()
            if r: c.execute('UPDATE oauth_states SET used=1 WHERE state=?',(state,))
        return r[0] if r else None
    def save_token(self,provider,access,refresh='',scope='',expires_in=3600):
        with self.connect() as c:
            c.execute('''INSERT INTO oauth_tokens VALUES(?,?,?,?,?,?)
                         ON CONFLICT(provider) DO UPDATE SET access_token=?,refresh_token=?,
                         expires_at=?,scope=?,updated_at=?''',
                      (provider,access,refresh,
                       (datetime.fromtimestamp(time.time()+expires_in,timezone.utc).isoformat()),
                       scope,now(),access,refresh,
                       (datetime.fromtimestamp(time.time()+expires_in,timezone.utc).isoformat()),scope,now()))
    def get_token(self,provider):
        with self.connect() as c:
            r=c.execute('SELECT access_token,expires_at FROM oauth_tokens WHERE provider=?',(provider,)).fetchone()
        if not r: return None
        tok,exp=r
        if exp and exp<now(): return None   # expired
        return tok

def oauth_status(provider):
    cfg=OAUTH_PROVIDERS[provider]
    missing=[v for v in cfg['client_env'] if not os.environ.get(v)]
    return {'provider':provider,'state':'ready' if not missing else 'blocked_by_credential',
            'missing_env':missing,'scopes':' '.join(cfg['scopes']),
            'auth_url':cfg['auth_url'],'detail':'OAuth مرورگری آماده'}

def oauth_start_url(provider,store,redirect_base=None):
    cfg=OAUTH_PROVIDERS[provider]
    cid=os.environ.get(cfg['client_env'][0])
    if not cid: raise DependencyMissing(f'{provider}: {cfg["client_env"][0]} تنظیم نشده (BLOCKED_BY_CREDENTIAL).')
    base=redirect_base or os.environ.get(cfg['redirect_env']) or 'http://127.0.0.1:8767'
    redirect=base.rstrip('/')+'/oauth/callback'
    state=store.new_state(provider)
    q=urllib.parse.urlencode({'client_id':cid,'redirect_uri':redirect,'response_type':'code',
        'scope':' '.join(cfg['scopes']),'state':state,'access_type':'offline','prompt':'consent'})
    return cfg['auth_url']+'?'+q

def oauth_callback(provider,store,code,state,redirect_base=None):
    cfg=OAUTH_PROVIDERS[provider]
    if not state or store.pop_state(state)!=provider:
        raise PermissionError('state نامعتبر است (CSRF).')
    cid=os.environ.get(cfg['client_env'][0]); sec=os.environ.get(cfg['client_env'][1])
    if not cid or not sec: raise DependencyMissing(f'{provider}: متغیرهای client تنظیم نشده‌اند.')
    base=redirect_base or os.environ.get(cfg['redirect_env']) or 'http://127.0.0.1:8767'
    data=urllib.parse.urlencode({'code':code,'client_id':cid,'client_secret':sec,
        'redirect_uri':base.rstrip('/')+'/oauth/callback','grant_type':'authorization_code'}).encode()
    req=urllib.request.Request(cfg['token_url'],data=data,method='POST')
    with urllib.request.urlopen(req,timeout=30) as r:
        out=json.load(r)
    store.save_token(provider,out.get('access_token',''),out.get('refresh_token',''),
                     out.get('scope',''),int(out.get('expires_in',3600)))
    return {'ok':True,'provider':provider,'scope':out.get('scope','')}

# ── Gemini image generation (real API, gated) ─────────────────
def gemini_image(prompt,out_path):
    key=os.environ.get('GOOGLE_AI_API_KEY')
    if not key: raise DependencyMissing('Gemini: GOOGLE_AI_API_KEY تنظیم نشده (BLOCKED_BY_CREDENTIAL).')
    model=os.environ.get('GEMINI_IMAGE_MODEL','gemini-2.0-flash-exp-image-generation')
    body=json.dumps({'contents':[{'parts':[{'text':prompt}]}],
        'generationConfig':{'responseModalities':['IMAGE','TEXT']}}).encode()
    req=urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}',
        data=body,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180) as r:
        out=json.load(r)
    import base64
    for part in (out.get('candidates') or [{}])[0].get('content',{}).get('parts',[]):
        if 'inlineData' in part:
            Path(out_path).parent.mkdir(parents=True,exist_ok=True)
            open(out_path,'wb').write(base64.b64decode(part['inlineData']['data']))
            return out_path
    raise RuntimeError('پاسخ Gemini تصویری نداشت.')

def gemini_image_handler(ctx):
    services=ctx.services
    prompt=ctx.payload.get('prompt') or ''
    content_id=ctx.payload.get('content_id')
    if not prompt.strip(): raise ValueError('پرامپت تصویر خالی است.')
    ctx.log('تولید تصویر با Gemini')
    ctx.progress(30)
    rd=services['renders']
    out=rd.root/f'gemini/{uuid.uuid4().hex[:8]}.png'
    gemini_image(prompt,str(out))
    ctx.progress(85)
    row=rd.add(content_id or 'unattached',f'GEMINI V{1+sum(1 for r in rd.list(content_id) if r.get("kind")=="gemini") if content_id else 1}',
               'gemini',str(out),out.stat().st_size,0,None,'gemini-image',ctx.id)
    return {'render_id':row['id'],'path':row['path']}

# ── GSC + Google Ads adapters (request builders, credential-gated) ──
def gsc_search_analytics(site_url,start,end,token=None):
    tok=token or os.environ.get('GSC_CREDENTIALS')  # service-account JSON path handled upstream
    if not tok: raise DependencyMissing('GSC: GSC_CREDENTIALS تنظیم نشده (BLOCKED_BY_CREDENTIAL).')
    body=json.dumps({'startDate':start,'endDate':end,'dimensions':['query','page'],
                     'rowLimit':250}).encode()
    req=urllib.request.Request(
        f'https://searchconsole.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(site_url, safe="")}/searchAnalytics/query',
        data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+tok})
    with urllib.request.urlopen(req,timeout=45) as r:
        return json.load(r)

def ads_config_status():
    need=('GOOGLE_ADS_DEVELOPER_TOKEN','GOOGLE_ADS_CUSTOMER_ID','GOOGLE_ADS_CLIENT_ID','GOOGLE_ADS_CLIENT_SECRET','GOOGLE_ADS_REFRESH_TOKEN')
    missing=[v for v in need if not os.environ.get(v)]
    return {'ready':not missing,'missing':missing,
            'library':'google-ads==25.1.0 (pinned)'}

def ads_keyword_ideas(keyword,language_code='fa',country_code='IR',max_rows=20):
    """Real Google Ads API KeywordIdeasQuery via official client (pinned 25.1.0).
    Requires developer token + OAuth client + refresh token (test-account ok)."""
    st=ads_config_status()
    if not st['ready']:
        raise DependencyMissing('Google Ads: '+ '، '.join(st['missing'])+' تنظیم نشده (BLOCKED_BY_CREDENTIAL).')
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    cfg={'developer_token':os.environ['GOOGLE_ADS_DEVELOPER_TOKEN'],
         'client_id':os.environ['GOOGLE_ADS_CLIENT_ID'],
         'client_secret':os.environ['GOOGLE_ADS_CLIENT_SECRET'],
         'refresh_token':os.environ['GOOGLE_ADS_REFRESH_TOKEN'],
         'login_customer_id':os.environ.get('GOOGLE_ADS_LOGIN_CUSTOMER_ID',''),
         'use_proto_plus':True}
    client=GoogleAdsClient.load_from_dict(cfg)
    cid=os.environ['GOOGLE_ADS_CUSTOMER_ID'].replace('-','')
    ks=client.get_service('KeywordPlanIdeaService')
    req=client.get_type('GenerateKeywordIdeasRequest')
    req.customer_id=cid
    req.keyword_seed.keywords.append(keyword)
    req.language=client.get_service('GoogleAdsService').language_constant_path(language_code=='fa' and 1007 or 1000)
    geo=client.get_service('GeoTargetConstantService')
    req.geo_target_constants.append(geo.geo_target_constant_path('_country_code' and 2724 if country_code=='IR' else 2840))  # IR=2724, US=2840
    req.page_size=max_rows
    try:
        resp=ks.generate_keyword_ideas(request=req)
    except GoogleAdsException as e:
        raise RuntimeError('Google Ads API: '+str(e.failure).split(chr(10))[0][:200])
    out=[]
    for idea in resp:
        m=idea.keyword_idea_metrics or {}
        out.append({'keyword':idea.text,
                    'avg_monthly_searches':getattr(m,'avg_monthly_searches',None),
                    'competition':str(getattr(m,'competition',None)).split('.')[-1] if m else None,
                    'low_top_bid':getattr(m,'low_top_of_page_bid_micros',None),
                    'high_top_bid':getattr(m,'high_top_of_page_bid_micros',None)})
    return out

import uuid
