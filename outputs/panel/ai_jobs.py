"""Executable AI jobs on the existing worker: research, verification, script,
hooks, title packages, social variants, article/SEO, pinned comment.

Every job persists its output, logs progress, fails honestly (no invented
success), and sources are checked with REAL HTTP requests — never fabricated.
"""
import json, re, uuid, urllib.request
from datetime import datetime, timezone
from jobs import DependencyMissing, JobCancelled
import ai
from ai import STATUS_KIND_FA, extract_json, validate_schema
import skill_router

def now(): return datetime.now(timezone.utc).isoformat()

MARKERS=['[FACE CAM]','[SCREEN RECORD]','[B-ROLL]','[GRAPHIC]','[SPONSOR]','[CTA]','[SHORT CANDIDATE]']
CTA_RULES=('قواعد CTA:\n'
 '- محتوای VoIP/تلفنی (Issabel، FreePBX، SIP، CRM تلفنی): معرفی زمینه‌ای MyTel / mytel.one — نه لوگوی دائمی و نه متن ثابت اسپانسری.\n'
 '- محتوای VPN/تونل/میکروتیک عمومی: دعوت به اشتراک، کامنت و سوال؛ گاهی tehnet.ir برای فایل/کانفیگ.\n'
 '- مقاله/فایل/کانفیگ: tehnet.ir.\n'
 '- مشاوره/پیاده‌سازی: دعوت نرم به تماس، فقط وقتی مناسب باشد.\n'
 '- برای محتوای VPN در حد «معرفی موردی سرویس» آزادی هست؛ اما هرگز مالکیت یا ارتباط رسمی PVNetwork با تهران نتورک را ذکر یا استنباط نکن.')
BRAND_RULES=('قواعد برند:\n'
 '- تهران نتورک برند اصلی آموزشی است؛ ستون‌ها: میکروتیک، VoIP، Issabel، FreePBX، SIP، شبکه، VPN/تونل، پیاده‌سازی عملی میکروتیک. محتوای VPN به‌خاطر مخاطب موجود رها نشود.\n'
 '- VoIP اهمیت راهبردی دارد چون پشتیبان MyTel است؛ MyTel فقط زمینه‌ای ظاهر شود.\n'
 '- لحن: محاوره‌ای، روان، مستقیم، عملی؛ نه کودکانه، نه شرکتی، نه رباتیک.\n'
 '- مخاطب: متخصصان IT/شبکه + علاقه‌مندان تازه‌کار.\n'
 '- تصویر ذهنی هدف: «این آدم موضوع‌های پیچیده فنی را ساده توضیح می‌دهد و آموزش‌های عملی و به‌روز منتشر می‌کند».')

def _ctx_text(services,content_id):
    item=services['store'].get(content_id)
    if not item: raise ValueError('محتوا پیدا نشد.')
    return item,services.get('policy','')

def _finish(ctx,content_id,kind,oid,status,result,raw,provider,model,job_id,payload=None):
    ctx.services['ai'].save_output(oid,content_id,kind,status,payload,result,raw,provider,model,job_id)

def _normalize_llm(data,list_key=None):
    """CENTRAL AI response-shape boundary (BUG-001). Contract:
    dict -> dict; list-of-one-dict -> that dict (model wrapped it);
    a bare JSON array -> {list_key: [...]} ONLY for handlers that declare a
    semantic list contract (hooks); everything else -> None (=> structured
    parse_error + strict retry). NEVER returns a raw list to a handler, so no
    handler can hit `list has no attribute get`."""
    if isinstance(data,dict): return data
    if isinstance(data,list):
        if list_key and data and all(isinstance(x,str) for x in data):
            return {list_key:data}                     # semantic bare-list (e.g. hook texts)
        if list_key and data and all(isinstance(x,dict) for x in data):
            return {list_key:data}                     # row objects without the wrapper
        if len(data)==1 and isinstance(data[0],dict): return data[0]
    return None

