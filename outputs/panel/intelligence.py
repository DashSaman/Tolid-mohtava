"""Content Matrix + Weekly Planner, SEO fix-proposal workflow, Smart Shorts V2.

Weekly planning is AI-assisted but grounded in REAL local evidence: published
projects, performance records, SEO scan findings. Every recommendation carries
WHY. SEO proposals explain each detected issue with a concrete fix; applying
site changes stays approval-gated. Shorts V2 ranks candidates by multi-signal
scoring and prefers DIFFERENT angles.
"""
import json, re, uuid
from datetime import datetime, timezone
import ai
from ai import extract_json

def now(): return datetime.now(timezone.utc).isoformat()

PILLARS_TN=['میکروتیک','شبکه','VoIP','VPN/تونل','فریلنسینگ میکروتیک','Issabel/FreePBX/SIP']
PILLARS_MYTEL=['VoIP','Issabel','FreePBX','SIP','CRM تلفنی','مرکز تماس']

def pillar_of(text,pillars):
    t=(text or '').lower()
    return next((p for p in pillars if p.split('/')[0].lower() in t),'')

# ── Content Matrix + Weekly Planner ────────────────────────────
def weekly_plan_handler(ctx):
    store=ctx.services['store']; ana=ctx.services['analytics']
    brand=ctx.payload.get('brand') or 'tehran-network'
    pillars=PILLARS_TN if brand=='tehran-network' else PILLARS_MYTEL
    items=store.list(brand)
    perf=ana.performance(brand=brand)
    seo=ctx.services['seo'].scans('tehnet.ir' if brand=='tehran-network' else 'mytel.one',limit=1)
    seo_issues=seo[0]['issues'] if seo else 0
    pillar_stats={}
    for p in perf:
        pil=p.get('pillar') or pillar_of((p.get('topic') or '')+(p.get('title') or ''),pillars)
        if not pil: continue
        m=p.get('metrics') or {}
        st=pillar_stats.setdefault(pil,{'n':0,'views':0,'engagement':0})
        st['n']+=1; st['views']+=float(m.get('views') or 0); st['engagement']+=float(m.get('engagement') or 0)
    evidence={
      'published_topics':[{'title':x['title'],'stage':x['stage']} for x in items[:12]],
      'pillar_performance':pillar_stats,
      'sample_size':len(perf),
      'seo_issues':seo_issues,
      'pillars':pillars,
    }
    ctx.log(f"شواهد محلی: {len(items)} پرونده، {len(perf)} رکورد عملکرد، {seo_issues} مشکل سئو")
    messages=[
     {'role':'system','content':f"""تو برنامه‌ریز محتوای هفتگی برندهای فنی فارسی هستی. فقط JSON بده.
هر پیشنهاد باید «چرا»ی مبتنی بر شواهد داده‌شده داشته باشد — لیست تصادفی ممنوع.
اگر دادهٔ عملکرد صفر است، صادقانه بنویس پیشنهاد بر اساس شکاف پوشش و اهمیت کسب‌وکار است (confidence پایین).
{('قواعد برند: تهران نتورک برند اصلی است؛ VoIP اهمیت راهبردی دارد چون MyTel را پشتیبانی می‌کند؛ محتوای VPN رها نشود.') if brand=='tehran-network' else ('MyTel: تمرکز VoIP/Issabel/FreePBX/SIP/CRM تلفنی؛ محتوای آموزشی و تجاری.')}"""},
     {'role':'user','content':('برنامهٔ محتوای هفتهٔ آیندهٔ '+('تهران نتورک' if brand=='tehran-network' else 'MyTel')+' را بساز (۳ تا ۵ پیشنهاد).\n\n'
      'شواهد محلی (JSON):\n'+json.dumps(evidence,ensure_ascii=False)[:3500]+'\n\n'
      'JSON:\n{"plan":[{"title":"عنوان پیشنهادی","pillar":"ستون محتوایی","platform":"پلتفرم هدف","content_type":"long یا short یا article","why":"دلیل انتخاب با ارجاع به شواهد","opportunity":"فرصت جست‌وجو/شکاف","business_relevance":"ارزش کسب‌وکار","confidence":0.0تا1.0}]}')}]
    ctx.progress(30)
    out=ai.chat(ctx.services['ai'],'analysis',messages,max_tokens=1600)
    data=extract_json(out['content'])
    if data is None:
        raise ValueError('خروجی مدل قابل‌خواندن نبود؛ دوباره تلاش کنید.')
    plan=data.get('plan') or []
    for p in plan:
        p['sample_size']=len(perf)
    return {'brand':brand,'plan':plan,'evidence_summary':{'projects':len(items),'performance_records':len(perf),'seo_issues':seo_issues},'provider':out['provider']}

