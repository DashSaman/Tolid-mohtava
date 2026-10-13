import tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from jobs import JobManager
from store import Store
from media import MediaLibrary
from render import Renders
from handlers import build_handlers

class YouTubeApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);db=root/'test.sqlite'
        self.store=Store(db);self.media=MediaLibrary(db,root/'media');self.renders=Renders(db,root/'renders')
        self.item=self.store.save({'title':'آموزش VLAN','brands':['tehran-network'],'body':'متن تأییدشده'})
        self.mgr=JobManager(db,build_handlers(),workers=1,services={'store':self.store,'media':self.media,'renders':self.renders})
        self.addCleanup(self.mgr.stop)
    def test_private_upload_requires_explicit_job_approval(self):
        import time
        j=self.mgr.enqueue('youtube_upload',{'content_id':self.item['id'],'revision':1,'render_id':'missing'})
        for _ in range(100):
            row=self.mgr.get(j['id'])
            if row['status'] not in ('queued','running'):break
            time.sleep(.02)
        self.assertEqual(row['status'],'waiting_approval')
        self.assertIn('خصوصی',row['result']['question'])
    def test_upload_never_accepts_stale_revision(self):
        import time
        j=self.mgr.enqueue('youtube_upload',{'content_id':self.item['id'],'revision':0,'render_id':'missing','approved':True})
        for _ in range(100):
            row=self.mgr.get(j['id'])
            if row['status'] not in ('queued','running'):break
            time.sleep(.02)
        self.assertEqual(row['status'],'failed')
        self.assertIn('نسخه',row['error'])
