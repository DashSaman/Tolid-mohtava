import unittest, tempfile, sys, time, shutil, subprocess, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from sync import SyncStore, sync_pair, envelope, correlate, find_claps, enhance_audio_handler, sync_content_handler
from whisper_config import WhisperSettings, rough_overlap, benchmark_handler
from ops import Auth, ArchiveStore, hash_password, verify_password, archive_copy_handler
from store import Store
from media import MediaLibrary
from render import Renders
import avtools
from jobs import JobManager, DependencyMissing

def reader_of(data):
    view=memoryview(data); pos=[0]
    def reader(n):
        if pos[0]>=len(data): return b''
        chunk=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n
        return chunk
    return reader

class SyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ff=avtools.ffmpeg_path()
        if not cls.ff: raise unittest.SkipTest('FFmpeg not available')
        cls.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        # reference: tone with a "clap-like" silence gap at 3s
        cls.ref=Path(cls.tmp.name)/'ref.wav'
        subprocess.run([cls.ff,'-y','-f','lavfi','-i','anoisesrc=d=8:c=pink:r=44100',
                        '-af',"volume=enable='between(t,3,3.4)':volume=0",str(cls.ref)],
                       capture_output=True,check=True)
        # offset copy: same content shifted by +1.2s (pad start with 1.2s silence)
        cls.off=Path(cls.tmp.name)/'off.wav'
        subprocess.run([cls.ff,'-y','-f','lavfi','-i','anullsrc=r=44100:cl=mono:d=1.2',
                        '-i',str(cls.ref),'-filter_complex','[0][1]concat=n=2:v=0:a=1',str(cls.off)],
                       capture_output=True,check=True)
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp.name,ignore_errors=True)
    def test_correlation_finds_known_offset(self):
        offset,conf,method=sync_pair(self.ref,self.off)
        self.assertIsNotNone(offset)
        self.assertAlmostEqual(abs(offset-1.2),0,delta=0.25)
        self.assertGreater(conf,0.4)
    def test_manual_offset_persists(self):
        db=Path(self.tmp.name)/'s.sqlite'
        st=SyncStore(db)
        st.save('c1','m1','ref',1.2,'manual',1.0)
        self.assertEqual(st.for_content('c1')[0]['offset_seconds'],1.2)
        st.save('c1','m1','ref',0.4,'waveform',0.8)
        self.assertEqual(st.for_content('c1')[0]['offset_seconds'],0.4,'upsert per media')
        st.clear('m1')
        self.assertEqual(st.for_content('c1'),[])
    def test_sync_job_needs_two_tracks(self):
        db=Path(self.tmp.name)/'s2.sqlite'
        lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        mgr=JobManager(db,handlers={'sync_content':sync_content_handler},workers=1,
                       services={'media':lib,'sync':SyncStore(db)})
        self.addCleanup(mgr.stop)
        m=lib.ingest(reader_of(self.ref.read_bytes()),'ref.wav','voice')
        j=mgr.enqueue('sync_content',{'content_id':'c1'})
        end=time.time()+30
        while time.time()<end and mgr.get(j['id'])['status'] not in ('completed','failed'): time.sleep(0.05)
        self.assertEqual(mgr.get(j['id'])['status'],'failed')
        self.assertIn('دو تراک',mgr.get(j['id'])['error'])

class EnhanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'e.sqlite'
        self.lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        self.rd=Renders(db,Path(self.tmp.name)/'renders')
        self.mgr=JobManager(db,handlers={'enhance_audio':enhance_audio_handler},workers=1,
                            services={'media':self.lib,'renders':self.rd})
        self.addCleanup(self.mgr.stop)
    @unittest.skipUnless(avtools.ffmpeg_path(),'FFmpeg not available')
    def test_enhance_creates_new_file_raw_untouched(self):
        ff=avtools.ffmpeg_path()
        raw=Path(self.tmp.name)/'voice.wav'
        subprocess.run([ff,'-y','-f','lavfi','-i','sine=frequency=440:duration=2','-ac','1',str(raw)],
                       capture_output=True,check=True)
        m=self.lib.ingest(reader_of(raw.read_bytes()),'voice.wav','voice')
        raw_bytes=raw.read_bytes(); raw.unlink()
        j=self.mgr.enqueue('enhance_audio',{'media_id':m['id']})
        end=time.time()+120
        while time.time()<end and self.mgr.get(j['id'])['status'] not in ('completed','failed'): time.sleep(0.05)
        st=self.mgr.get(j['id'])
        self.assertEqual(st['status'],'completed',st.get('error'))
        self.assertIn('ENHANCED',st['result']['label'])
        self.assertTrue(Path(self.lib.get(m['id'])['path']).exists(),'RAW must remain')
        self.assertTrue(Path(self.rd.get(st['result']['render_id'])['path']).exists())

class WhisperConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        self.ws=WhisperSettings(Path(self.tmp.name)/'w.sqlite')
    def test_model_selection_persists_and_validates(self):
        self.assertEqual(self.ws.whisper_model(),'small','sane default')
        self.ws.set_whisper_model('medium')
        self.assertEqual(WhisperSettings(self.ws.path).whisper_model(),'medium')
        with self.assertRaises(ValueError): self.ws.set_whisper_model('giant')
    def test_rough_overlap_real_signal(self):
        self.assertGreater(rough_overlap('سلام دوستان تنظیم مودم','سلام دوستان تنظیم مودم'),90)
        self.assertLess(rough_overlap('سلام دوستان','خداحافظ همه'),40)

class AuthAndArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        self.db=Path(self.tmp.name)/'a.sqlite'
        self.store=Store(self.db)
        self.lib=MediaLibrary(self.db,Path(self.tmp.name)/'media')
        self.arch=ArchiveStore(self.db)
    def test_password_hash_roundtrip(self):
        h=hash_password('s3cret')
        self.assertTrue(verify_password('s3cret',h))
        self.assertFalse(verify_password('wrong',h))
    def test_auth_env_based_and_rate_limited(self):
        import os
        os.environ['ADMIN_USER']='admin'; os.environ['ADMIN_PASSWORD']='pw12345'
        try:
            a=Auth()
            self.assertTrue(a.enabled)
            self.assertTrue(a.login('admin','pw12345')['token'],'correct login returns a session token')
            bad=[a.login('admin','nope',ip='1.2.3.4') for _ in range(10)]
            self.assertIn('۵ دقیقه',bad[-1]['error'],'rate limit kicks in')
        finally:
            os.environ.pop('ADMIN_USER',None); os.environ.pop('ADMIN_PASSWORD',None)
    def test_auth_disabled_without_env(self):
        self.assertFalse(Auth().enabled)
    @unittest.skipUnless(avtools.ffmpeg_path(),'FFmpeg not available')
    def test_archive_copy_verified_and_approval_gated(self):
        ff=avtools.ffmpeg_path()
        raw=Path(self.tmp.name)/'v.wav'
        subprocess.run([ff,'-y','-f','lavfi','-i','sine=frequency=500:duration=1','-ac','1',str(raw)],
                       capture_output=True,check=True)
        c=self.store.save(dict(title='پروژه آرشیو',brands=['mytel'],body=''))
        m=self.lib.ingest(reader_of(raw.read_bytes()),'v.wav','voice',content_id=c['id'])
        passport=Path(self.tmp.name)/'passport'; passport.mkdir()
        archdir=Path(self.tmp.name)/'arch'
        archdir.mkdir()
        self.arch=ArchiveStore(self.db)
        mgr=JobManager(self.db,handlers={'archive_copy':archive_copy_handler},workers=1,
                       services={'store':self.store,'media':self.lib,'archive':self.arch})
        self.addCleanup(mgr.stop)
        j=mgr.enqueue('archive_copy',{'content_id':c['id'],'passport_path':str(passport)})
        end=time.time()+30
        while time.time()<end and mgr.get(j['id'])['status'] not in ('completed','failed','waiting_approval'): time.sleep(0.05)
        self.assertEqual(mgr.get(j['id'])['status'],'waiting_approval','archive must be approval-gated')
        mgr.decide(j['id'],True)
        end=time.time()+60
        while time.time()<end and mgr.get(j['id'])['status'] not in ('completed','failed'): time.sleep(0.05)
        st=mgr.get(j['id'])
        self.assertEqual(st['status'],'completed',st.get('error'))
        copied=list((passport/'content-factory').rglob('*.wav'))
        if not copied:
            debug=list(passport.rglob('*'))[:12]
            raise AssertionError(f'copied file missing; passport tree: {debug}')
        self.assertEqual(len(copied),1)
        rows=[r for r in self.arch.list() if r['media_id']==m['id']]
        self.assertTrue(rows and rows[0]['checksum_ok']==1)
        # the delete step must NOT have happened
        self.assertTrue(Path(self.lib.get(m['id'])['path']).exists(),'SSD copy must stay until separate approval')

if __name__=='__main__': unittest.main(verbosity=2)
