"""Audit an exported source tree without importing or starting the game server."""
import argparse
import ast
import base64
from collections import Counter
import hashlib
import gzip
import importlib.util
import json
from pathlib import Path
import re
import sys
import zlib


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf8')


def sensitive(value, path, failures):
    keys = re.compile(r'^(token_key|secret|secret_key|api_key|apikey|password|passwd|access_token|refresh_token|authorization|cookie|private_key|ssh_key)$', re.I)
    if isinstance(value, dict):
        for key, item in value.items():
            if keys.fullmatch(key) and isinstance(item, str) and item and item != '__GENERATE_LOCALLY__':
                failures.append(f'{path}: unredacted credential field {key}')
            sensitive(item, path, failures)
    elif isinstance(value, list):
        for item in value:
            sensitive(item, path, failures)


def audit(root):
    inventory = json.loads((root / 'source-inventory.json').read_text('utf8'))
    failures, modules, trees = [], set(), {}
    for p in (root / 'server').glob('*.py'):
        modules.add(p.stem)
    for p in (root / 'server/tools/re').glob('*.py'):
        modules.add(p.stem)
    for p in (root / 'server').iterdir():
        if p.is_dir() and (p / '__init__.py').exists():
            modules.add(p.name)
    counts = Counter()
    for entry in inventory['entries']:
        rel = entry['path']
        p = root / rel
        data = p.read_bytes()
        if sha(data) != entry['sha256']:
            failures.append(rel + ': export hash mismatch')
        counts[entry['category']] += 1
        if p.suffix == '.py':
            trees[rel] = ast.parse(data, filename=rel)
        payload = gzip.decompress(data) if p.name.endswith('.json.gz') else data
        if p.suffix == '.json' or p.name.endswith('.json.gz'):
            value = json.loads(payload)
            sensitive(value, rel, failures)
            if rel.startswith('config-templates/') and isinstance(value, dict) and isinstance(value.get('hash'), str):
                if sha(canonical({k: v for k, v in value.items() if k != 'hash'})) != value['hash']:
                    failures.append(rel + ': configuration content hash mismatch')
        text = payload.decode('utf8')
        if re.search(r'\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{20,})\b', text):
            failures.append(rel + ': credential token pattern')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            failures.append(rel + ': private key')
        if p.suffix.lower() not in {'.py', '.ps1', '.bat', '.cs', '.js', '.cjs', '.mjs', '.css', '.html', '.md', '.txt', '.json', '.fragment'} and not (p.name.endswith('.json.gz') and entry['category'] == 'runtime-data-template'):
            failures.append(rel + ': unreviewed file type')
        if p.name in {'state.json', 'shop.json', 'player-import-validation.json'}:
            failures.append(rel + ': live state or installation certificate')
        if len(data) >= 100 * 1024 * 1024:
            failures.append(rel + ': exceeds GitHub file-size limit')
    external = set()
    for rel, tree in trees.items():
        if not rel.startswith('server/') or '/' in rel[len('server/'):]:
            continue
        for node in ast.walk(tree):
            names = [x.name.split('.')[0] for x in node.names] if isinstance(node, ast.Import) else [node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module and not node.level else []
            for name in names:
                if name not in sys.stdlib_module_names and name not in modules:
                    external.add(name)
    active = json.loads((root / 'active-business-source.json').read_text('utf8'))
    runtime_path = root / 'server/hot_update_runtime.py'
    spec = importlib.util.spec_from_file_location('export_audit_runtime', runtime_path)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)  # definitions only; install() is not invoked
    handlers = runtime.compile_handlers((root / 'server' / active['code']).read_bytes(),
                                        active['code'], active['routes'], allow_templates=True)
    compiled_history = []
    history = json.loads((root / 'business-source-history.json').read_text('utf8'))
    for descriptor in history['revisions']:
        runtime.compile_handlers((root / 'server' / descriptor['code']).read_bytes(),
                                 descriptor['code'], descriptor['routes'],
                                 allow_templates=descriptor['abi'] == 2)
        compiled_history.append(descriptor['revision'])
    compressed = 0
    for rel, tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or len(node.value) < 64 or not node.value.startswith(('eJ', 'eN')):
                continue
            try:
                inflater = zlib.decompressobj()
                decoded = inflater.decompress(base64.b64decode(node.value, validate=True), 32 * 1024 * 1024)
                if not inflater.eof:
                    continue
                value = json.loads(decoded)
            except (ValueError, zlib.error, UnicodeDecodeError):
                continue
            compressed += 1
            sensitive(value, rel + ' (compressed JSON)', failures)
    result = dict(status='PASS' if not failures else 'FAIL',
                  inventory_files=len(inventory['entries']), python_files_parsed=len(trees),
                  category_counts=dict(counts), active_business_revision=active['revision'],
                  compiled_active_routes=sorted(handlers),
                  compiled_history_revisions=compiled_history,
                  compressed_json_payloads_checked=compressed,
                  root_external_imports=sorted(external), failures=failures,
                  live_services_started=False, live_assets_written=False,
                  upstream_launch_integration_verified=False, native_game_verified=False)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1] / 'enhanced')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = audit(args.root.resolve())
    data = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.write_text(data, encoding='utf8', newline='\n')
    print(data)
    sys.exit(0 if result['status'] == 'PASS' else 1)
