import unittest,tempfile,sys,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from install_skills import install

class InstallTests(unittest.TestCase):
    def test_pinned_files_and_existing_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(len(install(d)),17)
            path=Path(d)/'post-writer/SKILL.md'
            path.write_text('custom user skill',encoding='utf-8')
            again=install(d)
            self.assertTrue(all(status=='preserved' for _,status in again))
            self.assertEqual(path.read_text(encoding='utf-8'),'custom user skill')
    def test_all_vendor_files_match_manifest(self):
        m=json.loads((ROOT/'outputs/installation-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(m['skills'],17)
        for e in m['files']:
            self.assertEqual(hashlib.sha256((ROOT/e['path']).read_bytes()).hexdigest(),e['sha256'])

if __name__=='__main__':unittest.main()
