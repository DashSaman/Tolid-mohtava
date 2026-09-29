"""Optional external intelligence adapters: GA4, Google Keyword Planner,
SERP/competitor intelligence, Screaming Frog, Ruflo orchestration.

ALL are credential/runtime-gated with honest states. None owns core state;
all normalize into existing stores (analytics snapshots, performance records,
SEO scans). The panel must run identically when every one is unavailable.
"""
import json, os, re, sqlite3, subprocess, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from jobs import DependencyMissing

def now(): return datetime.now(timezone.utc).isoformat()

# ── GA4 (visitors after arrival) ──────────────────────────────
GA4_METRICS=('users','sessions','engaged_sessions','engagement_rate',
             'conversions','events','sessions_per_user')

def ga4_status():
    missing=[v for v in ('GA4_PROPERTY_ID','GA4_ACCESS_TOKEN') if not os.environ.get(v)]
    return {'provider':'ga4','state':'ready' if not missing else 'blocked_by_credential',
            'missing_env':missing,'detail':'GA4 Data API (users/sessions/engagement/conversions)'}

def ga4_fetch(property_id=None,token=None):
    """Real GA4 Data API runReport. Only called with credentials present."""
    pid=property_id or os.environ.get('GA4_PROPERTY_ID')
    tok=token or os.environ.get('GA4_ACCESS_TOKEN')
    if not pid or not tok:
        raise DependencyMissing('GA4: GA4_PROPERTY_ID / GA4_ACCESS_TOKEN تنظیم نشده (BLOCKED_BY_CREDENTIAL).')
    body=json.dumps({'dateRanges':[{'startDate':'7daysAgo','endDate':'today'}],
        'metrics':[{'name':m} for m in GA4_METRICS]}).encode()
    req=urllib.request.Request(f'https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport',
        data=body,headers={'Authorization':'Bearer '+tok,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r:
        out=json.load(r)
    row=(out.get('rows') or [{}])[0].get('metricValues',{})
    return {m:float(row.get(m,{}).get('value',0)) for m in GA4_METRICS}

# ── Keyword data (Google Ads / Keyword Planner as ONE provider) ─
class KeywordStore:
    def __init__(self,db_path):
        self.path=Path(db_path)
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS keyword_data(
                id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT NOT NULL,
                language TEXT, country TEXT, volume_monthly INTEGER,
                volume_range TEXT, competition TEXT, cpc_avg REAL,
                source TEXT NOT NULL, collected_at TEXT NOT NULL)''')
            c.execute('CREATE INDEX IF NOT EXISTS kw_idx ON keyword_data(keyword,source)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            with c: yield c
        finally: c.close()
    def add(self,keyword,language='fa',country='IR',volume_monthly=None,
            volume_range=None,competition=None,cpc_avg=None,source='manual'):
        if not (keyword or '').strip(): raise ValueError('کلمهٔ کلیدی خالی است.')
        with self.connect() as c:
            c.execute('''INSERT INTO keyword_data(keyword,language,country,volume_monthly,
                         volume_range,competition,cpc_avg,source,collected_at) VALUES(?,?,?,?,?,?,?,?,?)''',
                      (keyword.strip()[:120],language,country,volume_monthly,volume_range,
                       competition,cpc_avg,source,now()))
    def search(self,q,limit=20):
        with self.connect() as c:
            cur=c.execute("SELECT * FROM keyword_data WHERE keyword LIKE ? ORDER BY id DESC LIMIT ?",
                          ('%'+q+'%',limit))
            keys=[d[0] for d in cur.description]
            return [dict(zip(keys,r)) for r in cur.fetchall()]

def keyword_provider_status():
    missing=[v for v in ('GOOGLE_ADS_DEVELOPER_TOKEN','GOOGLE_ADS_CUSTOMER_ID','GOOGLE_ADS_REFRESH_TOKEN') if not os.environ.get(v)]
    return {'provider':'google_ads_keyword_planner',
            'state':'ready' if not missing else 'blocked_by_credential',
            'missing_env':missing,
            'detail':'Keyword Planner (حجم جست‌وجو/رقابت/CPC) — یکی از KeywordDataProviderها؛ ذخیره در keyword_data'}

# ── Search / competitor intelligence (SERP) ────────────────────
def search_intelligence_status():
    configured=[k for k in ('SERP_API_KEY','SERPAPI_API_KEY','SERP_PROVIDER') if os.environ.get(k)]
    if not configured:
        return {'provider':'search_intelligence','state':'unavailable',
                'detail':'هیچ SERP providerای تنظیم نشده (کلید اختیاری SERP_API_KEY). معماری آماده؛ بدون منبع معتبر، داده ساخته نمی‌شود.'}
    return {'provider':'search_intelligence','state':'ready','detail':'کلید SERP موجود است'}

# ── Screaming Frog (optional local SEO spider) ────────────────
SF_CONFIG={'win_default_paths':[
  r'C:\Program Files\Screaming Frog SEO Spider\ScreamingFrogSEOSpider.exe',
  r'C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpider.exe'],
  'env_binary':'SCREAMING_FROG_PATH','cli_flags':['--headless','--save-crawl','--export-tabs']}

def screaming_frog_status():
    path=os.environ.get(SF_CONFIG['env_binary']) or next(
        (p for p in SF_CONFIG['win_default_paths'] if Path(p).exists()),None)
    if path:
        return {'provider':'screaming_frog','state':'ready','binary':path,
                'detail':'نرمال‌سازی نتایج به مدل سئوی موجود؛ خزندهٔ داخلی fallback می‌ماند'}
    return {'provider':'screaming_frog','state':'unavailable',
            'detail':'نصب نیست. با SCREAMING_FROG_PATH معرفی شود؛ تا آن زمان خزندهٔ داخلی (تست‌شده) استفاده می‌شود. لایسنس/نصب با شماست.'}

def normalize_sf_export(csv_path):
    """Normalize a Screaming Frog 'Internal: All' CSV export into our page model."""
    import csv
    out=[]
    with open(csv_path,encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            out.append({'url':row.get('Address',''),
                        'status':int(row['Status code']) if (row.get('Status code') or '').isdigit() else None,
                        'title':row.get('Title 1') or None,
                        'meta_description':row.get('Meta Description 1') or None,
                        'h1_count':len([k for k in row if k.startswith('H1') and row[k]]),
                        'canonical':row.get('Canonical Link Element 1') or None,
                        'indexability':row.get('Indexability') or None})
    return out

# ── Ruflo (optional AI orchestration) ────────────────────────
RUFLO_PINNED_VERSION=os.environ.get('RUFLO_PINNED_VERSION','')  # e.g. '0.4.2'
RUFLO_ENV_HINT='RUFLO_ENDPOINT (مثلاً http://127.0.0.1:8117) و اختیاری RUFLO_PINNED_VERSION'

def ruflo_status():
    ep=os.environ.get('RUFLO_ENDPOINT')
    if not ep:
        return {'provider':'ruflo','state':'disabled',
                'detail':'اختیاری و خاموش. برای هم‌اردازی چند-عاملی (research/fact-check) فعال کنید: '+RUFLO_ENV_HINT}
    try:
        req=urllib.request.Request(ep+'/health' if not ep.endswith('/health') else ep,timeout=6)
        with urllib.request.urlopen(req,timeout=6) as r:
            body=json.load(r)
        ver=str(body.get('version') or '')
        if RUFLO_PINNED_VERSION and ver and ver!=RUFLO_PINNED_VERSION:
            return {'provider':'ruflo','state':'version_mismatch',
                    'detail':f'نسخهٔ {ver} != پین {RUFLO_PINNED_VERSION}؛ همان نسخهٔ تست‌شده لازم است'}
        return {'provider':'ruflo','state':'available','version':ver or 'unknown',
                'detail':'آماده برای وظایف هم‌اردازی؛ صف/تأیید/رسانه مالکیتشان همچنان Core است'}
    except Exception as e:
        return {'provider':'ruflo','state':'error','detail':str(e)[:140]}

def all_optional_integrations():
    return {'ga4':ga4_status(),'keyword_planner':keyword_provider_status(),
            'search_intelligence':search_intelligence_status(),
            'screaming_frog':screaming_frog_status(),'ruflo':ruflo_status()}