# ── SEO proposals: detect → explain → propose ─────────────────
def _rule(code):
    R={
     'missing_meta':('توضیح متا ندارد','برای صفحه توضیح متا (۱۵۵ نویسه) بنویسید که کلمهٔ کلیدی اصلی و وعدهٔ صفحه را داشته باشد؛ در وردپرس با سئوپلاگین یا فیلد excerpt تنظیم می‌شود.'),
     'missing_canonical':('canonical ندارد','برای جلوگیری از محتوای تکراری، canonical به نشانی canonical صفحه اضافه شود.'),
     'h1_issue':('ساختار H1 نامناسب','دقیقاً یک H1 در صفحه؛ تیترهای بعدی H2/H3.'),
     'sitemap_missing':('ریشه‌یابی کامل 2026-09-28 (بدون تغییر روی سایت): هیچ پلاگین سئویی نصب نیست (WP REST فقط WooCommerce/Jetpack را نشان می‌دهد)؛ ریدایرکت 301 از sitemap.xml به wp-sitemap.xml را خودِ وردپرس صادر می‌کند (X-Redirect-By: WordPress) ولی مقصد 404 است؛ یعنی sitemap هستهٔ وردپرس غیرفعال شده است (معمولاً با فیلتر wp_sitemaps_enabled در کد قالب/mu-plugin/snippet، یا تیک Discourage search engines در تنظیمات خواندن) و robots.txt هم خط Sitemap ندارد',
                        'گام‌های پیشنهادی (بدون نصب پلاگین جدید، با تأیید شما در wp-admin): (۱) تنظیمات ← خواندن ← تیک «جلوگیری از ایندکس موتورهای جست‌وجو» برداشته شود؛ (۲) اگر snippet/mu-plugin/قالب فیلتر wp_sitemaps_enabled یا wp_sitemaps_remove_rewrite_rules دارد، حذف/غیرفعال شود؛ (۳) تنظیمات ← پیوندهای یکتا ← ذخیره (فلوش rewrite)؛ (۴) تأیید wp-sitemap.xml = 200؛ (۵) افزودن خط «Sitemap: https://tehnet.ir/wp-sitemap.xml» به robots.txt؛ (۶) ریدایرکت موجود بی‌ضرر می‌شود ولی در صورت تمایل حذف گردد؛ (۷) در پنل، «اجرای اسکن» دوباره — بهبود در تاریخچهٔ اسکن قابل راستی‌آزمایی است.'),
    }
    issue,fix=R[code]
    return {'issue':issue,'fix':fix}
def build_seo_proposals(pages,summary):
    """Turn scan findings into actionable, explained proposals (no site change without approval)."""
    props=[]
    for p in pages:
        u=p.get('url','')
        if p.get('status')!=200:
            props.append({'page':u,'code':'http_error','issue':f"وضعیت HTTP {p.get('status')}",
                          'fix':'دسترس‌پذیری صفحه بررسی شود (404/500).'})
        if not p.get('title'): props.append({'page':u,'code':'missing_title','issue':'عنوان صفحه ندارد','fix':'تگ title یکتا و توصیفی اضافه شود.'})
        if not p.get('meta_description'):
            props.append({'page':u,'code':'missing_meta','kind':'issue',**_rule('missing_meta')})
        if not p.get('canonical'):
            props.append({'page':u,'code':'missing_canonical','kind':'issue',**_rule('missing_canonical')})
        if p.get('h1_count',0)!=1:
            props.append({'page':u,'code':'h1_issue','kind':'issue',**_rule('h1_issue')})
        if p.get('images_missing_alt'):
            props.append({'page':u,'code':'missing_alt','issue':f"{p['images_missing_alt']} تصویر بدون alt",
                          'fix':'متن جایگزین توصیفی برای تصاویر اضافه شود.'})
    for d in (summary.get('duplicate_titles') or []):
        props.append({'page':d['pages'][0],'code':'duplicate_title','issue':f"عنوان تکراری در {len(d['pages'])} صفحه",
                      'fix':'عنوان یکتا برای هر صفحه.'})
    for d in (summary.get('duplicate_descriptions') or []):
        props.append({'page':d['pages'][0],'code':'duplicate_description','issue':f"توضیح متای تکراری در {len(d['pages'])} صفحه",
                      'fix':'توضیح متای یکتا برای هر صفحه.'})
    if (summary.get('infra') or {}).get('sitemap') not in ('ok',):
        props.append({'page':summary.get('site',''),'code':'sitemap_missing','kind':'infra',**_rule('sitemap_missing')})
    for b in (summary.get('broken_links') or []):
        props.append({'page':b['url'],'code':'broken_link','issue':f"لینک خراب ({b['status']})",
                      'fix':'اصلاح یا حذف لینک؛ ریدایرکت 301 برای نشانی تغییرکرده.'})
    return props