def _llm_json(ctx,content_id,kind,oid,task,messages,max_tokens=1400,validator=None,list_key=None):
    """Structured-output pipeline: extract → repair → validate → one stricter
    retry → honest parse_error. Never fabricates missing fields."""
    ctx.progress(20)
    out=ai.chat(ctx.services['ai'],task,messages,max_tokens=max_tokens,temperature=0.4)
    ctx.log(f"پاسخ از {out['provider']} دریافت شد ({out['model']})")
    ctx.progress(55)
    data=_normalize_llm(extract_json(out['content']),list_key)
    problems=validator(data) if (data is not None and validator) else []
    if data is None or problems:
        reason='خروجی JSON نبود' if data is None else '؛ '.join(problems)
        ctx.log('خروجی قابل‌قبول نبود ('+reason+') — یک تلاش مجدد با قید سخت‌گیرانه‌تر')
        retry=list(messages)
        retry.insert(len(retry)-1 if retry[-1]['role']=='user' else len(retry),
            {'role':'system','content':'یادآوری حیاتی: پاسخ را فقط و فقط به شکل یک JSON خام و معتبر بده — بدون مقدمه، بدون توضیح، بدون markdown، بدون کلید ستاره‌دار. ساختار فیلدها دقیقاً همان باشد که خواسته شد. مشکل قبلی: '+reason})
        try:
            out2=ai.chat(ctx.services['ai'],task,retry,max_tokens=min(max_tokens+800,4800),temperature=0.2)
            data2=_normalize_llm(extract_json(out2['content']),list_key)
            problems2=validator(data2) if (data2 is not None and validator) else []
            if data2 is not None and not problems2:
                ctx.log('تلاش دوم موفق بود')
                ctx.progress(75)
                return out2,data2
            if data2 is not None and (data is None or not (problems and not problems2 and len(problems2)>=len(problems))):
                if not problems2:
                    return out2,data2
            out=out2 if data2 is not None else out
            if data2 is not None: data=data2
            problems=problems2 or problems
            reason='خروجی JSON نبود' if data is None else '؛ '.join(problems)
        except Exception as e:
            ctx.log('تلاش مجدد هم شکست خورد: '+str(e)[:120])
        _finish(ctx,content_id,kind,oid,'parse_error',None,out['content'],out['provider'],out['model'],ctx.id)
        raise ValueError('خروجی مدل قابل‌خواندن نشد ('+reason+')؛ متن خام ذخیره شد. مدل قوی‌تری برای این وظیفه انتخاب کنید.')
    ctx.progress(75)
    return out,data

def article_validator(d):
    """Required SEO fields for generate_article — no fabrication of missing ones."""
    return validate_schema(d,
        required=('title','slug','meta_description','primary_keyword'),
        list_fields=('sections',),min_list=2)

def verify_urls(urls,timeout=10):
    """REAL reachability check. Returns {url: 'live'|'dead'|'invalid'}"""
    out={}
    for u in list(dict.fromkeys(urls or []))[:12]:
        if not re.match(r'^https?://',u or ''): out[u]='invalid'; continue
        try:
            req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (content-factory research)','Range':'bytes=0-4095'})
            with urllib.request.urlopen(req,timeout=timeout) as r:
                out[u]='live' if r.status<400 else 'dead'
        except Exception:
            out[u]='dead'
    return out

JSON_RESEARCH=('JSON خروجی با این ساختار:\n'
 '{"intent":"هدف مخاطب از این محتوا در یک جمله","audience":"مخاطب هدف",'
 '"key_points":["نکتهٔ کلیدی ۱","نکتهٔ کلیدی ۲"],'
 '"claims":[{"claim":"ادعای فنی قابل راستی‌آزمایی","url":"نشانی منبع پیشنهادی یا خالی","confidence":"high یا medium یا low"}],'
 '"search_queries":["کوئری جست‌وجوی فارسی","کوئری انگلیسی"],'
 '"content_gaps":["آنچه رقبا/منابع موجود پوشش نمی‌دهند"],'
 '"structure":["فصل‌بندی پیشنهادی ۴ تا ۷ مورد"]}')

