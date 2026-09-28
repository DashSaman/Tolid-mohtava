"""Intelligence engines tests: snapshots append-only, learning-loop truthfulness,
BASELINE→DATA_DRIVEN scheduling, optimization patterns, Shorts V2 diversity,
SEO proposals from real scan data, adapter honesty.
"""
import unittest, tempfile, sys, time, shutil, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from analytics import (AnalyticsStore, adapter_status, recommend_slot, detect_patterns,
    detect_anomalies, MIN_SAMPLE)
from intelligence import rank_short_candidates, build_seo_proposals, weekly_plan_handler
from seo_engine import SEOStore
from store import Store
import ai as ai_mod

class AnalyticsStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        self.a=AnalyticsStore(Path(self.tmp.name)/'an.sqlite')
    def test_snapshots_append_only_and_validated(self):
        self.a.add_snapshot('youtube','tn','v1',{'views':100,'ctr':0.04},'manual')
        self.a.add_snapshot('youtube','tn','v1',{'views':150,'ctr':0.05},'manual')
        self.assertEqual(len(self.a.snapshots('youtube')),2,'history kept')
        with self.assertRaises(ValueError): self.a.add_snapshot('youtube','tn','v1',{'views':'many'},'manual')
        with self.assertRaises(ValueError): self.a.add_snapshot('youtube','tn','v1',{'bogus':1},'manual')
    def test_learning_loop_only_claims_with_evidence(self):
        r=recommend_slot(self.a,'tehran-network','youtube')
        self.assertEqual(r['mode'],'BASELINE')
        self.assertEqual(r['sample_size'],0)
        self.assertLess(r['confidence'],0.5)
        # add enough real history with a clear winner (پنجشنبه 20)
        for i in range(MIN_SAMPLE):
            self.a.upsert_performance(f'c{i}','tehran-network','youtube','long','میکروتیک','t','h',f't{i}','th',
                500,None,'subscribe','','پنجشنبه',20 if i%2==0 else 11,
                {'views':1000 if i%2==0 else 100,'engagement':80 if i%2==0 else 5})
        r2=recommend_slot(self.a,'tehran-network','youtube')
        self.assertEqual(r2['mode'],'DATA_DRIVEN')
        self.assertEqual((r2['day'],r2['hour']),('پنجشنبه',20))
        self.assertGreaterEqual(r2['sample_size'],MIN_SAMPLE)
        self.assertTrue(r2['evidence'],'recommendation must cite evidence')
    def test_optimization_patterns_fire_on_real_numbers(self):
        hist=[{'metrics':{'views':800}} for _ in range(4)]
        pats=detect_patterns({'impressions':5000,'ctr':0.015},hist)
        self.assertTrue(any(p[0]=='HIGH_IMPRESSIONS_LOW_CTR' for p in pats))
        self.assertEqual(detect_patterns({'impressions':50,'ctr':0.9},hist),[])
        self.assertEqual(detect_patterns({'impressions':5000,'ctr':0.01},[]),[],'no history = no claims')
    def test_anomaly_detection(self):
        for v in (100,110,105,95):
            self.a.add_snapshot('telegram','tn','ch',{'views':v},'manual')
        self.assertEqual(detect_anomalies(self.a,'telegram'),[])
        self.a.add_snapshot('telegram','tn','ch',{'views':400},'manual')
        self.assertTrue(any(x['kind']=='spike' for x in detect_anomalies(self.a,'telegram')))
    def test_proposal_lifecycle(self):
        pid=self.a.add_proposal('c1','youtube','X','d','r',{'k':1},5,0.7)
        self.assertEqual(self.a.proposals('proposed')[0]['id'],pid)
        self.a.decide_proposal(pid,'approved')
        self.assertEqual(self.a.proposals('approved')[0]['id'],pid)
        with self.assertRaises(ValueError): self.a.decide_proposal(pid,'bogus')
    def test_adapters_honest_without_credentials(self):
        rows=adapter_status()
        self.assertEqual(len(rows),8)
        import os
        if not any(os.environ.get(v) for r in rows for v in r['env']):
            self.assertTrue(all(r['state']=='blocked_by_credential' for r in rows),'no fake readiness')

