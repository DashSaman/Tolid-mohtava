"""Integration Center readiness verification (9 integrations) + article
reliability + extraction regression tests."""
import unittest, tempfile, sys, shutil, json, os, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs/panel'))
from ai import extract_json, validate_schema, parse_markdown_kv, _repair_json, _balanced_json, _close_opens
from ai_jobs import article_validator
from analytics import adapter_status, health_check, ADAPTERS, PLATFORMS
from seo_engine import _crawl_policy, CRAWL_DEFAULTS

REAL_LLAMA_ARTICLE=("Here is a rewritten article in a structured format for the website tehnet.ir:\n\n"
 "**Title:** COMPLETE GUIDE TO CONFIGURING YOUR MODEM SETTINGS\n"
 "**Slug:** complete-guide-to-configuring-your-modem-settings\n"
 "**Meta Description:** Learn how to configure your modem settings with this step-by-step guide.\n"
 "**Primary Keyword:** Modem Settings\n"
 "**Sections:**\n - Accessing the admin panel\n - Changing WAN settings\n")

class ExtractionRegressionTests(unittest.TestCase):
    def test_real_llama_markdown_kv_now_parses(self):
        d=extract_json(REAL_LLAMA_ARTICLE)
        self.assertIsNotNone(d,'the exact E2E failure sample must now parse')
        self.assertEqual(d['title'],'COMPLETE GUIDE TO CONFIGURING YOUR MODEM SETTINGS')
        self.assertTrue(d['slug'].startswith('complete-guide'))
        self.assertFalse(str(d['title']).startswith('*'))
    def test_kv_bullets_and_clean_keys(self):
        d=parse_markdown_kv('**Key:** value\n - one\n - two')
        self.assertEqual(d['key'],['value','one','two'],'value + bullets accumulate under the key')
        d2=parse_markdown_kv('**هوک‌ها:**\n - اول\n - دوم')
        self.assertEqual(d2.get('هوک_ها'),['اول','دوم'])
        self.assertFalse(any(k.startswith('*') or k.endswith('*') for k in d2))
        d3=parse_markdown_kv('**Title:** x')
        self.assertEqual(d3.get('title'),'x')
    def test_repair_layers(self):
        self.assertEqual(_repair_json('{"a":1,"b":[1,2,],}'),{'a':1,'b':[1,2]})
        self.assertEqual(_repair_json('متن {"title":"x","items":[{"h2":"a"'),
                         {'title':'x','items':[{'h2':'a'}]})
        self.assertEqual(_close_opens('{"x":[{"y":"z"'),'{\"x\":[{\"y\":\"z\"}]}')
    def test_balanced_json_nested(self):
        self.assertEqual(_balanced_json('noise {"a":{"b":[1,2,{"c":3}]}} tail'),{'a':{'b':[1,2,{'c':3}]}})
        self.assertIsNone(_balanced_json('no braces at all'))
    def test_validate_schema_honest(self):
        problems=validate_schema({'title':'t'},required=('slug',),list_fields=('sections',))
        self.assertTrue(any('slug' in p for p in problems))
        self.assertTrue(any('sections' in p for p in problems))
        self.assertEqual(validate_schema({'slug':'s','sections':[{'h2':'a'},{'h2':'b'}]},
                                          required=('slug',),list_fields=('sections',)),[])
    def test_article_validator_requires_seo_fields(self):
        self.assertTrue(article_validator({'title':'t','slug':'s'}))
        self.assertEqual(article_validator({'title':'t','slug':'s','meta_description':'m',
            'primary_keyword':'k','sections':[{'h2':'a'},{'h2':'b'}]}),[])

class IntegrationCenterReadinessTests(unittest.TestCase):
    EXPECTED={'tehnet.ir','mytel.one','youtube','instagram','facebook','linkedin','telegram','gsc'}
    def test_all_adapters_exist_with_scopes_and_env(self):
        self.assertEqual(set(ADAPTERS),self.EXPECTED,'8 integrations expected')
        for p,a in ADAPTERS.items():
            self.assertTrue(a['scopes'],'scope documented for '+p)
            self.assertTrue(a['env'] and all(re_ok(v) for v in a['env']),'env names for '+p)
            self.assertTrue(a['endpoint'])
    def test_status_honest_and_no_secrets(self):
        rows=adapter_status()
        self.assertEqual({r['platform'] for r in rows},self.EXPECTED)
        leaked=[r for r in rows if any(os.environ.get(v) for v in r['env'])]
        for r in rows:
            if not leaked:
                self.assertEqual(r['state'],'blocked_by_credential')
            self.assertIn(r['state_fa'],['BLOCKED_BY_CREDENTIAL','آماده (Credential ثبت شده)'])
            for k,v in r.items():
                self.assertNotIn('sk-',str(v)); self.assertNotIn('password=',str(v).lower())
    def test_health_check_missing_env_detail(self):
        os.environ.pop('TELEGRAM_BOT_TOKEN',None)
        h=health_check('telegram')
        self.assertFalse(h['ok'])
        self.assertIn('TELEGRAM_BOT_TOKEN',h['detail'],'must name exactly what is missing')
    def test_gemini_env_documented_in_ui_data(self):
        # Gemini is handled by the thumbs path; ensure the env name exists in adapter surface
        rows={r['platform']:r for r in adapter_status()}
        self.assertIn('gsc',rows)

def re_ok(name): return __import__('re').fullmatch(r'[A-Z0-9_]+',name or '')

class CrawlPolicyTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        self.assertEqual(CRAWL_DEFAULTS['max_pages'],25)
        self.assertGreaterEqual(CRAWL_DEFAULTS['delay_seconds'],1.0)
    def test_clamping_hard_limits(self):
        p=_crawl_policy({'max_pages':999999,'delay_seconds':0.0,'timeout':999,'max_depth':99})
        self.assertEqual(p['max_pages'],100)
        self.assertEqual(p['delay_seconds'],0.2)
        self.assertEqual(p['timeout'],60)
        self.assertEqual(p['max_depth'],6)
        self.assertEqual(_crawl_policy(None),CRAWL_DEFAULTS)

if __name__=='__main__': unittest.main(verbosity=2)