def research_topic_handler(ctx):
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    item,policy=_ctx_text(services,content_id)
    oid=uuid.uuid4().hex
    ctx.log('ساخت تحقیق ساختاریافته از موضوع پروژه')
    base=item.get('transcript') or item.get('body') or item['title']
    system=(f"تو دستیار تحقیق محتوای فنی به زبان فارسی هستی. فقط JSON معتبر بده، بدون هیچ توضیح اضافه.\n{BRAND_RULES}\n{policy[:1500]}")
    user=('برای این موضوع محتوایی، تحقیق ساختاریافته انجام بده. منابع را فقط نشانی‌های واقعی و معروف (مستندات رسمی، ریپوی رسمی، منابع معتبر فنی) بده؛ اگر از نشانی مطمئن نیستی، همان را با confidence=low بده تا بررسی شود.\n\n'
      'موضوع: '+item['title']+'\nمتن پایه (ایده/سناریو/پیاده‌شده):\n'+base[:2500]+'\n\n'+JSON_RESEARCH)
    out,data=_llm_json(ctx,content_id,'research',oid,'research',
                       [{'role':'system','content':system},{'role':'user','content':user}])
    claims=data.get('claims') or []
    urls=[c.get('url') for c in claims if c.get('url')]
    ctx.log(f"بررسی واقعی {len(urls)} نشانی پیشنهادی")
    ctx.progress(80)
    live=verify_urls(urls)
    for c in claims:
        u=c.get('url') or ''
        if u:
            status=live.get(u,'unknown')
            note='تأیید شد (پاسخ داد)' if status=='live' else ('نیاز به بررسی — دسترسی تأیید نشد' if status!='invalid' else 'نشانی نامعتبر')
            services['ai'].add_source(content_id,oid,c.get('claim',''),u,status,note)
    result={'intent':data.get('intent',''),'audience':data.get('audience',''),
            'key_points':data.get('key_points',[]),'claims':claims,'live_map':live,
            'search_queries':data.get('search_queries',[]),'content_gaps':data.get('content_gaps',[]),
            'structure':data.get('structure',[]),
            'needs_verification':[c.get('claim') for c in claims if c.get('confidence')=='low' or (c.get('url') and live.get(c.get('url'))!='live')]}
    _finish(ctx,content_id,'research',oid,'ok',result,'',out['provider'],out['model'],ctx.id)
    ctx.log(f"تحقیق کامل: {len(result['key_points'])} نکته، {len(claims)} ادعا، {sum(1 for v in live.values() if v=='live')} منبع زنده")
    return {'output_id':oid,'kind':'research','sources_added':len(claims),'needs_verification':len(result['needs_verification'])}

JSON_VERIFY=('JSON:\n'
 '{"checks":[{"claim":"ادعا","kind":"version یا command یا syntax یا config یا url یا api یا feature یا compatibility",'
 '"status":"verified یا needs_verification یا wrong","source":"نشانی یا نام منبع رسمی","note":"توضیح کوتاه"}]}')

def technical_verification_handler(ctx):
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    item,policy=_ctx_text(services,content_id)
    oid=uuid.uuid4().hex
    base=item.get('transcript') or item.get('body') or item['title']
    srcs='\n'.join(f"- {s['claim']} ({s['url']} [{s['status']}])" for s in services['ai'].sources(content_id)[:10])
    system='تو بررسی‌کنندهٔ فنی محتوای شبکه/ویپ هستی. فقط JSON معتبر بده. چیزی که مطمئن نیستی را حدس نزن؛ needs_verification بزن.'
    user=('ادعاهای فنی قابل‌راستی‌آزمایی این محتوا را استخراج و وضعیت هر یک را مشخص کن. '
      'اولویت منبع: مستندات رسمی > ریپوی رسمی > مستندات سازنده > منبع تخصصی معتبر > جامعه.\n\n'
      'متن:\n'+base[:2500]+'\n\nمنابع تحقیق موجود:\n'+(srcs or '(ندارد)')+'\n\n'+JSON_VERIFY)
    out,data=_llm_json(ctx,content_id,'verification',oid,'verification',
                       [{'role':'system','content':system},{'role':'user','content':user}])
    checks=data.get('checks') or []
    urls=[c.get('source') for c in checks if (c.get('source') or '').startswith('http')]
    live=verify_urls(urls)
    for c in checks:
        u=c.get('source') or ''
        if u.startswith('http'):
            c['http']=live.get(u,'unchecked')
            if c.get('status')=='verified' and c['http']!='live': c['status']='needs_verification'
    result={'checks':checks,'summary':(f"{sum(1 for c in checks if c['status']=='verified')} تأیید، "
        f"{sum(1 for c in checks if c['status']=='needs_verification')} نیاز به بررسی، "
        f"{sum(1 for c in checks if c['status']=='wrong')} نادرست")}
    _finish(ctx,content_id,'verification',oid,'ok',result,'',out['provider'],out['model'],ctx.id)
    return {'output_id':oid,'summary':result['summary']}

JSON_HOOKS=('JSON:\n'
 '{"hooks":[{"angle":"problem یا mistake یا result یا question یا contrast یا quick-win","text":"متن هوک"}]}')

