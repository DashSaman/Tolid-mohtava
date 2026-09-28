"""AI layer tests with a deterministic fake provider: provider health/routing,
research with REAL url verification, script+markers, hooks, packages, and the
full pipeline — plus honest failure when no provider is available.
"""
import unittest, tempfile, sys, time, shutil, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from store import Store
from ai import AIStore, chat, provider_health, extract_json, DependencyMissing
from ai_jobs import (research_topic_handler, technical_verification_handler, generate_script_handler,
    generate_hooks_handler, generate_title_packages_handler, content_pipeline_handler)
from jobs import JobManager

FAKE_JSON={
 'intent':'آموزش گام‌به‌گام تنظیم مودم برای مخاطب شبکه',
 'audience':'متخصصان IT و تازه‌کارها',
 'key_points':['ورود به پنل مودم','تغییر تنظیمات WAN','ذخیره و ری‌استارت'],
 'claims':[{'claim':'آدرس پیش‌فرض 192.168.1.1 است','url':'','confidence':'high'},
           {'claim':'مستندات رسمی TP-Link','url':'https://www.tp-link.com/en/support/','confidence':'medium'}],
 'search_queries':['تنظیم مودم TP-Link'],'content_gaps':['نکتهٔ ری‌استارت'],
 'structure':['ورود به پنل','تنظیم WAN','ذخیره']}
FAKE_CHECKS={'checks':[{'claim':'192.168.1.1 آدرس پیش‌فرض است','kind':'url','status':'verified','source':'https://www.tp-link.com/en/support/','note':''},
 {'claim':'فرمان backup با نسخهٔ ۷ فرق دارد','kind':'command','status':'needs_verification','source':'','note':''}]}
FAKE_SCRIPT="""[SCREEN RECORD]
سلام به همه! امروز می‌خوایم مودم رو درست تنظیم کنیم.
[FACE CAM]
اول بگم که این آموزش برای تازه‌کارها هم مناسبه.
[SCREEN RECORD]
وارد پنل مودم بشید و تنظیمات WAN رو باز کنید.
[GRAPHIC]
این جدول تنظیمات رو دقت کنید.
[CTA]
اگر سوال داشتید کامنت بزنید و کانال رو دنبال کنید."""
FAKE_HOOKS={'hooks':[{'angle':'problem','text':'مودمت هر هفته قطع می‌شه؟ مشکل از اینجاست'},
 {'angle':'mistake','text':'بزرگ‌ترین اشتباه در تنظیم مودم'}]}
FAKE_PACKAGES={'packages':[{'name':'PACKAGE A — پیشنهاد Agent','title':'تنظیم مودم در ۵ دقیقه','hook':'مودمت قطع می‌شود؟','thumbnail':'چهره ۴۰٪ + متن «۵ دقیقه» + تصویر مودم','reason':'وعدهٔ زمانی مشخص'}]}

class FakeChat:
    """Deterministic stand-in for ai.chat."""
    def __init__(self,store): self.store=store; self.calls=[]
    def __call__(self,store,task,messages,max_tokens=900,temperature=0.6,timeout=600,provider_name=None):
        self.calls.append(task)
        user=messages[-1]['content']
        if 'JSON' in user and 'checks' in user: content=json.dumps(FAKE_CHECKS,ensure_ascii=False)
        elif 'شش هوک' in user or '"hooks"' in user: content=json.dumps(FAKE_HOOKS,ensure_ascii=False)
        elif 'چهار بستهٔ هماهنگ' in user: content=json.dumps(FAKE_PACKAGES,ensure_ascii=False)
        elif 'تحقیق ساختاریافته' in user: content=json.dumps(FAKE_JSON,ensure_ascii=False)
        elif 'سناریوی کامل فارسی' in user: content=FAKE_SCRIPT
        else: content=json.dumps(FAKE_JSON,ensure_ascii=False)
        return {'content':content,'provider':'fake','model':'fake-1'}

def reader_of(data):
    view=memoryview(data); pos=[0]
    def reader(n):
        if pos[0]>=len(data): return b''
        chunk=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n
        return chunk
    return reader

class AILayerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'ai.sqlite'
        self.store=Store(db)
        self.ai=AIStore(db)
        self.item=self.store.save(dict(title='آموزش تنظیم مودم',brands=['tehran-network'],
            body='می‌خوام تنظیم مودم TP-Link رو نشون بدم',transcript=''))
        self.mgr=JobManager(db,handlers=self._handlers(),workers=1,
            services={'store':self.store,'ai':self.ai,'policy':'سیاست آزمایشی','profile':{}})
        self.addCleanup(self.mgr.stop)
        self._orig_chat=ai_module_chat=None
        import ai as ai_mod
        self._orig_chat=ai_mod.chat
        self.fake=FakeChat(ai_mod)
        ai_mod.chat=self.fake
        self.addCleanup(lambda: setattr(ai_mod,'chat',self._orig_chat))
    def _handlers(self):
        import ai_jobs
        return {'research_topic':ai_jobs.research_topic_handler,
                'technical_verification':ai_jobs.technical_verification_handler,
                'generate_script':ai_jobs.generate_script_handler,
                'generate_hooks':ai_jobs.generate_hooks_handler,
                'generate_title_packages':ai_jobs.generate_title_packages_handler,
                'content_pipeline':ai_jobs.content_pipeline_handler}
    def wait(self,jid,timeout=60):
        end=time.time()+timeout
        while time.time()<end:
            j=self.mgr.get(jid)
            if j['status'] in ('completed','failed','cancelled','waiting_approval'): return j
            time.sleep(0.02)
        raise AssertionError('job did not settle: '+json.dumps(self.mgr.get(jid),ensure_ascii=False)[:300])
    def test_provider_routing_and_honest_health(self):
        p=self.ai.provider_for_task('research')
        self.assertEqual(p['name'],'lmstudio','default provider must serve tasks')
        self.ai.save_provider('remote-openai','https://api.openai.com/v1','gpt','OPENAI_API_KEY',[])
        r=provider_health(self.ai,'remote-openai')
        self.assertFalse(r['ok'])
        self.assertIn('OPENAI_API_KEY',r['detail'],'missing credential must be honest')
        self.ai.save_provider('dead-local','http://127.0.0.1:59999/v1','','',[])
        r=provider_health(self.ai,'dead-local')
        self.assertFalse(r['ok'])
    def test_no_provider_means_honest_failure(self):
        for p in self.ai.providers(): self.ai.save_provider(p['name'],p['base_url'],p['model'],p['api_key_env'],p['tasks'],enabled=False)
        with self.assertRaises(DependencyMissing):
            chat(self.ai,'script',[{'role':'user','content':'x'}])
    def test_extract_json_survives_chatter_and_fences(self):
        self.assertEqual(extract_json('```json\n{"a":1}\n```'),{'a':1})
        self.assertEqual(extract_json('بفرمایید: {"a": {"b": 2}} پایان'),{'a':{'b':2}})
        self.assertIsNone(extract_json('هیچ JSONی نیست'))
    def test_research_verifies_real_urls(self):
        import ai_jobs
        self._orig_verify=ai_jobs.verify_urls
        ai_jobs.verify_urls=lambda urls,timeout=10:{u:'dead' for u in (urls or [])}
        self.addCleanup(lambda: setattr(ai_jobs,'verify_urls',self._orig_verify))
        j=self.mgr.enqueue('research_topic',{'content_id':self.item['id']})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        srcs=self.ai.sources(self.item['id'])
        self.assertEqual(len(srcs),1,'only claims with urls become sources')
        self.assertIn(srcs[0]['status'],('live','dead'),'real HTTP check happened')
        out=self.ai.outputs(self.item['id'],'research',1)[0]
        self.assertTrue(out['result']['needs_verification'],'low-confidence claims flagged')
    def test_script_contains_markers_and_words(self):
        j=self.mgr.enqueue('generate_script',{'content_id':self.item['id']})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        out=self.ai.outputs(self.item['id'],'script',1)[0]
        self.assertIn('[SCREEN RECORD]',out['result']['script'])
        self.assertGreater(out['result']['words'],10)
    def test_hooks_and_packages(self):
        j=self.mgr.enqueue('generate_hooks',{'content_id':self.item['id']})
        self.assertEqual(self.wait(j['id'])['status'],'completed')
        self.assertEqual(len(self.ai.outputs(self.item['id'],'hooks',1)[0]['result']['hooks']),2)
        j=self.mgr.enqueue('generate_title_packages',{'content_id':self.item['id']})
        self.assertEqual(self.wait(j['id'])['status'],'completed')
        pk=self.ai.outputs(self.item['id'],'title_packages',1)[0]['result']['packages']
        self.assertEqual(len(pk),1)
        self.assertIn('PACKAGE A',pk[0]['name'])
    def test_full_pipeline_runs_all_stages(self):
        j=self.mgr.enqueue('content_pipeline',{'content_id':self.item['id']})
        j=self.wait(j['id'],timeout=120)
        self.assertEqual(j['status'],'completed',j.get('error'))
        kinds={o['kind'] for o in self.ai.outputs(self.item['id'])}
        self.assertTrue({'research','verification','script','hooks','title_packages'}<=kinds)
        self.assertEqual(self.fake.calls.count('research'),1)
    def test_parse_error_is_honest_and_stored(self):
        import ai as ai_mod
        ai_mod.chat=lambda store,task,messages,**kw: {'content':'این متن JSON نیست','provider':'fake','model':'x'}
        try:
            j=self.mgr.enqueue('generate_hooks',{'content_id':self.item['id']})
            j=self.wait(j['id'])
            self.assertEqual(j['status'],'failed')
            outs=self.ai.outputs(self.item['id'],'hooks')
            self.assertEqual(outs[0]['status'],'parse_error')
            self.assertTrue(outs[0]['raw'])
        finally:
            ai_mod.chat=self.fake

if __name__=='__main__': unittest.main(verbosity=2)
