"""Content intelligence engines: dedup/cannibalization detection, evergreen
refresh recommendations, and the unified ContentOptimizationEngine
(SEO/AEO/GEO/AI-Search-readiness in ONE engine — no duplicated machinery).
"""
import re, json
from datetime import datetime, timezone
from difflib import SequenceMatcher
import knowledge as kb_mod

def now(): return datetime.now(timezone.utc).isoformat()

# ── 13. dedup / cannibalization ───────────────────────────────
VERDICT_FA={'SAFE_NEW_TOPIC':'موضوع جدید امن','UPDATE_EXISTING_CONTENT':'به‌روزرسانی محتوای موجود',
 'MERGE_RECOMMENDED':'ادغام پیشنهاد می‌شود','POTENTIAL_CANNIBALIZATION':'احتمال کنیبالیزیشن',
 'DUPLICATE':'تکراری'}

def _norm(t): return re.sub(r'[\s‌.,!?؟،؛:«»\-]+','',(t or '').lower())

def check_topic(existing,kb,new_title,new_keyword=''):
    """existing: list of {id,title,platform}; returns verdict + evidence."""
    nt=_norm(new_title); nk=(new_keyword or '').strip().lower()
    best=None
    for x in existing:
        st=SequenceMatcher(None,nt,_norm(x['title'])).ratio()
        kw_hit=bool(nk) and nk in (x['title'] or '').lower()
        score=st+(0.35 if kw_hit else 0)
        if best is None or score>best['score']:
            best={'score':round(score,2),'sim':round(st,2),'kw_overlap':kw_hit,'item':x}
    hits=kb.search(new_title,limit=3) if kb else []
    kb_sim=max((SequenceMatcher(None,nt,_norm(h['title'])).ratio() for h in hits),default=0.0)
    if not best or best['score']<0.45 and kb_sim<0.45:
        return {'verdict':'SAFE_NEW_TOPIC','evidence':{'best':best,'kb_hits':len(hits)},'note':'شباهت معناداری با محتوای موجود یافت نشد'}
    if best['sim']>=0.9 or kb_sim>=0.92:
        v='DUPLICATE'
    elif best['score']>=0.75:
        v='MERGE_RECOMMENDED'
    elif best['kw_overlap'] and best['score']>=0.5:
        v='POTENTIAL_CANNIBALIZATION'
    else:
        v='UPDATE_EXISTING_CONTENT'
    return {'verdict':v,'evidence':best,'kb_hits':kb_sim,'note':VERDICT_FA[v]}

# ── 14. evergreen refresh ─────────────────────────────────────
def refresh_candidates(items,perf=None,seo_last_issues=0):
    """Rank existing content for refresh: age + stale stage + perf decline
    signals when real data exists. No GSC data => age/coverage-only reasoning,
    honestly labeled."""
    out=[]
    for x in items:
        reasons=[]
        try:
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(x['updated'])).days
        except Exception:
            age=0
        if age>=180: reasons.append(f'قدمت {age} روز')
        if x.get('stage') in ('SEO','آماده بررسی') and x.get('publish_status')=='approved': reasons.append('منتشرشده بدون به‌روزرسانی سئو')
        p=[r for r in (perf or []) if r['content_id']==x['id']]
        if p and p[0].get('metrics',{}).get('ctr') is not None:
            m=p[0]['metrics']
            if float(m.get('impressions') or 0)>500 and float(m.get('ctr') or 0)<0.03:
                reasons.append('نمایش بالا/CTR پایین (دادهٔ واقعی)')
        if reasons:
            out.append({'content_id':x['id'],'title':x['title'],'reasons':reasons,
                        'priority':'high' if any('CTR' in r for r in reasons) or age>=365 else 'normal',
                        'suggested_changes':['به‌روزرسانی نسخه‌ها/دستورات','تازه‌سازی نکات و اسکرین‌شات‌ها','بازبینی عنوان و متا']})
    out.sort(key=lambda r:0 if r['priority']=='high' else 1)
    return out

# ── 16. unified ContentOptimizationEngine (SEO/AEO/GEO/AI) ────
AEO_CHECKS=('پاسخ مستقیم و روشن در ابتدای محتوا','بخش پرسش‌های متداول (FAQ)')
GEO_CHECKS=('ارجاع به منابع معتبر و به‌روز','وضوح موجودیت/برند (چه کسی، دربارهٔ چه)')
AI_CHECKS=('بخش‌های نقل‌قول‌پذیر واقعی','تیترهای ساختاریافته و مشخص','به‌روز بودن نسخه‌ها/تاریخ‌ها')

def optimize_content(text,title='',has_faq=False,has_schema=False):
    """One engine, four dimensions. Returns per-dimension checklist with pass/fail
    and a concrete suggestion — usable for article drafts before approval."""
    t=(text or ''); tl=t.lower()
    res={'dimensions':{}}
    def dim(name,checks,extra=None):
        rows=[{'check':c,'ok':cond} for c,cond in checks]
        d={'checks':rows,'score':round(sum(1 for r in rows if r['ok'])/max(1,len(rows)),2)}
        if extra: d.update(extra)
        res['dimensions'][name]=d
    # SEO
    dim('SEO',[
        ('عنوان حاوی کلمهٔ کلیدی', bool(title and len(title)>10)),
        ('تیترهای H2/H3 ساختاریافته', t.count('\n##')>=2 or len(re.findall(r'^#{1,3}\s',t,re.M))>=2),
        ('طول مناسب (>=300 کلمه)', len(t.split())>=300),
        ('لینک داخلی پیشنهادی', 'لینک' in tl or 'http' in t),
    ],{'schema_opportunity':not has_schema})
    # AEO
    dim('AEO',[
        ('پاسخ مستقیم در ۱۵۰ کلمهٔ اول', len(t.split()[:150])>=40 and any(k in tl[:800] for k in ('به طور خلاصه','خلاصه','یعنی','به این صورت','مراحل'))),
        ('بخش FAQ', has_faq or 'سوالات متداول' in tl or 'پرسش' in tl),
    ])
    # GEO
    dim('GEO',[
        ('ارجاع به منابع', 'http' in t or 'منبع' in tl),
        ('ذکر نسخه/تاریخ', bool(re.search(r'(نسخه|v?\d+\.\d+|۲۰۲\d|20\d\d)',t))),
    ])
    # AI-Search readiness
    dim('AI_SEARCH',[
        ('بخش‌های واقعی و نقل‌قول‌پذیر', len(t.split())>=200),
        ('ساختار پاراگراف/فهرست', ('\n-' in t or '\n*' in t or len(re.findall(r'^\d+\.',t,re.M))>=3)),
    ])
    weak=[k for k,d in res['dimensions'].items() if d['score']<0.5]
    res['summary']='ضعف در: '+', '.join(weak) if weak else 'همهٔ ابعاد قابل‌قبول'
    return res
