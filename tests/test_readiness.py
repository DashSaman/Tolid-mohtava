"""Readiness regressions: configured providers, OAuth and reachable integrations."""
import io,json,os,socket,subprocess,sys,tempfile,time,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'outputs/panel'))
from providers import OAuthStore,oauth_callback,OAUTH_PROVIDERS
from integrations import ga4_fetch

class Provider(BaseHTTPRequestHandler):
    def do_GET(self):
        body=json.dumps({'data':[{'id':'test-model'}]}).encode()
        self.send_response(200);self.end_headers();self.wfile.write(body)
    def log_message(self,*args): pass

class ReadinessHTTP(unittest.TestCase):
    def test_job_counts_and_status_filter_include_older_failures(self):
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(Path(self.tmp.name)/'test.sqlite')) as c:
            c.executemany('INSERT INTO jobs(id,kind,payload,status,logs,created_at) VALUES(?,?,?,?,?,?)',
                [(f'history-fixture-{i}','fixture','{}','completed','[]','2026-10-13T00:00:00') for i in range(120)]+
                [('older-filtered-failure','fixture','{}','failed','[]','2020-01-01T00:00:00')])
            c.commit()
        self.assertNotIn('older-filtered-failure',[j['id'] for j in self.api('/api/jobs')[1]])
        code,counts=self.api('/api/jobs/counts');self.assertEqual(code,200,counts)
        self.assertGreaterEqual(counts['failed'],1)
        self.assertIn('older-filtered-failure',[j['id'] for j in self.api('/api/jobs?status=failed&limit=500')[1]])
        self.assertEqual(self.api('/api/jobs?limit=10000')[0],400)
    def test_auto_edit_api_reports_missing_inputs_and_subtitle_format(self):
        self.assertEqual(self.api('/api/auto-edit?media_id=missing'),(200,None))
        for kind,payload in [('auto_edit_video',{'media_id':'missing'}),('auto_edit_final',{'plan_id':'missing','approved':True})]:
            code,out=self.api('/api/jobs',{'kind':kind,'payload':payload})
            self.assertEqual(code,400,out)
        self.assertEqual(self.api('/api/renders/subtitles?id=missing&format=srt')[0],404)
        self.assertEqual(self.api('/api/renders/subtitles?id=missing&format=exe')[0],400)
    def test_final_auto_edit_cannot_submit_its_own_approval(self):
        from auto_video import AutoEditPlans
        plan=AutoEditPlans(Path(self.tmp.name)/'test.sqlite').save({'media_id':'approval-fixture','raw_sha':'test',
            'transcript_revision':1,'cuts':[],'options':{},'zooms':[],'preview_id':'preview','source_duration':10})
        code,out=self.api('/api/jobs',{'kind':'auto_edit_final','payload':{'plan_id':plan['id'],'approved':True}})
        self.assertEqual(code,200,out)
        self.assertNotIn('approved',out['payload'])
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.upstream=ThreadingHTTPServer(('127.0.0.1',0),Provider)
        Thread(target=cls.upstream.serve_forever,daemon=True).start()
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        cls.base=f'http://127.0.0.1:{port}'
        env=dict(os.environ,TEHNET_PANEL_PORT=str(port),TEHNET_PANEL_DB=str(Path(cls.tmp.name)/'test.sqlite'))
        for k in ('GOOGLE_AI_API_KEY','GA4_PROPERTY_ID','GA4_ACCESS_TOKEN','GOOGLE_ADS_DEVELOPER_TOKEN','GOOGLE_ADS_CUSTOMER_ID','GOOGLE_ADS_CLIENT_ID','GOOGLE_ADS_CLIENT_SECRET','GOOGLE_ADS_REFRESH_TOKEN'):env.pop(k,None)
        for k in ('ADMIN_USER','ADMIN_PASSWORD','ADMIN_PASSWORD_HASH'):env.pop(k,None)
        code="import sys;sys.path.insert(0,'outputs/panel');import server as s;s.ga4_fetch=lambda:{'views':12};s.ThreadingHTTPServer((\"127.0.0.1\",s.PORT),s.Handler).serve_forever()"
        cls.proc=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:cls.token=cls.api('/api/session')[1]['token'];break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Test server did not start')
    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate();cls.proc.wait(timeout=5)
        cls.upstream.shutdown();cls.upstream.server_close();cls.tmp.cleanup()
    @classmethod
    def api(cls,path,data=None):
        headers={'Content-Type':'application/json','X-Panel-Token':getattr(cls,'token','')}
        req=urllib.request.Request(cls.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    def test_preflight_uses_configured_hook_provider(self):
        self.api('/api/ai/providers/save',{'name':'lmstudio','enabled':False})
        self.api('/api/ai/providers/save',{'name':'ollama','base_url':f'http://127.0.0.1:{self.upstream.server_port}/v1','model':'test-model','tasks':['hooks']})
        code,out=self.api('/api/jobs',{'kind':'generate_hooks','payload':{}})
        self.assertEqual(code,200,out)
        self.assertIn('id',out)
    def test_optional_connection_buttons_do_not_crash_without_keys(self):
        for platform in ('ga4','google_ads','gemini'):
            code,out=self.api('/api/integrations/test',{'platform':platform})
            self.assertEqual(code,200,out)
            self.assertFalse(out['ok'])
            self.assertTrue(out['detail'])
    def test_oauth_start_without_client_is_actionable_not_crash(self):
        code,out=self.api('/api/oauth/start?provider=youtube')
        self.assertEqual(code,400,out)
        self.assertIn('YOUTUBE_CLIENT_ID',out.get('error',''))
    def test_gsc_and_gemini_jobs_reach_dependency_gate(self):
        for path,payload in [('/api/gsc/ingest',{'site':'https://tehnet.ir','start':'2026-10-01','end':'2026-10-12'}),('/api/gemini/generate',{'prompt':'test'})]:
            code,out=self.api(path,payload)
            self.assertEqual(code,200,out)
            self.assertIn('id',out)
    def test_ga4_fetch_records_selected_brand(self):
        code,out=self.api('/api/ga4/fetch',{'brand':'mytel'})
        self.assertEqual(code,200,out)
        rows=self.api('/api/analytics/snapshots?platform=ga4')[1]
        self.assertEqual(rows[0]['brand'],'mytel')
        self.assertEqual(rows[0]['metrics']['views'],12)

class OAuthCallbackTests(unittest.TestCase):
    def test_expired_state_cannot_be_used(self):
        with tempfile.TemporaryDirectory() as td:
            store=OAuthStore(Path(td)/'oauth.sqlite');state=store.new_state('youtube')
            with store.connect() as c:c.execute("UPDATE oauth_states SET created_at='2000-01-01T00:00:00+00:00' WHERE state=?",(state,))
            self.assertIsNone(store.pop_state(state))
    def test_callback_resolves_provider_from_single_use_state(self):
        with tempfile.TemporaryDirectory() as td:
            store=OAuthStore(Path(td)/'oauth.sqlite')
            state=store.new_state('youtube')
            with patch.dict(os.environ,{'YOUTUBE_CLIENT_ID':'fixture-client','YOUTUBE_CLIENT_SECRET':'fixture-secret'}),patch('providers.urllib.request.urlopen',return_value=io.BytesIO(b'{"access_token":"fixture-access","expires_in":3600}')):
                out=oauth_callback(None,store,'fixture-code',state,'http://127.0.0.1:18767')
                self.assertEqual(store.get_token('youtube'),'fixture-access')
                with self.assertRaises(PermissionError):oauth_callback(None,store,'fixture-code',state)

class LinuxStorageTests(unittest.TestCase):
    def test_mounted_media_and_archive_report_real_capacity(self):
        import system
        with tempfile.TemporaryDirectory() as td,patch('system.platform.system',return_value='Linux'),patch('system.ctypes.windll',None,create=True),patch.dict(os.environ,{'TEHNET_STORAGE_PATHS':json.dumps([{'path':td,'label':'My Passport','type':'removable'}])}):
            rows=system.drives()
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['letter'],td)
            self.assertGreater(rows[0]['total'],0)
            self.assertGreaterEqual(rows[0]['free'],0)

