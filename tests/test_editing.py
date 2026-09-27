import unittest, tempfile, sys, time, shutil, subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from media import MediaLibrary
from transcribe import Transcripts
from editing import EditDecisions, analyze, detect_fillers_and_repeats, report_lines, fa_time, edit_detect_handler, scan_silences
from store import Store
import avtools
from jobs import JobManager

def reader_of(data):
    view=memoryview(data); pos=[0]
    def reader(n):
        if pos[0]>=len(data): return b''
        chunk=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n
        return chunk
    return reader

class EditingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'test.sqlite'
        self.lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        self.ts=Transcripts(db)
        self.dec=EditDecisions(db)
        self.store=Store(db)
    def media(self,audio=b'x'*32):
        return self.lib.ingest(reader_of(audio),'rec.wav','voice')
    def test_fillers_and_repeats_detection(self):
        segs=[{'start':0,'end':1,'text':'اِ'},
              {'start':1,'end':4,'text':'برای نصب باید تنظیمات شبکه را باز کنید'},
              {'start':4.2,'end':7.4,'text':'برای نصب باید تنظیمات شبکه رو باز کنید'},
              {'start':7.4,'end':9,'text':'بعد از آن ذخیره بزنید'}]
        f,r=detect_fillers_and_repeats(segs)
        self.assertEqual(len(f),1); self.assertAlmostEqual(f[0][0],0)
        self.assertEqual(len(r),1); self.assertAlmostEqual(r[0][0],4.2)
    def test_analyze_creates_conservative_decisions(self):
        m=self.media()
        t=self.ts.add(m['id'],'اِ سلام\nاین جمله اول است\nاین جمله اول است\nپایان',
                      [{'start':0,'end':0.5,'text':'اِ'},
                       {'start':0.5,'end':2,'text':'سلام'},
                       {'start':2,'end':5,'text':'این جمله اول است'},
                       {'start':5.1,'end':8,'text':'این جمله اول است'},
                       {'start':8,'end':9,'text':'پایان'}],'automatic')
        summary=analyze(self.lib.get(m['id']),t['segments'],t['revision'],self.dec)
        rows=self.dec.list(m['id'])
        codes={r['reason_code']:r['state'] for r in rows}
        self.assertEqual(codes.get('filler'),'active','clear filler auto-cuts')
        self.assertEqual(codes.get('repeat'),'proposed','repeat only proposed')
        self.assertGreaterEqual(summary['created'],2)
    def test_states_restore_dismiss_and_manual(self):
        m=self.media()
        d=self.dec.add(m['id'],1,2,'silence',0.9,'automatic','active')
        self.assertEqual(self.dec.set_state(d['id'],'restored')['state'],'restored')
        self.assertEqual(self.dec.set_state(d['id'],'restored')['state'],'restored','idempotent same-state')
        self.assertEqual(self.dec.set_state(d['id'],'dismissed')['state'],'dismissed')
        man=self.dec.add(m['id'],3,4,'manual',1.0,'manual','active')
        self.assertEqual(man['origin'],'manual')
        with self.assertRaises(ValueError): self.dec.add(m['id'],5,5,'manual',1.0,'manual','active')
        with self.assertRaises(ValueError): self.dec.set_state(d['id'],'nope')
    def test_timeline_merges_and_respects_restore(self):
        m=self.media()
        a=self.dec.add(m['id'],0,1,'silence',0.9,'automatic','active')
        self.dec.add(m['id'],1.5,2.5,'silence',0.9,'automatic','active')
        self.dec.add(m['id'],2.4,3.5,'silence',0.9,'automatic','active')
        self.dec.add(m['id'],9,10,'silence',0.9,'automatic','restored')
        t=self.dec.timeline(m['id'])
        self.assertEqual(t,[(0,1),(1.5,3.5)],'overlaps merged, restored excluded')
        self.dec.set_state(a['id'],'restored')
        self.assertEqual(self.dec.timeline(m['id']),[(1.5,3.5)])
    def test_rerun_respects_user_verdicts(self):
        m=self.media()
        segs=[{'start':0,'end':0.4,'text':'اِ'},{'start':0.4,'end':2,'text':'متن'}]
        t=self.ts.add(m['id'],'اِ متن',segs,'automatic')
        analyze(self.lib.get(m['id']),segs,1,self.dec)
        filler=[d for d in self.dec.list(m['id']) if d['reason_code']=='filler'][0]
        self.dec.set_state(filler['id'],'restored')
        analyze(self.lib.get(m['id']),segs,1,self.dec)
        filler_after=[d for d in self.dec.list(m['id']) if d['reason_code']=='filler']
        self.assertEqual(len(filler_after),1,'user restore must survive re-analysis')
        self.assertEqual(filler_after[0]['state'],'restored')
    def test_report_lines_persian(self):
        m=self.media()
        self.dec.add(m['id'],804,808,'long_pause',0.9,'automatic','active')
        lines=report_lines(self.dec,m['id'])
        self.assertEqual(len(lines),1)
        self.assertIn('۱۳:۲۴',lines[0]['span'])
        self.assertIn('سکوت طولانی',lines[0]['reason'])
        self.assertEqual(lines[0]['state_fa'],'حذف شد')
    def test_manual_decision_report_and_state(self):
        m=self.media()
        self.dec.add(m['id'],61,64,'manual',1.0,'manual','active')
        lines=report_lines(self.dec,m['id'])
        self.assertEqual(lines[0]['origin'],'manual')

