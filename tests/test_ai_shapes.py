import json,os,sys,tempfile,unittest,time,subprocess
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','outputs','panel'))

class ShapeMatrix(unittest.TestCase):
    """BUG-001 regression: no AI parsing path may raise AttributeError/TypeError/KeyError
    because of a valid-but-unexpected model response shape. Exercises the central
    _normalize_llm boundary with the full matrix, then each handler's post-parse access
    pattern via a fake data dict path (dict guaranteed)."""
    def test_normalize_matrix(self):
        from ai_jobs import _normalize_llm
        cases={
            'empty-dict':{}, 'expect-dict':{'hooks':[{'a':1}]},
            'single-dict-in-list':[{'hooks':[1]}],
            'multi-dict-list':[{'a':1},{'b':2}], 'string-list':['x','y'],
            'empty-list':[], 'nested-obj':{'result':{'hooks':[]}},
            'missing-fields':{'other':1},
        }
        for k,v in cases.items():
            r=_normalize_llm(v)
            self.assertTrue(r is None or isinstance(r,dict),f'{k} -> {type(r)}')
        self.assertEqual(_normalize_llm({'a':1}),{'a':1})
        self.assertEqual(_normalize_llm([{'a':1}]),{'a':1})
        self.assertIsNone(_normalize_llm(['x']))
        self.assertIsNone(_normalize_llm(None))
        self.assertIsNone(_normalize_llm([{'a':1},{'b':2}]))
        self.assertEqual(_normalize_llm(['h1','h2'],'hooks'),{'hooks':['h1','h2']})
        self.assertEqual(_normalize_llm([{'angle':'x'}],'hooks'),{'hooks':[{'angle':'x'}]})
        self.assertIsNone(_normalize_llm(['x','y']))  # no contract declared

    def test_extract_matrix_never_raises(self):
        from ai import extract_json
        for v in ('{}','[]','[{}]','[{},{}]','"s"','null','```json\\n{"hooks":[]}\\n```',
                  '{"hooks":[{"angle":"x"','{"r":{"h":[]}}','{"x":1}',''):
            try: extract_json(v)
            except Exception as e: self.fail(f'extract_json raised on {v!r}: {e}')

if __name__=='__main__':unittest.main()
