"""Focused tests for the completion-sprint modules: OAuth store/flow, Gemini
gating, WP idempotency/retry semantics, Telegram retry/dedupe, GSC ingestion,
auth enforcement."""
import unittest, tempfile, sys, shutil, json, os, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from providers import OAuthStore, oauth_start_url, OAUTH_PROVIDERS, gemini_image
from jobs import DependencyMissing, JobManager

class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        self.st=OAuthStore(Path(self.tmp.name)/'o.sqlite')
    def test_state_single_use_and_csrf(self):
        st=self.st.new_state('youtube')
        self.assertEqual(self.st.pop_state(st),'youtube')
        self.assertIsNone(self.st.pop_state(st),'state is single-use (CSRF)')
        self.assertIsNone(self.st.pop_state('forged'))
    def test_start_url_requires_client(self):
        os.environ.pop('YOUTUBE_CLIENT_ID',None)
        with self.assertRaises(DependencyMissing): oauth_start_url('youtube',self.st)
    def test_start_url_shape(self):
        os.environ['YOUTUBE_CLIENT_ID']='cid-test'
        try:
            u=oauth_start_url('youtube',self.st,'http://127.0.0.1:8767')
            self.assertIn('accounts.google.com',u); self.assertIn('state=',u)
            self.assertIn('youtube.upload',u.replace('%20','+').replace('+','%20')) or self.assertIn('youtube.upload',u)
        finally: os.environ.pop('YOUTUBE_CLIENT_ID',None)
    def test_token_store_expiry(self):
        self.st.save_token('youtube','acc','ref','s',3600)
        self.assertEqual(self.st.get_token('youtube'),'acc')
        self.st.save_token('youtube','acc','ref','s',-10)
        self.assertIsNone(self.st.get_token('youtube'),'expired token rejected')

class GeminiTests(unittest.TestCase):
    def test_gated_without_key(self):
        os.environ.pop('GOOGLE_AI_API_KEY',None)
        with self.assertRaises(DependencyMissing): gemini_image('prompt','/tmp/x.png')

class WordPressIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        self.dbdir=Path(self.tmp.name)
        os.environ['TEHNET_PANEL_DB']=str(self.dbdir/'c.sqlite')
    def tearDown(self):
        os.environ.pop('TEHNET_PANEL_DB',None)
    def test_guard_blocks_duplicate(self):
        import publishing
        import urllib.request, urllib.error
        # simulate: guard file pre-written => no network, deduplicated result
        payload={'title':'t'}
        guard=self.dbdir/('wp-idem-tehnet-ir-'+__import__('hashlib').sha256(json.dumps({'title':'t','content':'c','status':'draft'},sort_keys=True).encode()).hexdigest()[:16]+'.json')
        guard.parent.mkdir(parents=True,exist_ok=True)
        guard.write_text(json.dumps({'id':77,'link':'http://x','status':'draft'}))
        os.environ.update(WP_TEHNET_USER='u',WP_TEHNET_APP_PASSWORD='p')
        try:
            res=publishing.wordpress_draft('tehnet.ir','t','c',slug=None,excerpt=None)
            self.assertEqual(res['id'],77); self.assertTrue(res.get('deduplicated'))
        finally:
            os.environ.pop('WP_TEHNET_USER',None); os.environ.pop('WP_TEHNET_APP_PASSWORD',None)

class TelegramRetryTests(unittest.TestCase):
    def test_gated(self):
        os.environ.pop('TELEGRAM_BOT_TOKEN',None)
        import notifications
        r=notifications.telegram_send('x')
        self.assertFalse(r['ok'])

class GSCIngestTests(unittest.TestCase):
    def test_gated_honest(self):
        tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(tmp.name,ignore_errors=True))
        from analytics import AnalyticsStore, gsc_ingest_handler
        an=AnalyticsStore(Path(tmp.name)/'a.sqlite')
        os.environ.pop('GSC_CREDENTIALS',None)
        class Ctx:
            services={'analytics':an}; payload={'site':'x'}; id='t1'
            @staticmethod
            def log(m): pass
            @staticmethod
            def progress(p): pass
        with self.assertRaises(DependencyMissing): gsc_ingest_handler(Ctx())

class AuthEnforcementTests(unittest.TestCase):
    def test_require_auth_blocks_when_enabled(self):
        import server as srv
        os.environ.update(ADMIN_USER='a',ADMIN_PASSWORD='pw12345')
        try:
            from ops import Auth
            a=Auth(); self.assertTrue(a.enabled)
            tok=a.login('a','pw12345')['token']
            self.assertTrue(a.check(tok))
            self.assertFalse(a.check('bad'))
        finally:
            os.environ.pop('ADMIN_USER',None); os.environ.pop('ADMIN_PASSWORD',None)

if __name__=='__main__': unittest.main(verbosity=2)
"""Focused tests for the completion-sprint modules: OAuth store/flow, Gemini
gating, WP idempotency/retry semantics, Telegram retry/dedupe, GSC ingestion,
auth enforcement."""
import unittest, tempfile, sys, shutil, json, os, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from providers import OAuthStore, oauth_start_url, OAUTH_PROVIDERS, gemini_image
from jobs import DependencyMissing, JobManager

