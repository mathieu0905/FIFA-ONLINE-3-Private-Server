import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installation_audit', ROOT / 'tools/check_enhanced_install.py')
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class ReadinessTests(unittest.TestCase):
    def test_empty_download_never_reports_ready_or_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            server, client, templates = (root / n for n in ('server', 'client', 'templates'))
            for p in (server, client, templates):
                p.mkdir()
            (templates / 'product_packs.json').write_text('{}')
            before = sorted(str(p.relative_to(root)) for p in root.rglob('*'))
            result = audit_module.audit(server, client, templates)
            self.assertEqual(result['status'], 'NEEDS_PREPARATION')
            self.assertIn('configs-and-keys', result['blocked'])
            self.assertIn('active-business-proof', result['blocked'])
            self.assertEqual(before, sorted(str(p.relative_to(root)) for p in root.rglob('*')))

    def test_missing_sqlite_is_never_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'missing.sqlite'
            with self.assertRaises(ValueError):
                audit_module.database_status(path, ['players'])
            self.assertFalse(path.exists())

    def test_existing_sqlite_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'players.sqlite'
            with closing(sqlite3.connect(path)) as con:
                con.execute('CREATE TABLE players(spid INTEGER)')
                con.commit()
            before = path.read_bytes()
            con = audit_module.database_status(path, ['players'])
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    con.execute('INSERT INTO players VALUES(1)')
            finally:
                con.close()
            self.assertEqual(before, path.read_bytes())

    def test_unmaterialized_keys_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            server, client, templates = (root / n for n in ('server', 'client', 'templates'))
            (server / 'gamedata').mkdir(parents=True)
            client.mkdir()
            templates.mkdir()
            value = {'token_key': '__GENERATE_LOCALLY__'}
            (templates / 'product_packs.json').write_text('{}')
            (server / 'gamedata/product_packs.json').write_text(json.dumps(value))
            result = audit_module.audit(server, client, templates)
            check = next(c for c in result['checks'] if c['code'] == 'configs-and-keys')
            self.assertFalse(check['passed'])
            self.assertIn('uninitialized', check['detail'])


if __name__ == '__main__':
    unittest.main()