def generate_hooks_handler(ctx):
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    item,policy=_ctx_text(services,content_id)
    oid=uuid.uuid4().hex
    skill=skill_router.skill_brief('hooks')
    system='تو متخصص هوک ویدیوهای آموزشی فنی فارسی هستی. فقط JSON بده. بدون کلیک‌بیت گمراه‌کننده؛ وعده و محتوا باید یکی باشند.'
    user=('شش هوک کوتاه فارسی (هر یک حداکثر ۱۸ کلمه) با شش زاویهٔ متفاوت برای این محتوا بنویس.\n'
      +skill[:1200]+'\n\n'
      'موضوع: '+item['title']+'\nمتن: '+((item.get('transcript') or item.get('body') or '')[:1200])+'\n\n'+JSON_HOOKS)
    out,data=_llm_json(ctx,content_id,'hooks',oid,'hooks',
                       [{'role':'system','content':system},{'role':'user','content':user}],max_tokens=900,list_key='hooks')
    hooks=data.get('hooks',[]) if isinstance(data,dict) else (data if isinstance(data,list) else [])
    result={'hooks':hooks}
    _finish(ctx,content_id,'hooks',oid,'ok',result,'',out['provider'],out['model'],ctx.id)
    return {'output_id':oid,'count':len(result['hooks'])}

JSON_PACKAGES=('JSON:\n'
 '{"packages":[{"name":"PACKAGE A — پیشنهاد Agent","title":"عنوان","hook":"هوک",'
 '"thumbnail":"کانسپت کاور: چیدمان، متن روی تصویر، عنصر تصویری","reason":"چرا این بسته"}]}')

def generate_title_packages_handler(ctx):
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    item,policy=_ctx_text(services,content_id)
    oid=uuid.uuid4().hex
    skill=skill_router.skill_brief('thumbnail')
    hooks=services['ai'].outputs(content_id,'hooks',1)
    best_hook=(hooks[0]['result'].get('hooks') or [{}])[0].get('text','') if hooks and hooks[0]['result'] else ''
    system=(f"تو بسته‌ساز عنوان/هوک/کاور یوتیوب هستی. عنوان، هوک و کانسپت کاور هر بسته باید دقیقاً یک وعدهٔ واحد بدهند — بدون کلیک‌بیت گمراه‌کننده. فقط JSON بده.\n"
      +skill[:1200]+'\n'
      'برای کاور یوتیوب صورت گوینده لحاظ شود: چهره حدود ۳۰ تا ۵۰ درصد کادر، متن خیلی کوتاه (حداکثر ۳ کلمه)، کنتراست بالا، یک عنصر تصویری پشتیبان، هویت یکدست. رنگ رسمی جعل نشود.')
    user=('چهار بستهٔ هماهنگ بساز. بستهٔ A پیشنهاد خودت است؛ B، C و D زاویه‌های متفاوت.\n'
      'عنوان: '+item['title']+'\nهوک برتر موجود: '+(best_hook or '(ندارم؛ خودت بساز)')+
      '\nمتن: '+((item.get('transcript') or item.get('body') or '')[:1000])+'\n\n'+JSON_PACKAGES)
    out,data=_llm_json(ctx,content_id,'title_packages',oid,'thumbnail',
                       [{'role':'system','content':system},{'role':'user','content':user}],max_tokens=1600)
    result={'packages':data.get('packages',[])}
    _finish(ctx,content_id,'title_packages',oid,'ok',result,'',out['provider'],out['model'],ctx.id)
    return {'output_id':oid,'count':len(result['packages'])}

