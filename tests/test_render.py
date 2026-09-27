import unittest, tempfile, sys, time, shutil, subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from media import MediaLibrary
from editing import EditDecisions
from render import Renders, keep_ranges, build_filter, render_cut_handler, probe_duration, build_cmd
import avtools
from jobs import JobManager, DependencyMissing

def reader_of(data):
    view=memoryview(data); pos=[0]
    def reader(n):
        if pos[0]>=len(data): return b''
        chunk=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n
        return chunk
    return reader

class RenderUnitTests(unittest.TestCase):
    def test_keep_ranges_complement_and_merge(self):
        self.assertEqual(keep_ranges([(1,2),(3.5,4.5)],6),[(0,1),(2,3.5),(4.5,6)])
        self.assertEqual(keep_ranges([],6),[(0,6)])
        self.assertEqual(keep_ranges([(0,6)],6),[])
        self.assertEqual(keep_ranges([(0,2),(1,3)],6),[(3,6)])
        self.assertEqual(keep_ranges([(-5,1)],4),[(1,4)])
    def test_build_filter_counts(self):
        f=build_filter([(0,1),(2,3)],has_video=True)
        self.assertIn('concat=n=2:v=1:a=0[vout]',f)
        self.assertIn('atrim=start=2.000:end=3.000',f)
        fa=build_filter([(1,2)],has_video=False)
        self.assertIn('concat=n=1:v=0:a=1[aout]',fa)
        self.assertNotIn('[0:v]',fa,'audio-only render must not map video')

def make_fixture_video(ff,dst,with_gap=False):
    """6s testsrc+tone; optionally re-encode silence gap 1-2s to prove cuts apply."""
    cmd=[ff,'-y','-f','lavfi','-i','testsrc=duration=6:size=320x240:rate=15',
         '-f','lavfi','-i','sine=frequency=440:duration=6','-shortest','-pix_fmt','yuv420p',str(dst)]
    subprocess.run(cmd,capture_output=True,timeout=120,check=True)

@unittest.skipUnless(avtools.ffmpeg_path() and avtools.ffprobe_path(),'FFmpeg not available')
class RenderPipelineTests(unittest.TestCase):
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
        raise AssertionError('render job did not settle')
    def test_preview_final_versions_apply_cuts(self):
        ff=avtools.ffmpeg_path()
        raw=Path(self.tmp.name)/'fixture.mp4'
        make_fixture_video(ff,raw)
        m=self.lib.ingest(reader_of(raw.read_bytes()),'fixture.mp4','screen',mime='video/mp4')
        raw.unlink()
        # two clear cuts: 1-2s and 3.5-4.5s => output ~4.0s
        self.dec.add(m['id'],1,2,'manual',1.0,'manual','active')
        d2=self.dec.add(m['id'],3.5,4.5,'manual',1.0,'manual','active')
        j=self.mgr.enqueue('render_cut',{'media_id':m['id'],'kind':'preview'})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        self.assertEqual(j['result']['label'],'EDIT V1')
        out=Path(self.rd.get(j['result']['render_id'])['path'])
        self.assertTrue(out.exists() and out.stat().st_size>0)
        dur=probe_duration(out)
        self.assertAlmostEqual(dur,4.0,delta=0.4)
        # restore one cut -> preview V2 is longer
        self.dec.set_state(d2['id'],'restored')
        j2=self.mgr.enqueue('render_cut',{'media_id':m['id'],'kind':'preview'})
        j2=self.wait(j2['id'])
        self.assertEqual(j2['status'],'completed',j2.get('error'))
        out2=Path(self.rd.get(j2['result']['render_id'])['path'])
        self.assertAlmostEqual(probe_duration(out2),5.0,delta=0.4)
        labels=[r['label'] for r in self.rd.list(m['id'])]
        self.assertEqual(labels,['EDIT V1','EDIT V2'])
        # final render is approval-gated
        j3=self.mgr.enqueue('render_cut',{'media_id':m['id'],'kind':'final'})
        j3=self.wait(j3['id'])
        self.assertEqual(j3['status'],'waiting_approval','final must wait for explicit approval')
        self.mgr.decide(j3['id'],True)
        j3=self.wait(j3['id'])
        self.assertEqual(j3['status'],'completed',j3.get('error'))
        self.assertEqual(j3['result']['label'],'FINAL')
        enc=self.rd.get(j3['result']['render_id'])['encoder']
        self.assertTrue(enc.startswith('h264_nvenc') or enc=='libx264',enc)
        for row in self.rd.list(m['id']):
            self.assertNotEqual(Path(row['path']),Path(self.lib.get(m['id'])['path']),'original must stay untouched')
            self.assertTrue(Path(row['path']).exists())
    def test_missing_ffmpeg_is_honest(self):
        import render as rmod
        orig=rmod.avtools.ffmpeg_path
        rmod.avtools.ffmpeg_path=lambda: None
        try:
            m=self.lib.ingest(reader_of(b'x'*32),'a.mp4','screen')
            j=self.mgr.enqueue('render_cut',{'media_id':m['id']})
            j=self.wait(j['id'])
            self.assertEqual(j['status'],'failed')
            self.assertTrue(j['error'].startswith('BLOCKED_BY_DEPENDENCY'),j.get('error'))
        finally:
            rmod.avtools.ffmpeg_path=orig
    def test_all_cut_is_rejected(self):
        ff=avtools.ffmpeg_path()
        raw=Path(self.tmp.name)/'fixture.mp4'
        make_fixture_video(ff,raw)
        m=self.lib.ingest(reader_of(raw.read_bytes()),'fixture.mp4','screen',mime='video/mp4')
        raw.unlink()
        self.dec.add(m['id'],0,10_000,'manual',1.0,'manual','active')
        j=self.mgr.enqueue('render_cut',{'media_id':m['id']})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'failed')
        self.assertIn('خالی',j['error'])

if __name__=='__main__': unittest.main(verbosity=2)
