"""Temporary-data checks for public config preparation and credential removal."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class DistributionTests(unittest.TestCase):
    def test_export_removes_secret_and_updates_only_config_hash(self):
        exporter = module('export_local_sources')
        original = {'schema': 1, 'token_key': '1' * 64, 'limits': {'day': 10}}
        original['hash'] = exporter.sha(exporter.canonical(original))
        exported = exporter.sanitize_config(original)
        self.assertEqual(exported['token_key'], '__GENERATE_LOCALLY__')
        self.assertEqual(original['token_key'], '1' * 64)
        self.assertEqual(exported['limits'], original['limits'])
        self.assertEqual(exported['hash'], exporter.sha(exporter.canonical({k: v for k, v in exported.items() if k != 'hash'})))

    def test_each_install_gets_a_fresh_key_without_changing_products(self):
        helper = module('materialize_config_templates')
        template = {'token_key': '__GENERATE_LOCALLY__', 'products': {'1': {'price': 9901}}, 'hash': 'old'}
        first, second = helper.materialize(template), helper.materialize(template)
        self.assertEqual(len(bytes.fromhex(first['token_key'])), 32)
        self.assertNotEqual(first['token_key'], second['token_key'])
        self.assertEqual(first['products'], template['products'])
        self.assertEqual(first['hash'], helper.digest({k: v for k, v in first.items() if k != 'hash'}))

    def test_cli_rejects_existing_destination_without_touching_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            templates = root / 'templates'
            templates.mkdir()
            output = root / 'existing'
            output.mkdir()
            saved = output / 'state.json'
            saved.write_bytes(b'original player progress')
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/materialize_config_templates.py'), '--templates', str(templates), '--output', str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(saved.read_bytes(), b'original player progress')

    def test_cli_refuses_state_in_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            templates = root / 'templates'
            templates.mkdir()
            (templates / 'state.json').write_text('{}')
            output = root / 'prepared'
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/materialize_config_templates.py'), '--templates', str(templates), '--output', str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_cli_materializes_catalogue_without_generating_player_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            templates = root / 'templates'
            templates.mkdir()
            (templates / 'shop.catalogue.json').write_text('{"prices":{"1":9901}}')
            (templates / 'product_packs.json').write_text('{"token_key":"__GENERATE_LOCALLY__","hash":"old"}')
            output = root / 'prepared'
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/materialize_config_templates.py'), '--templates', str(templates), '--output', str(output)], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((output / 'shop.json').read_text())['prices']['1'], 9901)
            self.assertFalse((output / 'state.json').exists())
            self.assertEqual(len(bytes.fromhex(json.loads((output / 'product_packs.json').read_text())['token_key'])), 32)


if __name__ == '__main__':
    unittest.main()