@unittest.skipUnless(avtools.ffmpeg_path(),'FFmpeg not available on this machine')
class SilenceScanIntegration(unittest.TestCase):
    def test_real_ffmpeg_detects_inserted_silence(self):
        ff=avtools.ffmpeg_path()
        tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(tmp.name,ignore_errors=True))
        wav=Path(tmp.name)/'tone.wav'
        # 1s tone, 1.5s silence, 1s tone  -> silencedetect must find the middle
        subprocess.run([ff,'-y','-f','lavfi','-i','sine=frequency=440:duration=1',
                        '-f','lavfi','-i','anullsrc=r=44100:cl=mono:d=1.5',
                        '-f','lavfi','-i','sine=frequency=440:duration=1',
                        '-filter_complex','[0][1][2]concat=n=3:v=0:a=1','-ac','1',str(wav)],
                       capture_output=True,timeout=60,check=True)
        sil=scan_silences(wav)
        self.assertTrue(sil,'expected at least one silence range')
        total=sum(d for _,_,d in sil)
        self.assertGreater(total,0.8,'~1.5s inserted silence must be found')
        wav.unlink()

class EditDetectJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'test.sqlite'
        self.lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        self.ts=Transcripts(db)
        self.dec=EditDecisions(db)
        self.mgr=JobManager(db,handlers={'edit_detect':edit_detect_handler},workers=1,
                            services={'media':self.lib,'transcripts':self.ts,'decisions':self.dec})
        self.addCleanup(self.mgr.stop)
    def wait(self,jid,timeout=10):
        end=time.time()+timeout
        while time.time()<end:
            j=self.mgr.get(jid)
            if j['status'] in ('completed','failed','cancelled','waiting_approval'): return j
            time.sleep(0.02)
        raise AssertionError('job did not settle')
    def test_handler_without_transcript_still_scans_silence(self):
        view=memoryview(b'x'*64); pos=[0]
        def reader(n):
            if pos[0]>=64: return b''
            c=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n; return c
        m=self.lib.ingest(reader,'rec.wav','voice')
        j=self.mgr.enqueue('edit_detect',{'media_id':m['id']})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        self.assertEqual(j['result']['transcript_revision'],None)

if __name__=='__main__': unittest.main(verbosity=2)
