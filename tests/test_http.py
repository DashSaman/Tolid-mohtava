import json,os,socket,subprocess,sys,tempfile,time,unittest,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        cls.base=f'http://127.0.0.1:{port}'
        env=dict(os.environ,TEHNET_PANEL_PORT=str(port),TEHNET_PANEL_DB=str(Path(cls.tmp.name)/'test.sqlite'))
        cls.process=subprocess.Popen([sys.executable,str(ROOT/'outputs/panel/server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                cls.token=json.loads(cls.request('/api/session')[1])['token'];break
            except OSError:time.sleep(.1)
        else:
            cls.process.terminate();cls.process.wait();cls.tmp.cleanup()
            raise RuntimeError('Isolated test server did not start')
    @classmethod
    def tearDownClass(cls):
        cls.process.terminate();cls.process.wait(timeout=5);cls.tmp.cleanup()
    @classmethod
    def request(cls,path,data=None,headers=None):
        req=urllib.request.Request(cls.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers or {})
        try:
            with urllib.request.urlopen(req,timeout=2) as r:return r.status,r.read(),r.headers
        except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
    def test_readonly_surface_and_path_limits(self):
        status,body,headers=self.request('/')
        self.assertEqual(status,200);self.assertIn(b'dir="rtl"',body)
        self.assertIn('frame-ancestors',headers['Content-Security-Policy'])
        self.assertEqual(len(json.loads(self.request('/api/skills')[1])),17)
        for path in ['/data/content.sqlite','/../server.py','/server.py']:self.assertEqual(self.request(path)[0],404)
        self.assertEqual(self.request('/api/items?brand=unknown')[0],400)
        self.assertEqual(self.request('/api/session',headers={'Host':'untrusted.example'})[0],403)
    def test_mutation_gate_and_no_publication(self):
        self.assertEqual(self.request('/api/items',{}, {'Content-Type':'application/json'})[0],403)
        h={'Content-Type':'application/json','X-Panel-Token':self.token}
        self.assertEqual(self.request('/api/items',{},dict(h,Origin='https://untrusted.example'))[0],403)
        self.assertEqual(self.request('/api/publish',{},h)[0],404)
        code,body,_=self.request('/api/items',dict(title='HTTP test',brands=['tehran-network'],body='Test draft'),h)
        self.assertEqual(code,200)
        record=json.loads(body)
        self.assertEqual(json.loads(self.request('/api/items?brand=mytel')[1]),[])
        decision=dict(id=record['id'],revision=1,gate='publish',status='approved')
        self.assertEqual(self.request('/api/decide',decision,h)[0],200)
        decision['revision']=0
        self.assertEqual(self.request('/api/decide',decision,h)[0],400)
    def test_jobs_surface_and_gates(self):
        h={'Content-Type':'application/json','X-Panel-Token':self.token}
        self.assertEqual(json.loads(self.request('/api/jobs')[1]),[])
        code,body,_=self.request('/api/jobs',{'kind':'unknown-kind'},h)
        self.assertEqual(code,400)
        self.assertIn('پشتیبانی',json.loads(body)['error'])
        self.assertEqual(self.request('/api/jobs',{'kind':'x'},{'Content-Type':'application/json'})[0],403)
        self.assertEqual(self.request('/api/job?id=missing')[0],404)
        self.assertEqual(self.request('/api/jobs/decision',{'id':'x','approved':'yes'},h)[0],400)
        self.assertEqual(self.request('/api/jobs/cancel',{'id':'missing'},h)[0],400)

if __name__=='__main__':unittest.main()
