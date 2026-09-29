# -*- coding: utf-8 -*-
"""REAL benchmark: Llama vs Qwen on Persian tasks (script, article, JSON hooks,
social variants, SEO metadata). Runs through ai.chat against the live LM Studio
with whichever models are loaded. Reports validity + timing + Persian keyword
relevance. No fabrication — raw failure counts as failure."""
import sys, time, json, re
sys.path.insert(0, str(__file__).rsplit('\\',2)[0] + '\\outputs\\panel')
import ai
from ai import AIStore, extract_json

DB = str(__file__).rsplit('\\',1)[0] + '\\..\\work\\bench.sqlite'
store = AIStore(DB)

TOPIC = 'راه‌اندازی سرویس VoIP با Issabel و اتصال ترانک SIP'
KEYWORDS = ['ایزابل','issabel','voip','sip','ترانک','تماس','تلفن']
TRANSCRIPT = ('سلام دوستان. در این ویدیو می‌خواهیم نصب ایزابل را نشان دهیم. ابتدا سرور اوبونتو را آماده می‌کنیم '
 'و سپس پکیج ایزابل را نصب می‌کنیم. بعد ترانک SIP را در تنظیمات وارد می‌کنیم و شماره‌ها را به داخلی‌ها وصل '
 'می‌کنیم. در پایان تست تماس انجام می‌دهیم و کیفیت صدا را بررسی می‌کنیم.')

def kw_relevance(text):
    t=(text or '').lower()
    hits=sum(1 for k in KEYWORDS if k in t)
    return round(hits/len(KEYWORDS),2)

TASKS = {
 'script': dict(task='script', max_tokens=1800,
    msgs=[{'role':'system','content':'تو سناریونویس ویدیوهای آموزشی فارسی هستی. محاوره‌ای و دقیق بنویس.'},
          {'role':'user','content':'یک سناریوی کوتاه فارسی برای این موضوع بنویس: '+TOPIC+'\nمتن پایه: '+TRANSCRIPT}]),
 'article': dict(task='seo', max_tokens=2400,
    msgs=[{'role':'system','content':'تو نویسندهٔ مقالهٔ وب فنی فارسی هستی. فقط JSON معتبر بده.'},
          {'role':'user','content':'از این transcript یک مقالهٔ وب برای tehnet.ir بساز. ONLY JSON:\n'
           '{"title":"...","slug":"english-slug","meta_description":"...","primary_keyword":"...","secondary_keywords":["..."],'
           '"sections":[{"h2":"تیتر","text":"متن"}]}\ntranscript: '+TRANSCRIPT}]),
 'hooks_json': dict(task='hooks', max_tokens=500,
    msgs=[{'role':'system','content':'فقط JSON بده.'},
          {'role':'user','content':'سه هوک فارسی برای این موضوع. ONLY JSON: {"hooks":[{"angle":"problem","text":"..."}]}\nموضوع: '+TOPIC}]),
 'social': dict(task='social', max_tokens=700,
    msgs=[{'role':'system','content':'فقط JSON بده.'},
          {'role':'user','content':'برای Telegram یک پست فارسی. ONLY JSON: {"variants":[{"platform":"Telegram","body":"...","cta":"..."}]}\nموضوع: '+TOPIC}]),
 'seo_meta': dict(task='seo', max_tokens=400,
    msgs=[{'role':'system','content':'فقط JSON بده.'},
          {'role':'user','content':'متادیتای سئو برای مقالهٔ فارسی. ONLY JSON: {"title":"...","meta_description":"...","slug":"...","keywords":["..."]}\nموضوع: '+TOPIC}]),
}

NEEDS_JSON = ('article','hooks_json','social','seo_meta')

def run_task(model,name,cfg):
    store.save_provider('lmstudio','http://127.0.0.1:1234/v1',model,'',['research','verification','script','social','seo','analysis','hooks','thumbnail'])
    t0=time.time()
    try:
        out=ai.chat(store,cfg['task'],cfg['msgs'],max_tokens=cfg['max_tokens'],
                    temperature=0.4,timeout=900,provider_name='lmstudio')
    except Exception as e:
        return {'ok':False,'err':str(e)[:120],'sec':round(time.time()-t0,1)}
    sec=round(time.time()-t0,1)
    text=out['content']
    res={'ok':True,'sec':sec,'chars':len(text),'rel':kw_relevance(text)}
    if name in NEEDS_JSON:
        d=extract_json(text)
        if d is None:
            res['ok']=False; res['err']='parse_error'; res['json']=False
        else:
            res['json']=True
            if name=='article':
                res['valid']=not ai.validate_schema(d,required=('title','slug','meta_description','primary_keyword'),
                                                    list_fields=('sections',),min_list=2)
                res['ok']=bool(res.get('valid'))
                res['sections']=len(d.get('sections') or [])
                res['rel']=kw_relevance(json.dumps(d,ensure_ascii=False))
    else:
        res['markers']=sum(1 for m in ('[FACE CAM]','[SCREEN RECORD]','[CTA]','[GRAPHIC]') if m in text)
    return res

def main(models):
    results={}
    for model in models:
        print(f'\n===== {model} =====',flush=True)
        results[model]={}
        for name,cfg in TASKS.items():
            r=run_task(model,name,cfg)
            results[model][name]=r
            tag='OK' if r['ok'] else 'FAIL'
            extra=f" {r.get('sec')}s rel={r.get('rel')}"+(f" json={r.get('json')} sections={r.get('sections')}" if name=='article' else '')
            print(f"  {name:10s} {tag}{extra} {('ERR='+r['err']) if r.get('err') else ''}",flush=True)
    json.dump(results,open('work/bench-results.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print('\nsaved work/bench-results.json')

if __name__=='__main__':
    main(sys.argv[1:])
