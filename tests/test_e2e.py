"""Critical end-to-end fixture: idea -> voice -> transcript -> edit -> restore ->
render preview -> final (approved) -> publish dry-run -> archive integrity.

Everything runs locally through the real job system and real FFmpeg.
The only substituted part is the speech engine (fake faster-whisper) so the
test is deterministic and never downloads models. No external publish happens.
"""
import unittest, tempfile, sys, time, shutil, subprocess, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from store import Store
from media import MediaLibrary
from transcribe import Transcripts, transcribe_audio_handler
from editing import EditDecisions, edit_detect_handler
from render import Renders, render_cut_handler, probe_duration
from triggers import publish_dryrun_handler, on_publish_approved
import avtools, transcribe as transcribe_mod
from jobs import JobManager

def reader_of(data):
    view=memoryview(data); pos=[0]
    def reader(n):
        if pos[0]>=len(data): return b''
        chunk=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n
        return chunk
    return reader

@unittest.skipUnless(avtools.ffmpeg_path() and avtools.ffprobe_path(),'FFmpeg not available')
class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root=Path(cls.tmp.name)
        db=root/'e2e.sqlite'
        cls.store=Store(db)
        cls.lib=MediaLibrary(db,root/'media')
        cls.ts=Transcripts(db)
        cls.dec=EditDecisions(db)
        cls.rd=Renders(db,root/'renders')
        cls.dryroot=root/'dryrun'
        cls.handlers={'transcribe_audio':transcribe_audio_handler,'edit_detect':edit_detect_handler,
                      'render_cut':render_cut_handler,'publish_dryrun':publish_dryrun_handler}
        cls.mgr=JobManager(db,handlers=cls.handlers,workers=1,
                           services={'media':cls.lib,'transcripts':cls.ts,'decisions':cls.dec,
                                     'renders':cls.rd,'store':cls.store,'dryrun_root':str(cls.dryroot)})
        # fixture audio: 1s tone, 1.5s silence, 1s tone, 1s tone, 1.5s tone
        cls.wav=root/'e2e-voice.wav'
        ff=avtools.ffmpeg_path()
        subprocess.run([ff,'-y','-f','lavfi','-i','sine=frequency=440:duration=1',
                        '-f','lavfi','-i','anullsrc=r=44100:cl=mono:d=1.5',
                        '-f','lavfi','-i','sine=frequency=440:duration=3.5',
                        '-filter_complex','[0][1][2]concat=n=3:v=0:a=1','-ac','1',str(cls.wav)],
                       capture_output=True,timeout=60,check=True)
        cls._orig=(transcribe_mod.engine_available,transcribe_mod.run_engine)
        transcribe_mod.engine_available=lambda: True
        transcribe_mod.run_engine=lambda path,segments_cb=None,model_size='small':{
            'engine':{'name':'fake-whisper','device':'cpu','model':model_size},'language':'fa','duration':6.0,
            'segments':[{'start':0.0,'end':1.0,'text':'شروع آموزش'},
                        {'start':1.0,'end':2.5,'text':'این بخش سکوت است'},
                        {'start':2.5,'end':3.5,'text':'نصب را باز می‌کنیم'},
                        {'start':3.5,'end':3.8,'text':'اِ'},
                        {'start':3.8,'end':5.0,'text':'تنظیمات را ذخیره کنید'},
                        {'start':5.0,'end':6.0,'text':'تنظیمات را ذخیره کنید'}],
            'text':'شروع آموزش\nاین بخش سکوت است\nنصب را باز می‌کنیم\nاِ\nتنظیمات را ذخیره کنید\nتنظیمات را ذخیره کنید'}
    @classmethod
    def tearDownClass(cls):
        cls.mgr.stop()
        transcribe_mod.engine_available,transcribe_mod.run_engine=cls._orig
        shutil.rmtree(cls.tmp.name,ignore_errors=True)
    def settle(self,jid,timeout=180):
        end=time.time()+timeout
        while time.time()<end:
            j=self.mgr.get(jid)
            if j['status'] in ('completed','failed','cancelled','waiting_approval'): return j
            time.sleep(0.05)
        raise AssertionError('job did not settle: '+jid)
    def test_full_pipeline(self):
        # 1) project idea
        c=self.store.save(dict(title='آموزش تنظیم مودم',brands=['tehran-network'],platform='YouTube',body=''))
        # 2) voice ingest + transcription
        voice=self.lib.ingest(reader_of(self.wav.read_bytes()),'voice.wav','voice',content_id=c['id'],mime='audio/wav')
        j=self.settle(self.mgr.enqueue('transcribe_audio',{'media_id':voice['id']})['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        self.assertEqual(self.ts.get(voice['id'])['revision'],1)
        # 3) script written, then approvals on revision 1
        c['body']='سناریوی کامل آموزش'
        c2=self.store.save(c)
        self.store.decide(c2['id'],c2['revision'],'script','approved')
        # 4) automatic edit decisions (silence + filler active, repeat proposed)
        j=self.settle(self.mgr.enqueue('edit_detect',{'media_id':voice['id']})['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        active=self.dec.timeline(voice['id'])
        self.assertEqual(len(active),2,'filler + silence should be active cuts')
        self.assertAlmostEqual(sum(e-s for s,e in active),1.8,delta=0.15)
        # 5) restore the silence cut (non-destructive restore)
        silenced=[d for d in self.dec.list(voice['id'],'active') if d['reason_code']=='long_pause'][0]
        self.dec.set_state(silenced['id'],'restored')
        self.assertEqual(len(self.dec.timeline(voice['id'])),1)
        # 6) preview render reflects the remaining cut
        j=self.settle(self.mgr.enqueue('render_cut',{'media_id':voice['id'],'kind':'preview'})['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        v1=self.rd.get(j['result']['render_id'])
        self.assertAlmostEqual(v1['duration'],5.7,delta=0.4)
        self.assertEqual(v1['label'],'EDIT V1')
        # 7) publish approval triggers exactly one dry-run; double-click is safe
        def approve_publish(cid,rev):
            before=self.store.get(cid); prev=before['publish_status']
            item=self.store.decide(cid,rev,'publish','approved')
            if prev!='approved': return on_publish_approved(self.mgr,cid,rev)
            return None
        dj=approve_publish(c2['id'],c2['revision'])
        dj=self.settle(dj['id'])
        self.assertEqual(dj['status'],'completed',dj.get('error'))
        pkg=json.loads(Path(dj['result']['artifact']).read_text(encoding='utf-8'))
        self.assertEqual(pkg['mode'],'dry_run')
        self.assertEqual(pkg['title'],'آموزش تنظیم مودم')
        # duplicate approval click does not create another job
        self.assertIsNone(approve_publish(c2['id'],c2['revision']))
        self.assertEqual(len([x for x in self.mgr.list(limit=200) if x['kind']=='publish_dryrun']),1)
        # 8) final render waits for approval, then renders
        fj=self.mgr.enqueue('render_cut',{'media_id':voice['id'],'kind':'final'})
        fj=self.settle(fj['id'])
        self.assertEqual(fj['status'],'waiting_approval')
        self.mgr.decide(fj['id'],True)
        fj=self.settle(fj['id'])
        self.assertEqual(fj['status'],'completed',fj.get('error'))
        self.assertEqual(fj['result']['label'],'FINAL')
        # 9) archive integrity: original untouched, checksum still valid
        self.assertTrue(self.lib.verify(voice['id']))
        self.assertEqual(len(self.rd.list(voice['id'])),2)
        self.assertEqual(len(self.ts.list(voice['id'])),1)
        # job history survived everything
        self.assertEqual(len(self.mgr.list(limit=200)),5)

if __name__=='__main__': unittest.main(verbosity=2)