def generate_script_handler(ctx):
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    item,policy=_ctx_text(services,content_id)
    oid=uuid.uuid4().hex
    skill=skill_router.skill_brief('script')
    research=services['ai'].outputs(content_id,'research',1)
    research_json=''
    if research and research[0]['result']:
        r=research[0]['result']
        research_json=json.dumps({'key_points':r.get('key_points',[]),'structure':r.get('structure',[]),
            'claims':[c.get('claim') for c in r.get('claims',[])[:8]]},ensure_ascii=False)
    verification=services['ai'].outputs(content_id,'verification',1)
    warn=''
    if verification and verification[0]['result']:
        warn='\n'.join(f"- {c['claim']}: {c['status']}" for c in verification[0]['result'].get('checks',[]) if c.get('status')!='verified')
        if warn: warn='ادعاهای نیازمند احتیاط (دقیق و محتاط اشاره شود):\n'+warn
    system=(f"تو سناریونویس حرفه‌ای ویدیوهای آموزشی فارسی هستی. سناریو باید کلمه‌به‌کلمه قابل خواندن جلوی دوربین باشد: "
      "محاوره‌ای، روان، مستقیم و عملی؛ نه کودکانه، نه شرکتی، نه رباتیک.\n"
      +BRAND_RULES+'\n'+CTA_RULES+'\n'
      'راهنمای ساختاری اسکیل reels-scripting (دانش ساختاری، نه متن تحمیلی):\n'+skill[:900]+'\n'
      "مارکرهای تولید را در جای درست داخل متن بگذار: "+' '.join(MARKERS)+'\n'+policy[:1200])
    user=('یک سناریوی کامل فارسی برای این محتوا بنویس.\n'
      'عنوان: '+item['title']+'\nمتن پایه (ایده/سناریو/متن واقعی ضبط):\n'+((item.get('transcript') or item.get('body') or '')[:2500])+
      '\n\nتحقیق موجود:\n'+(research_json or '(تحقیقی ثبت نشده)')+'\n'+warn+
      '\n\nساختار: هوک ۱۵ ثانیه‌ای، معرفی مسئله، آموزش گام‌به‌گام روی تصویر صفحه، اشتباه رایج، جمع‌بندی + CTA.\n'
      'خروجی فقط متن سناریو باشد؛ مارکرها در خط جداگانه قبل از بخش مربوطه.')
    ctx.progress(20)
    out=ai.chat(ctx.services['ai'],'script',[{'role':'system','content':system},{'role':'user','content':user}],
                max_tokens=2600,temperature=0.7)
    script=out['content'].strip()
    found=[m for m in MARKERS if m in script]
    ctx.progress(80)
    result={'script':script,'markers':found,'words':len(script.split())}
    _finish(ctx,content_id,'script',oid,'ok',result,'',out['provider'],out['model'],ctx.id)
    ctx.log(f"سناریو تولید شد: {result['words']} کلمه، {len(found)} مارکر تولید")
    return {'output_id':oid,'markers':found,'words':result['words']}

JSON_SOCIAL=('JSON:\n'
 '{"variants":[{"platform":"YouTube","body":"متن کامل نسخه","cta":"CTA متناسب"}]}')

def generate_social_handler(ctx):
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    item,policy=_ctx_text(services,content_id)
    oid=uuid.uuid4().hex
    skill=skill_router.skill_brief('social')
    platform=ctx.payload.get('platform') or 'همه'
    system=(f"تو نسخه‌ساز محتوای شبکه‌های اجتماعی هستی. کپی یکسان ممنوع؛ ساختار و CTA مخصوص هر پلتفرم.\n{CTA_RULES}\n{skill[:1000]}\nفقط JSON بده.")
    user=('برای این محتوا نسخهٔ اختصاصی بساز برای: '+platform+
      ' (اگر «همه» بود: YouTube، YouTube Shorts، Instagram، Instagram Reels، Telegram، Facebook، LinkedIn).\n'
      'عنوان: '+item['title']+'\nمتن/سناریو: '+((item.get('body') or item.get('transcript') or '')[:1800])+'\n\n'+JSON_SOCIAL)
    out,data=_llm_json(ctx,content_id,'social',oid,'social',
                       [{'role':'system','content':system},{'role':'user','content':user}],max_tokens=2200)
    result={'variants':data.get('variants',[])}
    _finish(ctx,content_id,'social',oid,'ok',result,'',out['provider'],out['model'],ctx.id)
    return {'output_id':oid,'count':len(result['variants'])}

JSON_ARTICLE=('JSON:\n'
 '{"title":"عنوان مقاله","slug":"url-slug-in-english","meta_description":"توضیح متا ۱۵۵ نویسه‌ای",'
 '"primary_keyword":"کلمهٔ اصلی","secondary_keywords":["..."],"h1":"H1",'
 '"sections":[{"h2":"تیتر","text":"پاراگراف‌های مقاله"}],"internal_links":["پیشنهاد لینک داخلی"],'
 '"external_references":["فقط نشانی واقعی و معتبر"],"image_alt":"متن alt تصویر شاخص",'
 '"schema":"نوع اسکیمای پیشنهادی","canonical_note":"یادداشت canonical و جلوگیری از محتوای تکراری","cta":"CTA متناسب سایت"}')

