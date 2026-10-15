import importlib.util,sqlite3,tempfile,unittest
from contextlib import closing
from pathlib import Path
spec=importlib.util.spec_from_file_location('restore_database',Path(__file__).resolve().parents[1]/'setup/restore_database.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class OfflineRestoreTests(unittest.TestCase):
    def test_verified_snapshot_replaces_stopped_database(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'backup.sqlite';target=Path(td)/'target.sqlite'
            with closing(sqlite3.connect(source)) as db:
                db.execute('CREATE TABLE content(id TEXT)');db.execute("INSERT INTO content VALUES('restored')");db.commit()
            with closing(sqlite3.connect(target)) as db:
                db.execute('CREATE TABLE content(id TEXT)');db.execute("INSERT INTO content VALUES('before')");db.commit()
            module.restore(source,target)
            with closing(sqlite3.connect(target)) as db:self.assertEqual(db.execute('SELECT id FROM content').fetchone()[0],'restored')
    def test_invalid_backup_leaves_existing_database_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'invalid.sqlite';target=Path(td)/'target.sqlite'
            source.write_bytes(b'not sqlite');target.write_bytes(b'unchanged')
            with self.assertRaises(sqlite3.DatabaseError):module.restore(source,target)
            self.assertEqual(target.read_bytes(),b'unchanged')