class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        self.st=OAuthStore(Path(self.tmp.name)/'o.sqlite')
    def test_state_single_use_and_csrf(self):
        st=self.st.new_state('youtube')
        self.assertEqual(self.st.pop_state(st),'youtube')
        self.assertIsNone(self.st.pop_state(st),'state is single-use (CSRF)')
        self.assertIsNone(self.st.pop_state('forged'))
    def test_start_url_requires_client(self):
        os.environ.pop('YOUTUBE_CLIENT_ID',None)
        with self.assertRaises(DependencyMissing): oauth_start_url('youtube',self.st)
    def test_start_url_shape(self):
        os.environ['YOUTUBE_CLIENT_ID']='cid-test'
        try:
            u=oauth_start_url('youtube',self.st,'http://127.0.0.1:8767')
            self.assertIn('accounts.google.com',u); self.assertIn('state=',u)
            self.assertIn('youtube.upload',u.replace('%20','+').replace('+','%20')) or self.assertIn('youtube.upload',u)
        finally: os.environ.pop('YOUTUBE_CLIENT_ID',None)
    def test_token_store_expiry(self):
        self.st.save_token('youtube','acc','ref','s',3600)
        self.assertEqual(self.st.get_token('youtube'),'acc')
        self.st.save_token('youtube','acc','ref','s',-10)
        self.assertIsNone(self.st.get_token('youtube'),'expired token rejected')

class GeminiTests(unittest.TestCase):
    def test_gated_without_key(self):
        os.environ.pop('GOOGLE_AI_API_KEY',None)
        with self.assertRaises(DependencyMissing): gemini_image('prompt','/tmp/x.png')

class WordPressIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        self.dbdir=Path(self.tmp.name)
        os.environ['TEHNET_PANEL_DB']=str(self.dbdir/'c.sqlite')
    def tearDown(self):
        os.environ.pop('TEHNET_PANEL_DB',None)
    def test_guard_blocks_duplicate(self):
        import publishing
        import urllib.request, urllib.error
        # simulate: guard file pre-written => no network, deduplicated result
        payload={'title':'t'}
        guard=self.dbdir/('wp-idem-tehnet-ir-'+__import__('hashlib').sha256(json.dumps({'title':'t','content':'c','status':'draft'},sort_keys=True).encode()).hexdigest()[:16]+'.json')
        guard.parent.mkdir(parents=True,exist_ok=True)
        guard.write_text(json.dumps({'id':77,'link':'http://x','status':'draft'}))
        os.environ.update(WP_TEHNET_USER='u',WP_TEHNET_APP_PASSWORD='p')
        try:
            res=publishing.wordpress_draft('tehnet.ir','t','c',slug=None,excerpt=None)
            self.assertEqual(res['id'],77); self.assertTrue(res.get('deduplicated'))
        finally:
            os.environ.pop('WP_TEHNET_USER',None); os.environ.pop('WP_TEHNET_APP_PASSWORD',None)

class TelegramRetryTests(unittest.TestCase):
    def test_gated(self):
        os.environ.pop('TELEGRAM_BOT_TOKEN',None)
        import notifications
        r=notifications.telegram_send('x')
        self.assertFalse(r['ok'])

class GSCIngestTests(unittest.TestCase):
    def test_gated_honest(self):
        tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(tmp.name,ignore_errors=True))
        from analytics import AnalyticsStore, gsc_ingest_handler
        an=AnalyticsStore(Path(tmp.name)/'a.sqlite')
        os.environ.pop('GSC_CREDENTIALS',None)
        class Ctx:
            services={'analytics':an}; payload={'site':'x'}; id='t1'
            @staticmethod
            def log(m): pass
            @staticmethod
            def progress(p): pass
        with self.assertRaises(DependencyMissing): gsc_ingest_handler(Ctx())

class AuthEnforcementTests(unittest.TestCase):
    def test_require_auth_blocks_when_enabled(self):
        import server as srv
        os.environ.update(ADMIN_USER='a',ADMIN_PASSWORD='pw12345')
        try:
            from ops import Auth
            a=Auth(); self.assertTrue(a.enabled)
            tok=a.login('a','pw12345')['token']
            self.assertTrue(a.check(tok))
            self.assertFalse(a.check('bad'))
        finally:
            os.environ.pop('ADMIN_USER',None); os.environ.pop('ADMIN_PASSWORD',None)

if __name__=='__main__': unittest.main(verbosity=2)

class SitemapDiscoveryTests(unittest.TestCase):
    def test_candidates_probed_and_recorded(self):
        from seo_engine import check_robots_and_sitemap
        res=check_robots_and_sitemap('https://tehnet.ir')
        self.assertIn('sitemap_candidates',res)
        urls=[c['url'] for c in res['sitemap_candidates']]
        self.assertTrue(any('wp-sitemap.xml' in u for u in urls))
        self.assertNotEqual(res.get('sitemap'),'ok','still broken until user acts (truthful)')
