import json,urllib.request,urllib.error,unittest,os,subprocess,sys,time,tempfile
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','outputs','panel'))
class StaleCsrfLoginTests(unittest.TestCase):
    """UI login must send the page CSRF token; a stale/missing one gets gate-403,
    and recovery = fetch a fresh /api/session token then login succeeds."""
    @classmethod
    def setUpClass(cls):
        cls.env=dict(os.environ,TEHNET_PANEL_PORT='8786',TEHNET_PANEL_DB=os.path.join(tempfile.gettempdir(),'stalecsrf.sqlite'))
        cls.env.pop('ADMIN_USER',None);cls.env.pop('ADMIN_PASSWORD_HASH',None)
        cls.p=subprocess.Popen([sys.executable,os.path.join(os.path.dirname(__file__),'..','outputs','panel','server.py')],
                               env=cls.env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        time.sleep(3);cls.B='http://127.0.0.1:8786'
    @classmethod
    def tearDownClass(cls):cls.p.kill()
    def call(self,path,data=None,tokn=None):
        h={'Content-Type':'application/json'}
        if tokn is not None:h['X-Panel-Token']=tokn
        b=json.dumps(data).encode() if data is not None else None
        r=urllib.request.Request(self.B+path,b,h)
        try:
            x=urllib.request.urlopen(r,timeout=8);return x.status,json.loads(x.read() or b'{}')
        except urllib.error.HTTPError as e:
            try:return e.code,json.loads(e.read() or b'{}')
            except:return e.code,{}
    def test_login_without_page_token_is_gate_rejected(self):
        s,_=self.call('/api/auth/login',{'username':'x','password':'y'})
        self.assertEqual(s,403)  # the real-browser incident: UI fetch without X-Panel-Token
    def test_recovery_contract_fresh_token_then_login(self):
        _,sess=self.call('/api/session')
        s,b=self.call('/api/auth/login',{'username':'a','password':'b'},tokn=sess['token'])
        # auth disabled in this fixture -> login succeeds at the route with a valid page token
        self.assertEqual(s,200)
if __name__=='__main__':unittest.main()