class ShortsV2Tests(unittest.TestCase):
    def test_diverse_angles_and_ranking(self):
        segs=[
            {'start':0,'end':12,'text':'چطور در میکروتیک یک تانل سالم بسازیم؟ در سه مرحله'},
            {'start':15,'end':26,'text':'بزرگ‌ترین اشتباه در پیکربندی فایروال میکروتیک همین‌جاست'},
            {'start':30,'end':44,'text':'نکتهٔ مهم: همیشه بکاپ بگیرید'},
            {'start':50,'end':70,'text':'راه‌حل سریع برای رفع مشکل NAT در روتر'},
            {'start':80,'end':120,'text':'متن خیلی طولانی بدون هوک که نمرهٔ کمتری می‌گیرد چون هیچ کلمهٔ کلیدی جذابی ندارد.'},
        ]
        picks=rank_short_candidates(segs)
        self.assertTrue(1<=len(picks)<=3)
        angles={p['angle'] for p in picks}
        self.assertEqual(len(angles),len(picks),'picks must be different angles')
        self.assertTrue(all('why' in p and 'score' in p for p in picks))
    def test_empty_or_short(self):
        self.assertEqual(rank_short_candidates([]),[])
        self.assertEqual(rank_short_candidates([{'start':0,'end':2,'text':'سلام'}]),[])

class SEOProposalTests(unittest.TestCase):
    def test_proposals_from_real_scan_shape(self):
        pages=[
            {'url':'https://x/1','status':200,'title':'T','meta_description':None,'canonical':None,'h1_count':0,'images':3,'images_missing_alt':2,'internal_links':2},
            {'url':'https://x/2','status':404},
        ]
        summary={'site':'tehnet.ir','infra':{'robots':'ok','sitemap':'http 404','sitemap_redirect':'https://tehnet.ir/wp-sitemap.xml'},
                 'duplicate_titles':[{'title':'dup','pages':['https://x/1','https://x/3']}],
                 'broken_links':[{'url':'https://x/dead','status':404}]}
        props=build_seo_proposals(pages,summary)
        codes={p['code'] for p in props}
        self.assertTrue({'missing_meta','missing_canonical','h1_issue','missing_alt','http_error','duplicate_title','sitemap_missing','broken_link'}<=codes)
        sitemap=[p for p in props if p['code']=='sitemap_missing'][0]
        self.assertIn('wp-sitemap.xml',sitemap['issue'],'must carry the real diagnosis')
        self.assertTrue(all(p.get('fix') for p in props),'every proposal has a concrete fix')

class WeeklyPlanTests(unittest.TestCase):
    def test_plan_uses_local_evidence_and_fake_llm(self):
        tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(tmp.name,ignore_errors=True))
        db=Path(tmp.name)/'w.sqlite'
        st=Store(db); an=AnalyticsStore(db); seo=SEOStore(db)
        c=st.save(dict(title='آموزش میکروتیک',brands=['tehran-network'],body='x'))
        an.upsert_performance(c['id'],'tehran-network','youtube','long','میکروتیک','t','h','ti','th',
            600,None,'sub','','پنجشنبه',20,{'views':900,'engagement':70})
        from jobs import JobManager
        mgr=JobManager(db,handlers={'weekly_plan':weekly_plan_handler},workers=1,
                       services={'store':st,'analytics':an,'seo':seo,'ai':None})
        self.addCleanup(mgr.stop)
        class Ctx:  # minimal job ctx
            services={'store':st,'analytics':an,'seo':seo,'ai':None}
            payload={'brand':'tehran-network'}
            def log(self,m): pass
            def progress(self,p): pass
        FAKE={'plan':[{'title':'تنظیم فایروال میکروتیک برای VoIP','pillar':'میکروتیک','platform':'YouTube',
                       'content_type':'long','why':'VoIP بر اساس رکوردها بهترین عملکرد را دارد','opportunity':'شکاف پوشش',
                       'business_relevance':'پشتیبان MyTel','confidence':0.6}]}
        orig=ai_mod.chat
        ai_mod.chat=lambda store,task,messages,**kw: {'content':json.dumps(FAKE,ensure_ascii=False),'provider':'fake','model':'x'}
        try:
            res=weekly_plan_handler(Ctx())
        finally:
            ai_mod.chat=orig
        self.assertEqual(res['evidence_summary']['projects'],1)
        self.assertEqual(res['evidence_summary']['performance_records'],1)
        self.assertEqual(res['plan'][0]['sample_size'],1,'plan rows carry sample size')

if __name__=='__main__': unittest.main(verbosity=2)
