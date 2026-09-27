import unittest, tempfile, sys, time, hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from media import MediaLibrary, KINDS
from transcribe import Transcripts, transcribe_audio_handler
from store import Store
import transcribe as transcribe_mod
from jobs import JobManager

def reader_of(data):
    view=memoryview(data); pos=[0]
    def reader(n):
        if pos[0]>=len(data): return b''
        chunk=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n
        return chunk
    return reader

class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'test.sqlite'
        self.lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        self.store=Store(db)
        self.ts=Transcripts(db)
    def content(self):
        return self.store.save(dict(title='آزمایش رسانه',brands=['tehran-network'],body='متن'))
    def test_ingest_registers_metadata_and_immutable_copy(self):
        data='سلام ویدیو آزمایشی'.encode()
        row=self.lib.ingest(reader_of(data),'voice note.wav','voice',mime='audio/wav')
        self.assertEqual(row['size'],len(data))
        self.assertEqual(row['sha256'],hashlib.sha256(data).hexdigest())
        p=Path(row['path'])
        self.assertTrue(p.exists() and p.parent.name=='media')
        self.assertEqual(p.read_bytes(),data)
        self.assertTrue(self.lib.verify(row['id']))
        self.assertEqual(self.lib.get(row['id'])['kind'],'voice')
    def test_kind_content_link_and_size_limit(self):
        data=b'x'*10
        c=self.content()
        row=self.lib.ingest(reader_of(data),'a.wav','screen',content_id=c['id'])
        self.assertEqual(self.lib.list(content_id=c['id'])[0]['id'],row['id'])
        with self.assertRaises(ValueError): self.lib.ingest(reader_of(data),'a.wav','wrong')
        with self.assertRaises(ValueError): self.lib.ingest(reader_of(data),'a.wav','voice',content_id='missing')
        with self.assertRaises(ValueError): self.lib.ingest(reader_of(b''),'a.wav','voice')
        with self.assertRaises(ValueError): self.lib.ingest(reader_of(b'12345'),'tiny.bin','voice',size_limit=3)
        self.assertFalse(Path(self.lib.get(row['id'])['path']).exists() is False)
    def test_transcript_versions_and_validation(self):
        t1=self.ts.add('m1','متن اول',[{'start':0,'end':1,'text':'متن اول'}],'manual_import')
        t2=self.ts.add('m1','متن دوم',[{'start':0,'end':2,'text':'متن دوم'}],'automatic',engine={'name':'fake'})
        self.assertEqual(t1['revision'],1); self.assertEqual(t2['revision'],2)
        self.assertEqual(self.ts.get('m1')['revision'],2,'latest by default')
        self.assertEqual(self.ts.get('m1',1)['text'],'متن اول')
        self.assertEqual(len(self.ts.list('m1')),2)
        self.assertEqual(self.ts.get('m1',2)['engine']['name'],'fake')
        with self.assertRaises(ValueError): self.ts.add('m1','  ',[],'manual_import')

class TranscribeJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'test.sqlite'
        self.lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        self.ts=Transcripts(db)
        self.mgr=JobManager(db,handlers={'transcribe_audio':transcribe_audio_handler},
                            workers=1,services={'media':self.lib,'transcripts':self.ts})
        self.addCleanup(self.mgr.stop)
        self._orig=(transcribe_mod.engine_available,transcribe_mod.run_engine)
        self.addCleanup(lambda: transcribe_mod.__dict__.update(engine_available=self._orig[0],run_engine=self._orig[1]))
    def wait(self,jid,timeout=10):
        end=time.time()+timeout
        while time.time()<end:
            j=self.mgr.get(jid)
            if j['status'] in ('completed','failed','cancelled','waiting_approval'): return j
            time.sleep(0.02)
        raise AssertionError('job did not settle')
    def test_fake_engine_produces_versioned_transcript(self):
        data=b'fake-audio-bytes'
        row=self.lib.ingest(reader_of(data),'rec.wav','voice')
        transcribe_mod.engine_available=lambda: True
        def fake_run(path,segments_cb=None,model_size='small'):
            segments_cb(60)
            return {'engine':{'name':'fake','device':'cpu','model':model_size},'language':'fa','duration':4.0,
                    'segments':[{'start':0.0,'end':2.0,'text':'سلام'},{'start':2.0,'end':4.0,'text':'این یک آزمایش است'}],
                    'text':'سلام\nاین یک آزمایش است'}
        transcribe_mod.run_engine=fake_run
        j=self.mgr.enqueue('transcribe_audio',{'media_id':row['id']})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'completed',j.get('error'))
        self.assertEqual(j['result']['revision'],1)
        t=self.ts.get(row['id'])
        self.assertEqual(t['text'],'سلام\nاین یک آزمایش است')
        self.assertEqual(len(t['segments']),2)
        self.assertEqual(t['source'],'automatic')
        j2=self.mgr.enqueue('transcribe_audio',{'media_id':row['id']})
        self.wait(j2['id'])
        self.assertEqual(self.ts.get(row['id'])['revision'],2,'rerun must add version, not overwrite')
        self.assertEqual(len(self.ts.list(row['id'])),2)
    def test_missing_engine_is_honest_blocker(self):
        row=self.lib.ingest(reader_of(b'audio'),'rec.wav','voice')
        transcribe_mod.engine_available=lambda: False
        j=self.mgr.enqueue('transcribe_audio',{'media_id':row['id']})
        j=self.wait(j['id'])
        self.assertEqual(j['status'],'failed')
        self.assertTrue(j['error'].startswith('BLOCKED_BY_DEPENDENCY'),j.get('error'))
        self.assertEqual(self.ts.list(row['id']),[],'no fake transcript may exist')
    def test_missing_media_fails(self):
        transcribe_mod.engine_available=lambda: True
        j=self.mgr.enqueue('transcribe_audio',{'media_id':'nope'})
        self.assertEqual(self.wait(j['id'])['status'],'failed')

if __name__=='__main__': unittest.main(verbosity=2)
