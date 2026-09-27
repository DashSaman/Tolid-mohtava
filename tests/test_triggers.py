import unittest, tempfile, sys, time, shutil, json, subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from store import Store
from media import MediaLibrary
from editing import EditDecisions
from render import Renders, render_cut_handler, probe_duration
from triggers import publish_dryrun_handler, on_publish_approved, build_dryrun, format_note
import avtools
from jobs import JobManager

def reader_of(data):
    view=memoryview(data); pos=[0]
    def reader(n):
        if pos[0]>=len(data): return b''
        chunk=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n
        return chunk
    return reader

class TriggerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'test.sqlite'
        self.store=Store(db)
        self.dryroot=Path(self.tmp.name)/'dryrun'
        self.mgr=JobManager(db,handlers={'publish_dryrun':publish_dryrun_handler},workers=1,
                            services={'store':self.store,'dryrun_root':str(self.dryroot)})
        self.addCleanup(self.mgr.stop)
    def wait(self,jid,timeout=10):
        end=time.time()+timeout
        while time.time()<end:
            j=self.mgr.get(jid)
            if j['status'] in ('completed','failed','cancelled','waiting_approval'): return j
            time.sleep(0.02)
        raise AssertionError('job did not settle')
    def content(self,**kw):
        return self.store.save(dict(title='آزمایش انتشار',brands=['tehran-network'],
                                    body='متن تأییدشده',transcript='متن واقعی ضبط',platform='YouTube',**kw))
    def test_publish_approval_enqueues_single_dryrun(self):
        c=self.content()
        j1=on_publish_approved(self.mgr,c['id'],1)
        j2=on_publish_approved(self.mgr,c['id'],1)
        self.assertEqual(j1['id'],j2['id'],'duplicate approval must not duplicate jobs')
        j1=self.wait(j1['id'])
        self.assertEqual(j1['status'],'completed',j1.get('error'))
        self.assertEqual(j1['result']['mode'],'dry_run')
        art=Path(j1['result']['artifact'])
        self.assertTrue(art.exists())
        pkg=json.loads(art.read_text(encoding='utf-8'))
        self.assertEqual(pkg['mode'],'dry_run')
        self.assertIn('هیچ انتشار خارجی',pkg['note'])
        self.assertEqual(pkg['brands'],{'tehran-network':'tehnet.ir'})
        self.assertIn('فصل‌بندی',pkg['sections']['platform_adaptation'])
        self.assertEqual(pkg['warnings'],[])
    def test_new_revision_gets_new_dryrun(self):
        c=self.content()
        j1=on_publish_approved(self.mgr,c['id'],1)
        self.wait(j1['id'])
        c['body']='متن نسخه دو'
        c2=self.store.save(c)
        self.assertEqual(c2['revision'],2)
        j2=on_publish_approved(self.mgr,c2['id'],2)
        self.assertNotEqual(j1['id'],j2['id'])
        r=self.wait(j2['id'])
        self.assertEqual(r['result']['revision'],2)
    def test_stale_revision_rejected(self):
        c=self.content()
        with self.assertRaises(ValueError): build_dryrun(self.store,c['id'],99)
        empty=self.store.save(dict(title='بدون متن',brands=['mytel'],body=''))
        pkg=build_dryrun(self.store,empty['id'],1)
        self.assertTrue(any('خالی' in w for w in pkg['warnings']),'empty body must warn honestly')
    def test_platform_notes_differ(self):
        self.assertNotEqual(format_note('Website'),format_note('Telegram'))

class FinalRenderApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'test.sqlite'
        self.lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        self.dec=EditDecisions(db)
        self.rd=Renders(db,Path(self.tmp.name)/'renders')
        self.mgr=JobManager(db,handlers={'render_cut':render_cut_handler},workers=1,
                            services={'media':self.lib,'decisions':self.dec,'renders':self.rd})
        self.addCleanup(self.mgr.stop)
    def wait(self,jid,timeout=120):
        end=time.time()+timeout
        while time.time()<end:
            j=self.mgr.get(jid)
            if j['status'] in ('completed','failed','cancelled','waiting_approval'): return j
            time.sleep(0.05)
        raise AssertionError('job did not settle')
    @unittest.skipUnless(avtools.ffmpeg_path(),'FFmpeg not available')
    def test_final_render_requires_approval_then_renders(self):
        ff=avtools.ffmpeg_path()
        raw=Path(self.tmp.name)/'fx.mp4'
        subprocess.run([ff,'-y','-f','lavfi','-i','testsrc=duration=3:size=320x240:rate=15',
                        '-f','lavfi','-i','sine=frequency=440:duration=3','-shortest',
                        '-pix_fmt','yuv420p',str(raw)],capture_output=True,timeout=60,check=True)
        m=self.lib.ingest(reader_of(raw.read_bytes()),'fx.mp4','screen',mime='video/mp4')
        raw.unlink()
        j=self.mgr.enqueue('render_cut',{'media_id':m['id'],'kind':'final'})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'waiting_approval','final render must wait for explicit approval')
        self.assertEqual(self.rd.list(m['id']),[],'nothing rendered before approval')
        d=self.mgr.decide(j['id'],True)
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        self.assertEqual(j['result']['label'],'FINAL')

if __name__=='__main__': unittest.main(verbosity=2)
