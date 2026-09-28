import unittest, tempfile, sys, time, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from notifications import Notifications, telegram_send
from jobs import JobManager

class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        self.n=Notifications(Path(self.tmp.name)/'n.sqlite')
    def test_add_list_unread_markread(self):
        self.n.add('job_failed','رندر ناموفق بود','خطای شبکه','job1')
        self.n.add('approval_needed','رندر نهایی منتظر تأیید','', 'job2')
        self.assertEqual(self.n.unread_count(),2)
        items=self.n.list()
        self.assertEqual(items[0]['kind'],'approval_needed','newest first')
        self.n.mark_read(items[0]['id'])
        self.assertEqual(self.n.unread_count(),1)
        self.n.mark_read()
        self.assertEqual(self.n.unread_count(),0)
    def test_telegram_without_credentials_is_honest(self):
        r=telegram_send('test')
        self.assertFalse(r['ok'])
        self.assertIn('BLOCKED_BY_CREDENTIAL',r.get('blocked',''))

if __name__=='__main__': unittest.main(verbosity=2)
