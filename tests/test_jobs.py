import unittest, tempfile, sys, time, json, shutil, threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from jobs import JobManager, DependencyMissing, STATES

class JobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db=Path(self.tmp.name)/'jobs.sqlite'
    def tearDown(self):
        shutil.rmtree(self.tmp.name,ignore_errors=True)
    def mgr(self,handlers,workers=2):
        m=JobManager(self.db,handlers=handlers,workers=workers)
        self.addCleanup(m.stop)
        return m
    def wait(self,jid,mgr=None,timeout=10,status=('completed','failed','cancelled','waiting_approval')):
        m=mgr or self.m
        end=time.time()+timeout
        while time.time()<end:
            j=m.get(jid)
            if j['status'] in status: return j
            time.sleep(0.02)
        raise AssertionError('job did not settle: '+json.dumps(m.get(jid),ensure_ascii=False)[:400])
    def test_lifecycle_result_and_timestamps(self):
        def work(ctx):
            ctx.log('شروع کار'); ctx.progress(50)
            return {'out':ctx.payload['x']*2}
        self.m=self.mgr({'double':work})
        j=self.m.enqueue('double',{'x':21})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'completed')
        self.assertEqual(j['result']['out'],42)
        self.assertEqual(j['progress'],100)
        self.assertTrue(j['started_at'] and j['finished_at'] and j['created_at'])
        self.assertTrue(any('شروع کار' in l['message'] for l in j['logs']))
    def test_idempotency_key_is_strict(self):
        gate=threading.Event()
        def slow(ctx):
            gate.wait(5); return {}
        self.m=self.mgr({'slow':slow})
        a=self.m.enqueue('slow',{},idempotency_key='render:1:2')
        b=self.m.enqueue('slow',{},idempotency_key='render:1:2')
        self.assertEqual(a['id'],b['id'])
        gate.set()
        a=self.wait(a['id'])
        c=self.m.enqueue('slow',{},idempotency_key='render:1:2')
        self.assertEqual(a['id'],c['id'],'same key after completion maps to the same job')
        self.wait(a['id'])
        r=self.m.retry(a['id'])
        self.assertEqual(r['id'],a['id'],'re-run goes through explicit retry of the same job')
    def test_unknown_kind_rejected(self):
        self.m=self.mgr({})
        with self.assertRaises(ValueError): self.m.enqueue('nope',{})
    def test_restart_preserves_history_and_redispatches_queue(self):
        blocker=threading.Event()
        release=threading.Event()
        def work(ctx):
            blocker.wait(5); release.wait(5); return {'ok':True}
        m1=self.mgr({'work':work},workers=1)
        j=m1.enqueue('work',{})
        deadline=time.time()+10
        while time.time()<deadline and m1.get(j['id'])['status']!='running': time.sleep(0.02)
        blocker.set()
        # simulate abrupt restart: no stop(), new manager over same DB (daemon thread abandoned)
        m2=JobManager(self.db,handlers={'work':lambda ctx:{'ok':True}},workers=1)
        self.addCleanup(m2.stop)
        j2=m2.get(j['id'])
        self.assertIn(j2['status'],('failed','completed'),'history must survive restart')
        if j2['status']=='failed': self.assertIn('بازراه‌اندازی',j2['error'])
        release.set()
        time.sleep(0.3)
        self.assertIsNotNone(m2.get(j['id']))
    def test_queued_job_survives_restart_with_zero_workers(self):
        m1=self.mgr({'work':lambda ctx:{'ok':True}},workers=0)
        j=m1.enqueue('work',{})
        self.assertEqual(m1.get(j['id'])['status'],'queued')
        m2=JobManager(self.db,handlers={'work':lambda ctx:{'ok':True}},workers=1)
        self.addCleanup(m2.stop)
        end=time.time()+10
        while time.time()<end and m2.get(j['id'])['status']!='completed': time.sleep(0.02)
        self.assertEqual(m2.get(j['id'])['status'],'completed')
    def test_running_job_marked_failed_after_restart(self):
        m1=self.mgr({'work':lambda ctx:{'ok':True}},workers=0)
        j=m1.enqueue('work',{})
        with m1.connect() as c:
            c.execute("UPDATE jobs SET status='running',started_at=? WHERE id=?",('2026-01-01T00:00:00+00:00',j['id']))
        m2=JobManager(self.db,handlers={'work':lambda ctx:{'ok':True}},workers=0)
        self.addCleanup(m2.stop)
        j2=m2.get(j['id'])
        self.assertEqual(j2['status'],'failed')
        self.assertIn('بازراه‌اندازی',j2['error'])
        self.assertEqual(j2['retry_count'],0)
    def test_cancel_queued_and_retry_failed(self):
        calls=[]
        def maybe_fail(ctx):
            calls.append(ctx.payload)
            if ctx.payload.get('boom'): raise RuntimeError('انفجار آزمایشی')
            return {}
        self.m=self.mgr({'w':maybe_fail})
        j=self.m.enqueue('w',{'boom':True})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'failed')
        self.assertIn('انفجار',j['error'])
        r=self.m.retry(j['id'])
        self.assertEqual(r['retry_count'],1)
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'failed','retried job must run again and fail honestly')
        gate=threading.Event()
        self.m.handlers['w']=lambda ctx:(gate.wait(5),{})[1]
        mc=self.mgr({'hold':lambda ctx:(gate.wait(5),{})[1]},workers=1)
        mc.enqueue('hold',{})
        deadline=time.time()+5
        while time.time()<deadline and mc.list(status='running',limit=1)==[]: time.sleep(0.02)
        k=mc.enqueue('hold',{})
        self.assertEqual(mc.get(k['id'])['status'],'queued')
        mc.cancel(k['id'])
        self.assertEqual(mc.get(k['id'])['status'],'cancelled')
        gate.set()
    def test_dependency_missing_is_honest_failure(self):
        self.m=self.mgr({'needs_engine':lambda ctx:(_ for _ in ()).throw(DependencyMissing('faster-whisper نصب نیست'))})
        j=self.m.enqueue('needs_engine',{})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'failed')
        self.assertTrue(j['error'].startswith('BLOCKED_BY_DEPENDENCY'))
    def test_waiting_approval_resume_and_reject(self):
        def two_stage(ctx):
            if not ctx.payload.get('approved'): return {'waiting_approval':True,'question':'رندر نهایی اجرا شود؟'}
            return {'done':True}
        self.m=self.mgr({'staged':two_stage})
        j=self.m.enqueue('staged',{})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'waiting_approval')
        d=self.m.decide(j['id'],True)
        self.assertIn(d['status'],('queued','running','completed'))
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'completed')
        self.assertTrue(j['result']['done'])
        k=self.m.enqueue('staged',{})
        k=self.wait(k['id'])
        self.m.decide(k['id'],False)
        self.assertEqual(self.m.get(k['id'])['status'],'cancelled')
        with self.assertRaises(ValueError): self.m.decide(k['id'],True)
    def test_list_filter_and_states(self):
        self.m=self.mgr({'ok':lambda ctx:{}})
        j=self.m.enqueue('ok',{})
        self.wait(j['id'])
        self.assertTrue(all(x['status'] in STATES for x in self.m.list()))
        self.assertEqual(len(self.m.list(status='completed')),1)
        with self.assertRaises(ValueError): self.m.list(status='bogus')

import threading
if __name__=='__main__': unittest.main(verbosity=2)
