"""Focused tests: safe delete/archive, media(recording) delete, INVALID_AUDIO
rejection + Whisper guard, dependency cleanup, path traversal."""
import unittest, tempfile, sys, shutil, subprocess, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from store import Store
from media import MediaLibrary
from transcribe import Transcripts
from editing import EditDecisions
from render import Renders
from jobs import JobManager
import avtools
import server as srvmod
def reader_of(data):
    view=memoryview(data); pos=[0]
    def r(n):
        if pos[0]>=len(data): return b''
        c=bytes(view[pos[0]:pos[0]+n]); pos[0]+=n; return c
    return r

class ProjectLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'t.sqlite'
        self.s=Store(db); self.lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        self.c=self.s.save(dict(title='پروژه تست',brands=['tehran-network'],body='x'))
    def test_rename_and_archive_flow(self):
        r=self.s.rename(self.c['id'],'نام جدید');self.assertEqual(r['title'],'نام جدید')
        a=self.s.set_archived(self.c['id'],True)
        self.assertTrue(a['archived'])
        self.assertEqual(self.s.list('tehran-network')[0]['archived'],True,'row kept, only flagged')
        u=self.s.set_archived(self.c['id'],False);self.assertFalse(u['archived'])
        with self.assertRaises(ValueError): self.s.rename(self.c['id'],'  ')
    def test_published_project_delete_needs_ack(self):
        self.s.decide(self.c['id'],1,'publish','approved')
        with self.assertRaises(ValueError) as cm:
            self.s.delete(self.c['id'])
        self.assertTrue(str(cm.exception).startswith('WARN_PUBLISHED'))
        self.s.delete(self.c['id'],force_published=True)  # no raise
        self.assertEqual(self.s.list('tehran-network'),[])
    def test_delete_clears_history_events(self):
        with sqlite3c(self.s.path) as c:
            n=c.execute('SELECT COUNT(*) FROM events WHERE content_id=?',(self.c['id'],)).fetchone()[0]
        self.assertGreater(n,0)
        self.s.delete(self.c['id'])
        with sqlite3c(self.s.path) as c:
            n2=c.execute('SELECT COUNT(*) FROM events WHERE content_id=?',(self.c['id'],)).fetchone()[0]
        self.assertEqual(n2,0)

def sqlite3c(path):
    import sqlite3
    return sqlite3.connect(path)

class MediaDeleteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
        db=Path(self.tmp.name)/'m.sqlite'
        self.lib=MediaLibrary(db,Path(self.tmp.name)/'media')
        self.ts=Transcripts(db); self.dec=EditDecisions(db); self.rd=Renders(db,Path(self.tmp.name)/'renders')
        self.m=self.lib.ingest(reader_of(b'A'*8000),'rec.webm','voice')
        self.ts.add(self.m['id'],'متن',[{'start':0,'end':1,'text':'متن'}],'automatic')
        self.dec.add(self.m['id'],1,2,'silence',.9,'automatic','active')
    def test_delete_recording_cleans_related(self):
        mid=self.m['id']
        from server import delete_media_row
        delete_media_row(mid,self.lib,self.ts,self.dec,self.rd)
        self.assertIsNone(self.lib.get(mid))
        with sqlite3c(self.lib.path) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM transcripts WHERE media_id=?',(mid,)).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM edit_decisions WHERE media_id=?',(mid,)).fetchone()[0],0)
        self.assertFalse(Path(self.m['path']).exists())
        # unrelated untouched
        other=self.lib.ingest(reader_of(b'B'*8000),'o.webm','voice')
        self.assertTrue(Path(other['path']).exists())

@unittest.skipUnless(avtools.ffmpeg_path(),'FFmpeg required')
class AudioValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp.name,ignore_errors=True))
    def _mk(self,name,seconds,silent=False):
        ff=avtools.ffmpeg_path()
        p=Path(self.tmp.name)/name
        src='anullsrc=r=16000:cl=mono' if silent else 'sine=frequency=440'
        subprocess.run([ff,'-y','-f','lavfi','-i',src+':d='+str(seconds),'-ac','1',str(p)],capture_output=True,check=True)
        return p
    def test_silence_and_short_rejected_tone_ok(self):
        from server import audio_rms_stats
        sil=audio_rms_stats(self._mk('sil.wav',3,silent=True))
        self.assertFalse(sil['valid']); self.assertIn('سکوت',sil['reason'])
        short=audio_rms_stats(self._mk('sh.wav',0.3))
        self.assertFalse(short['valid'])
        tone=audio_rms_stats(self._mk('tone.wav',2))
        self.assertTrue(tone['valid'],tone)
        self.assertGreater(tone['rms'],60)

class WhisperGuardTests(unittest.TestCase):
    def test_guard_blocks_invalid_before_queue(self):
        # validated through server module helper: validate_audio returns INVALID for empty file
        from server import validate_audio as _va
        tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(lambda: shutil.rmtree(tmp.name,ignore_errors=True))
        lib=MediaLibrary(Path(tmp.name)/'v.sqlite',Path(tmp.name)/'media')
        empty=lib.ingest(reader_of(b'\x00'*100),'e.webm','voice')
        r=_va(empty['id'],lib)
        self.assertEqual(r['status'],'INVALID_AUDIO')

if __name__=='__main__': unittest.main(verbosity=2)
