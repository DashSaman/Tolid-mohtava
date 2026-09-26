import unittest, tempfile, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
try:
    from store import Store
except ImportError:
    Store=None

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(Store,'Store must implement persistent content and approval policy')
        self.tmp=tempfile.TemporaryDirectory()
        self.s=Store(Path(self.tmp.name)/'test.sqlite')
    def tearDown(self):
        if hasattr(self,'tmp'): self.tmp.cleanup()
    def create(self,**kw):
        return self.s.save(dict(title='آزمایش',brands=['tehran-network'],body='متن',**kw))
    def test_isolation_and_persistence(self):
        x=self.create()
        self.assertEqual(len(self.s.list('mytel')),0)
        self.assertEqual(Store(self.s.path).get(x['id'])['body'],'متن')
    def test_edit_invalidates_approval_and_stale_rejected(self):
        x=self.create()
        self.s.decide(x['id'],1,'script','approved')
        x['body']='متن جدید'; y=self.s.save(x)
        self.assertEqual(y['revision'],2)
        self.assertEqual(y['script_status'],'pending')
        with self.assertRaises(ValueError): self.s.decide(x['id'],1,'publish','approved')
        self.assertEqual(len(self.s.history(x['id'])),3)
    def test_approval_idempotency_and_distinct_gates(self):
        x=self.create()
        self.s.decide(x['id'],1,'script','approved')
        self.s.decide(x['id'],1,'script','approved')
        self.assertEqual(len(self.s.history(x['id'])),2)
        self.assertEqual(self.s.get(x['id'])['publish_status'],'pending')
    def test_cross_brand_explicit_and_validation(self):
        x=self.s.save(dict(title='مشترک',brands=['tehran-network','mytel'],body='سناریو'))
        self.assertEqual(self.s.list('mytel')[0]['id'],x['id'])
        with self.assertRaises(ValueError): self.s.save(dict(title='',brands=['mytel']))
        with self.assertRaises(ValueError): self.s.save(dict(title='x',brands=['wrong']))
        with self.assertRaises(ValueError): self.s.decide(x['id'],1,'publish','published')
    def test_concurrent_edit_conflict(self):
        x=self.create(); self.s.save(x)
        with self.assertRaises(ValueError): self.s.save(x)

if __name__=='__main__': unittest.main(verbosity=2)
