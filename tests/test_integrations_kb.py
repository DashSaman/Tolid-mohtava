"""Tests for the new integration/KB/intel/observability layer."""
import unittest, tempfile, sys, shutil, json, time, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from integrations import (all_optional_integrations, KeywordStore, ga4_status, ga4_fetch,
    keyword_provider_status, screaming_frog_status, ruflo_status, normalize_sf_export, search_intelligence_status)
from knowledge import KnowledgeBase, index_project, _tokens
from content_intel import check_topic, refresh_candidates, optimize_content
from store import Store
from jobs import JobManager

def reader_of(d):
    v=memoryview(d); p=[0]
    def r(n):
        if p[0]>=len(d): return b''
        c=bytes(v[p[0]:p[0]+n]); p[0]+=n; return c
    return r

class IntegrationStatusTests(unittest.TestCase):
    def test_all_optional_reported_honestly(self):
        d=all_optional_integrations()
        self.assertEqual(set(d),{'ga4','keyword_planner','search_intelligence','screaming_frog','ruflo'})
        import os
        if not os.environ.get('RUFLO_ENDPOINT'):
            self.assertEqual(d['ruflo']['state'],'disabled')
        self.assertIn(d['screaming_frog']['state'],('ready','unavailable'))
        self.assertIn(d['ga4']['state'],('ready','blocked_by_credential'))
    def test_ga4_fetch_gated(self):
        from jobs import DependencyMissing
        saved={k:os.environ.get(k) for k in ('GA4_PROPERTY_ID','GA4_ACCESS_TOKEN')}
        os.environ.pop('GA4_PROPERTY_ID',None); os.environ.pop('GA4_ACCESS_TOKEN',None)
        try:
            with self.assertRaises(DependencyMissing): ga4_fetch()
        finally:
            for k,v in saved.items():
                if v is not None: os.environ[k]=v

class KeywordStoreTests(unittest.TestCase):
    def test_add_search_no_invented_volume(self):
        tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(tmp.name,ignore_errors=True))
        ks=KeywordStore(Path(tmp.name)/'k.sqlite')
        ks.add('تنظیم مودم',volume_monthly=None,source='manual')
        ks.add('میکروتیک vpn',volume_monthly=1200,source='manual')
        self.assertEqual(len(ks.search('مودم')),1)
        row=ks.search('vpn')[0]
        self.assertEqual(row['volume_monthly'],1200)
        self.assertIsNone(KeywordStore(Path(tmp.name)/'k.sqlite').search('مودم')[0]['volume_monthly'])
        with self.assertRaises(ValueError): ks.add('   ')

class KBTests(unittest.TestCase):
    def test_index_and_traceable_search(self):
        tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(tmp.name,ignore_errors=True))
        db=Path(tmp.name)/'kb.sqlite'
        st=Store(db); kb=KnowledgeBase(db)
        c=st.save(dict(title='آموزش Issabel نصب',brands=['tehran-network'],
                       body='نصب ایزابل و اتصال ترانک SIP تست تماس'))
        n=index_project(kb,st)
        self.assertGreaterEqual(n,1)
        hits=kb.search('نصب ایزابل ترانک')
        self.assertTrue(hits)
        for h in hits:
            self.assertTrue(h['ref_type'] and h['ref_id'],'traceability kept')
        self.assertIn('script',kb.stats())

class ContentIntelTests(unittest.TestCase):
    def _kb(self):
        return KnowledgeBase(Path(tempfile.mkdtemp())/'x.sqlite')
    def test_safe_duplicate_and_cannibalization(self):
        kb=self._kb()
        existing=[{'id':'1','title':'آموزش نصب Issabel روی اوبونتو','platform':'YouTube'},
                  {'id':'2','title':'تنظیم مودم TP-Link','platform':'YouTube'}]
        v1=check_topic(existing,kb,'آموزش نصب Issabel روی اوبونتو ۲۰۲۴')
        self.assertIn(v1['verdict'],('DUPLICATE','MERGE_RECOMMENDED'),'same topic+year = not a new topic')
        v2=check_topic(existing,kb,'آموزش نصب Issabel روی اوبونتو')
        self.assertIn(v2['verdict'],('UPDATE_EXISTING_CONTENT','POTENTIAL_CANNIBALIZATION','DUPLICATE','MERGE_RECOMMENDED'))
        self.assertTrue(v2['evidence'])
        v3=check_topic(existing,kb,'تنظیم فایروال میکروتیک','فایروال')
        self.assertIn(v3['verdict'],('SAFE_NEW_TOPIC','UPDATE_EXISTING_CONTENT'))
    def test_refresh_candidates_age_and_real_ctr(self):
        items=[{'id':'a','title':'قدیمی','updated':'2025-01-01T00:00:00+00:00','stage':'SEO','publish_status':'approved'},
               {'id':'b','title':'تازه','updated':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'stage':'ایده','publish_status':'pending'}]
        out=refresh_candidates(items,perf=[{'content_id':'a','metrics':{'impressions':900,'ctr':0.02}}])
        self.assertEqual(len(out),1); self.assertEqual(out[0]['content_id'],'a')
        self.assertEqual(out[0]['priority'],'high')
    def test_optimize_engine_four_dimensions(self):
        text=('خلاصه: مراحل نصب به این صورت است.\n## نصب\n'+'متن آموزشی '*80+'\nمنبع: https://example.com نسخه 7.4\n- گام یک\n- گام دو')
        r=optimize_content(text,title='آموزش نصب Issabel نسخه 7')
        self.assertEqual(set(r['dimensions']),{'SEO','AEO','GEO','AI_SEARCH'})
        self.assertTrue(all('score' in d for d in r['dimensions'].values()))

class ObservabilityTests(unittest.TestCase):
    def test_stale_detection_and_retry_cap(self):
        tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(tmp.name,ignore_errors=True))
        db=Path(tmp.name)/'o.sqlite'
        m=JobManager(db,handlers={'w':lambda ctx:{'ok':1}},workers=0)
        self.addCleanup(m.stop)
        j=m.enqueue('w',{})
        with m.connect() as c:
            old='[{"time":"2020-01-01T00:00:00+00:00","message":"شروع"}]'
            c.execute("UPDATE jobs SET status='running',started_at='2020-01-01T00:00:00+00:00',logs=? WHERE id=?",(old,j['id']))
        stale=m.mark_stale_running()
        self.assertIn(j['id'],stale)
        self.assertEqual(m.get(j['id'])['status'],'possibly_stuck')
        obs=m.observability()
        row=[o for o in obs if o['job_id']==j['id']][0]
        self.assertEqual(row['status'],'POSSIBLY_STUCK')
        self.assertIn('blocker',row)
        m2=JobManager(db,handlers={'w':lambda ctx:{'ok':1}},workers=0)
        self.addCleanup(m2.stop)
        with m2.connect() as c:
            c.execute("UPDATE jobs SET retry_count=5 WHERE id=?",(j['id'],))
        with self.assertRaises(ValueError): m2.retry(j['id'])

if __name__=='__main__': unittest.main(verbosity=2)