def generate_article_handler(ctx):
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    item,policy=_ctx_text(services,content_id)
    oid=uuid.uuid4().hex
    site=ctx.payload.get('site') or 'tehnet.ir'
    base=item.get('transcript') or ''
    if not base.strip(): raise ValueError('مقاله از متن واقعی ضبط ساخته می‌شود؛ اول transcript را داشته باش.')
    system='تو نویسندهٔ مقالهٔ وب فنی فارسی هستی. فقط JSON معتبر بده.'
    user=('برای سایت '+site+' از این transcript یک مقالهٔ وب کامل بساز و فیلدهای سئو را تولید کن. '
      'مقاله نباید کپی transcript باشد؛ بازنویسی ساختاریافتهٔ وب با هدف جست‌وجوست.\n'
      'transcript:\n'+base[:4000]+'\n\n'+JSON_ARTICLE)
    out,data=_llm_json(ctx,content_id,'article_seo',oid,'seo',
                       [{'role':'system','content':system},{'role':'user','content':user}],max_tokens=3800,
                       validator=article_validator)
    urls=[u for u in data.get('external_references',[]) if isinstance(u,str) and u.startswith('http')]
    data['external_reference_status']=verify_urls(urls)
    data['site']=site
    _finish(ctx,content_id,'article_seo',oid,'ok',data,'',out['provider'],out['model'],ctx.id)
    return {'output_id':oid,'title':data.get('title')}

JSON_PINNED='JSON:\n{"comment":"متن کامنت پین فارسی (۳ تا ۵ جمله)"}'

def generate_pinned_handler(ctx):
    services=ctx.services
    content_id=ctx.payload.get('content_id')
    item,policy=_ctx_text(services,content_id)
    oid=uuid.uuid4().hex
    system='تو کامنت پین یوتیوب می‌سازی: یک پرسش مشارکتی + یک ادامهٔ مفید + CTA نرم. فقط JSON بده. انتشار نیازمند تأیید شماست.'
    user=('موضوع: '+item['title']+'\nمتن: '+((item.get('body') or item.get('transcript') or '')[:900])+'\n'+CTA_RULES+'\n\n'+JSON_PINNED)
    out,data=_llm_json(ctx,content_id,'pinned_comment',oid,'social',
                       [{'role':'system','content':system},{'role':'user','content':user}],max_tokens=500)
    result={'comment':data.get('comment','')}
    _finish(ctx,content_id,'pinned_comment',oid,'ok',result,'',out['provider'],out['model'],ctx.id)
    return {'output_id':oid}

class _Sub:
    """Narrow ctx view for running a full handler as one pipeline stage."""
    def __init__(self,ctx,label,total,i):
        self.services=ctx.services; self.payload={'content_id':ctx.payload.get('content_id')}
        self.id=ctx.id
        self._base=int(i/total*92); self._span=int(92/total); self._label=label; self._outer=ctx
    def progress(self,pct):
        self._outer.progress(min(92,self._base+int(max(0,min(100,pct))/100*self._span)))
    def log(self,m): self._outer.log('«'+self._label+'» '+m)
    def cancelled(self): return self._outer.cancelled()

def content_pipeline_handler(ctx):
    """transcript/idea -> research -> verification -> script -> hooks -> packages -> approval."""
    content_id=ctx.payload.get('content_id')
    steps=[('تحقیق',research_topic_handler),('بررسی فنی',technical_verification_handler),
           ('سناریو',generate_script_handler),('هوک‌ها',generate_hooks_handler),
           ('بسته‌های عنوان/کاور',generate_title_packages_handler)]
    outputs={}
    for i,(label,fn) in enumerate(steps):
        if ctx.cancelled(): raise JobCancelled()
        ctx.log(f"مرحلهٔ {i+1} از {len(steps)}: {label}")
        ctx.progress(int(i/len(steps)*92))
        outputs[label]=fn(_Sub(ctx,label,len(steps),i))
    script_out=outputs.get('سناریو',{})
    rec=uuid.uuid4().hex
    _finish(ctx,content_id,'pipeline',rec,'ok',
            {'steps':{k:v.get('output_id') for k,v in outputs.items()},'awaiting':'approval'},
            '','pipeline','',ctx.id)
    ctx.log('خط تولید کامل شد؛ سناریو، هوک‌ها و بسته‌ها منتظر تأیید شماست.')
    return {'steps':{k:v.get('output_id') for k,v in outputs.items()},'script_words':script_out.get('words',0)}