class GA4ResponseTests(unittest.TestCase):
    def test_metric_values_array_is_decoded_using_api_header_names(self):
        payload={'metricHeaders':[{'name':'totalUsers'},{'name':'sessions'},{'name':'keyEvents'}],
                 'rows':[{'metricValues':[{'value':'10'},{'value':'12'},{'value':'2'}]}]}
        with patch('integrations.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())):
            result=ga4_fetch('fixture-property','fixture-token')
        self.assertEqual(result['users'],10)
        self.assertEqual(result['sessions'],12)
        self.assertEqual(result['conversions'],2)

class GSCRequestTests(unittest.TestCase):
    def test_real_date_format_and_clicks_are_preserved(self):
        from datetime import date
        from types import SimpleNamespace
        from analytics import AnalyticsStore,gsc_ingest_handler
        with tempfile.TemporaryDirectory() as td:
            store=AnalyticsStore(Path(td)/'gsc.sqlite')
            ctx=SimpleNamespace(payload={'site':'https://tehnet.ir/','brand':'tehran-network'},services={'analytics':store},id='fixture',log=lambda _:None,progress=lambda _:None)
            response={'rows':[{'keys':['query','page'],'clicks':2,'impressions':10}]}
            with patch.dict(os.environ,{'GSC_CREDENTIALS':'fixture-token'}),patch('providers.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as transport:
                gsc_ingest_handler(ctx)
                request=transport.call_args.args[0]
                payload=json.loads(request.data)
                self.assertLess(date.fromisoformat(payload['endDate']),date.today())
                date.fromisoformat(payload['startDate'])
            metrics=store.snapshots('gsc')[0]['metrics']
            self.assertEqual(metrics['clicks'],2)
            self.assertNotIn('views',metrics)

class AuthenticatedReadTests(unittest.TestCase):
    def test_private_reads_require_login_and_cookie_allows_media_requests(self):
        with tempfile.TemporaryDirectory() as td:
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            base=f'http://127.0.0.1:{port}'
            env=dict(os.environ,TEHNET_PANEL_PORT=str(port),TEHNET_PANEL_DB=str(Path(td)/'test.sqlite'),ADMIN_USER='fixture-user',ADMIN_PASSWORD='fixture-password')
            env.pop('ADMIN_PASSWORD_HASH',None)
            proc=subprocess.Popen([sys.executable,str(ROOT/'outputs/panel/server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                for _ in range(80):
                    try:
                        session=json.load(urllib.request.urlopen(base+'/api/session',timeout=1));break
                    except OSError:time.sleep(.1)
                with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(base+'/api/media',timeout=3)
                self.assertEqual(caught.exception.code,401)
                req=urllib.request.Request(base+'/api/auth/login',data=b'{"username":"fixture-user","password":"fixture-password"}',headers={'Content-Type':'application/json','X-Panel-Token':session['token']})
                with urllib.request.urlopen(req,timeout=3) as r:
                    cookie=r.headers.get('Set-Cookie');self.assertTrue(cookie)
                    login_token=json.load(r)['token']
                req=urllib.request.Request(base+'/api/media',headers={'Cookie':cookie.split(';',1)[0]})
                with urllib.request.urlopen(req,timeout=3) as r:self.assertEqual(json.load(r),[])
                req=urllib.request.Request(base+'/api/session',headers={'Cookie':cookie.split(';',1)[0]})
                with urllib.request.urlopen(req,timeout=3) as r:self.assertTrue(json.load(r).get('authenticated',False))
                req=urllib.request.Request(base+'/api/auth/logout',data=b'{}',headers={'Content-Type':'application/json','X-Panel-Token':session['token'],'Cookie':cookie.split(';',1)[0]})
                urllib.request.urlopen(req,timeout=3).close()
                req=urllib.request.Request(base+'/api/media',headers={'X-Panel-Token':login_token})
                with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(req,timeout=3)
                self.assertEqual(caught.exception.code,401)
            finally:
                proc.terminate();proc.wait(timeout=5)

class ArchiveReadinessTests(unittest.TestCase):
    def test_missing_source_is_not_reported_as_successful_archive(self):
        from store import Store
        from media import MediaLibrary
        from ops import ArchiveStore,archive_copy_handler
        from jobs import DependencyMissing
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);db=root/'data.sqlite';store=Store(db);lib=MediaLibrary(db,root/'media');archive=ArchiveStore(db)
            item=store.save({'title':'fixture','brands':['tehran-network'],'body':''})
            stream=io.BytesIO(b'fixture raw media')
            media=lib.ingest(stream.read,'fixture.mp4','screen',item['id'])
            Path(media['path']).unlink()
            dest=root/'archive';dest.mkdir()
            ctx=SimpleNamespace(payload={'content_id':item['id'],'passport_path':str(dest),'approved':True},services={'store':store,'media':lib,'archive':archive},log=lambda _:None,progress=lambda _:None,cancelled=lambda:False)
            with self.assertRaises(DependencyMissing):archive_copy_handler(ctx)

class BenchmarkMediaTests(unittest.TestCase):
    def test_transcription_honors_saved_model_and_explicit_override(self):
        from transcribe import transcribe_audio_handler
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        with tempfile.TemporaryDirectory() as td:
            audio=Path(td)/'voice.mp3';audio.write_bytes(b'fixture')
            lib=Mock();lib.get.return_value={'id':'voice-id','path':str(audio),'orig_name':'voice.mp3'}
            ws=Mock();ws.whisper_model.return_value='medium'
            transcripts=Mock();transcripts.add.return_value={'id':'tx','revision':1}
            result={'text':'fixture','segments':[],'language':'fa','duration':1,'engine':{}}
            ctx=SimpleNamespace(payload={'media_id':'voice-id'},services={'media':lib,'transcripts':transcripts,'whisper_settings':ws},log=lambda _:None,progress=lambda _:None,id='job')
            with patch('transcribe.engine_available',return_value=True),patch('transcribe.run_engine',return_value=result) as run:
                transcribe_audio_handler(ctx)
                self.assertEqual(run.call_args.kwargs['model_size'],'medium')
                ctx.payload['model_size']='small';transcribe_audio_handler(ctx)
                self.assertEqual(run.call_args.kwargs['model_size'],'small')
    def test_benchmark_uses_uploaded_media_instead_of_missing_host_sample(self):
        from whisper_config import benchmark_handler
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        with tempfile.TemporaryDirectory() as td:
            audio=Path(td)/'voice.mp3';audio.write_bytes(b'fixture')
            lib=Mock();lib.get.return_value={'path':str(audio)}
            ws=Mock();ctx=SimpleNamespace(payload={'media_id':'voice-id','models':['small'],'reference_text':'reference'},services={'media':lib,'whisper_settings':ws},log=lambda _:None,progress=lambda _:None)
            measured={'model':'small','device':'cuda','audio_seconds':1,'load_seconds':1,'transcribe_seconds':1,'rough_overlap':100,'sample':'voice.mp3'}
            with patch('whisper_config.run_benchmark',return_value=measured) as run:
                self.assertEqual(benchmark_handler(ctx)['recommended'],'small')
                run.assert_called_once_with(str(audio),'reference','small')

if __name__=='__main__':unittest.main()