def seo_proposals_handler(ctx):
    seo=ctx.services['seo']
    site=ctx.payload.get('site') or 'tehnet.ir'
    scans=seo.scans(site,limit=1)
    if not scans: raise ValueError('اول یک اسکن سئو اجرا کنید.')
    pages=seo.scan_pages(scans[0]['id'])
    summary=json.loads(scans[0]['summary'])
    props=build_seo_proposals(pages,summary)
    pid=uuid.uuid4().hex
    ctx.services['analytics'].add_proposal(None,site,'SEO_AUDIT',
        f"{len(props)} مورد قابل‌اقدام از اسکن {site}",
        'پیشنهادها آماده است؛ اعمال تغییر روی سایت نیازمند تأیید شما و (برای وردپرس) Credential است.',
        {'proposals':props[:40]},1,0.9)
    ctx.log(f"{len(props)} پیشنهاد ساخته شد؛ در مرکز تأیید قابل مشاهده است.")
    return {'proposal_count':len(props),'site':site,'first_three':[p['issue'] for p in props[:3]]}

# ── Smart Shorts V2 ────────────────────────────────────────────
def rank_short_candidates(segments,transcript_text=''):
    """Multi-signal ranking; force angle diversity, avoid near-duplicates."""
    if not segments: return []
    scored=[]
    norm=lambda t:re.sub(r'[\s‌.,!?؟،؛:«»\-]+','',t or '')
    for i,s in enumerate(segments):
        text=(s.get('text') or '').strip()
        if len(text)<35: continue
        score=0.0
        hooks=('چطور','چگونه','اشتباه','راه‌حل','نکته','مهم','آسان','سریع','چرا','بهترین','بدون')
        if any(h in text for h in hooks): score+=30
        if text.endswith(('.','!','؟')): score+=15
        score+=min(25,len(text)/8)
        if i==0 or i==len(segments)-1: score+=8
        angle='how-to' if any(h in text for h in ('چطور','چگونه','مرحله')) else \
              'mistake' if 'اشتباه' in text else \
              'insight' if any(h in text for h in ('نکته','چرا','مهم')) else \
              'quick' if any(h in text for h in ('سریع','آسان')) else 'general'
        scored.append({'start':s['start'],'end':s['end'],'text':text,'score':score,'angle':angle,
                       'standalone':bool(text.endswith(('.','!','؟')) and len(text)>50)})
    # pick diverse angles greedily
    by_angle={}
    for c in sorted(scored,key=lambda c:-c['score']):
        by_angle.setdefault(c['angle'],[]).append(c)
    picks=[];used=[]
    order=sorted(by_angle.values(),key=lambda lst:-lst[0]['score'])
    while len(picks)<3:
        added=False
        for lst in order:
            if not lst: continue
            c=lst.pop(0)
            if any(abs(c['start']-u['start'])<25 for u in used): continue
            c['duration']=round(c['end']-c['start'],1)
            c['hook']=c['text'][:60]
            c['why']=f"زاویهٔ {c['angle']} · امتیاز {int(c['score'])} · جملهٔ {'کامل' if c['standalone'] else 'ناقص'}"
            picks.append(c);used.append(c);added=True
            if len(picks)>=3: break
        if not added: break
    return picks

def shorts_v2_handler(ctx):
    services=ctx.services
    mid=ctx.payload.get('media_id')
    m=services['media'].get(mid)
    if not m: raise ValueError('رسانه پیدا نشد.')
    t=services['transcripts'].get(mid)
    if not t or not t['segments']: raise ValueError('این رسانه transcript ندارد؛ اول تبدیل گفتار را اجرا کنید.')
    picks=rank_short_candidates(t['segments'],t['text'])
    if not picks: raise ValueError('قطعهٔ مناسبی برای Short پیدا نشد.')
    ctx.log(f"{len(picks)} کاندیدای رتبه‌بندی‌شده (زاویه‌های متفاوت) آماده تأیید است.")
    return {'candidates':picks,'note':'قبل از رندر، کاندیداها را در تب Shorts تأیید/رد/تنظیم کنید.'}
