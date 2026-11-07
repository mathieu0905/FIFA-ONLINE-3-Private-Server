"""Export maintained FO3 code for public review, never runtime assets or saves.

Run against a local installation with --server, --workspace and --output.
The output must be a new directory outside the server and client. No service is
started and no source file is modified. The export intentionally does not turn
local installation receipts into portable installation certificates.
"""
import argparse
import ast
from collections import Counter
import hashlib
import gzip
import json
import os
from pathlib import Path
import re
import sys

SOURCE = {'.py', '.ps1', '.bat', '.cs', '.js', '.cjs', '.mjs', '.css', '.html'}
SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'github-public',
        'certs', 'captures', 'raw', 'decompiled', 'analysis_deps', 'analysis-deps',
        'deps', 'private-servers', 'upstream-review', 'upstream-integration',
        'candidates', 'bulk-sources', 'client-code', 'transaction-tests',
        'research', 'outputs', 'artifacts', 'mpl-cache', 'tmp', 'temp', 'cache',
        'server', 'client', '32795', 'native', 'ea-sources', 'before',
        'rendered', 'assets', 'gamedata'}
SKIP_PARTS = ('backup', 'snapshot', 'sandbox', 'fixture', 'install-test',
              'release-test', 'runtime-test', 'test-runtime', 'checks-runtime',
              'site-packages')
PRIVATE_CONFIG = {'shop.json', 'state.json', 'player-import-validation.json',
                  'fa_prices.json', 'fa_faces.json', 'formations.json', 'stadiums.json'}
SECRET_KEY = re.compile(r'^(?:token_key|secret|secret_key|api_key|apikey|password|passwd|access_token|refresh_token|authorization|cookie|private_key|ssh_key)$', re.I)
TOKEN = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{20,})\b')
PEM = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
PLACEHOLDER = '__GENERATE_LOCALLY__'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def walk_sources(root):
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d.lower() not in SKIP
                         and not d.startswith('.') and not d.startswith('public-source-export-')
                         and not any(k in d.lower() for k in SKIP_PARTS))
        for name in sorted(files):
            p = Path(current) / name
            # Downloaded web pages and site JavaScript are source evidence, not
            # authored application code. Retain our UI and browser-test scripts.
            fetched = p.suffix.lower() == '.html' and name != 'index.html'
            fetched = fetched or name in ('datacenter.js', 'site-public.js', '10163705-inline.js', '47163705-inline.js')
            if p.suffix.lower() in SOURCE and not fetched and '.before' not in name and name != 'prepare_public_fork.py':
                yield p


def secret_values(value, found):
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.fullmatch(key) and isinstance(child, str) and len(child) >= 16:
                found.add(child)
            secret_values(child, found)
    elif isinstance(value, list):
        for child in value:
            secret_values(child, found)


def sanitize_config(value):
    if isinstance(value, dict):
        result = {k: PLACEHOLDER if SECRET_KEY.fullmatch(k) else sanitize_config(v)
                  for k, v in value.items()}
        # These are distribution templates, not old installation receipts. Only
        # canonical content hashes in edited configurations are recalculated.
        if 'hash' in result and result != value:
            result['hash'] = sha(canonical({k: v for k, v in result.items() if k != 'hash'}))
        return result
    if isinstance(value, list):
        return [sanitize_config(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    server, workspace, output = args.server.resolve(), args.workspace.resolve(), args.output.resolve()
    client = server.parent / '32795'
    if output.exists() or output.is_relative_to(server) or output.is_relative_to(client):
        parser.error('Output must be a new directory outside the live server/client')
    candidates = {}
    configurations = {}

    for p in sorted(server.iterdir()):
        if p.is_file() and p.suffix.lower() in SOURCE:
            candidates['server/' + p.name] = (p, 'runtime')
    for name in ('admin', 'analysis', 'launcher', 'player_editor', 'tools', 'patches'):
        for p in sorted((server / name).rglob('*')):
            if p.is_file() and p.suffix.lower() in SOURCE and not any(x in p.parts for x in ('__pycache__', 'node_modules')):
                candidates['server/' + p.relative_to(server).as_posix()] = (p, 'runtime' if name != 'patches' else 'installation-source')
    for p in sorted((server / 'hot_updates/revisions').glob('*/business.py')):
        candidates['server/' + p.relative_to(server).as_posix()] = (p, 'business')
    for p in sorted((server / 'docs').iterdir()):
        if p.is_file() and p.suffix in ('.md', '.txt'):
            candidates['server/' + p.relative_to(server).as_posix()] = (p, 'documentation')
    for name in ('draw_first_rules.json', 'server_display_zh.json', 'tools/player_import/rig-map.json'):
        p = server / name
        if p.exists():
            configurations['server/' + name] = p
    provenance = server / 'docs/wonderkid-portrait-sources.json'
    if provenance.exists():
        configurations['server/docs/wonderkid-portrait-sources.json'] = provenance
    for p in sorted((server / 'gamedata').glob('*.json')):
        if p.name not in PRIVATE_CONFIG and '.before' not in p.name:
            configurations['config-templates/' + p.name] = p
    compressed_inputs = {}
    for p in sorted((server / 'gamedata').glob('*.json.gz')):
        if p.name != 'fair-value-v13-utility-evidence.json.gz':
            compressed_inputs['config-templates/' + p.name] = p
    model_path = server / 'tools/value_v11/selected-model.json.gz'
    if model_path.exists():
        compressed_inputs['server/tools/value_v11/selected-model.json.gz'] = model_path
    for p in walk_sources(workspace):
        relative = p.relative_to(workspace).as_posix()
        candidates['development/' + relative] = (p, 'development-history')
    # Trained value models are software inputs; raw training tables/databases,
    # scraped pages and player images are deliberately not exported.
    for p in sorted((workspace / 'npc-peer-market').glob('*model*.json')):
        if p.is_file() and not any(x in p.parts for x in ('analysis-deps', 'deps')):
            configurations['development/' + p.relative_to(workspace).as_posix()] = p

    buffers, configs, secrets = {}, {}, set()
    for relative, (p, category) in candidates.items():
        data = p.read_bytes()
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = data.decode('gb18030')
        buffers[relative] = (p, category, data, text)
        if p.suffix == '.py':
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Dict):
                    for key, val in zip(node.keys, node.values):
                        if isinstance(key, ast.Constant) and isinstance(key.value, str) and SECRET_KEY.fullmatch(key.value) and isinstance(val, ast.Constant) and isinstance(val.value, str) and len(val.value) >= 16:
                            secrets.add(val.value)
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and len(node.value.value) >= 16:
                    if any(isinstance(t, ast.Name) and SECRET_KEY.fullmatch(t.id) for t in node.targets):
                        secrets.add(node.value.value)
    for relative, p in configurations.items():
        data = p.read_bytes()
        value = json.loads(data.decode('utf-8-sig'))
        secret_values(value, secrets)
        configs[relative] = (p, data, value)
    shop_path = server / 'gamedata/shop.json'
    if shop_path.exists():
        data = shop_path.read_bytes()
        shop = json.loads(data.decode('utf-8-sig'))
        allowed = {'hidden', 'packs', 'items', 'packages', 'lists', 'prices',
                   'free', 'currency', 'chain_names'}
        if set(shop) - allowed:
            raise RuntimeError('Shop catalogue has unreviewed fields; review before export')
        secret_values(shop, secrets)
        configs['config-templates/shop.catalogue.json'] = (shop_path, data, shop)
    # Include the upstream response schema files only after sanitizing any
    # locally edited account/roster payloads; no captured account response is
    # copied from the live install here.
    upstream = Path(__file__).resolve().parents[1]
    for p in (upstream / 'responses').glob('*.json'):
        rel = 'server/responses/' + p.name
        # Reviewed local edits are static season/ranking definitions, not an
        # account response captured from a running manager session.
        if p.name in ('static_roster.json', 'ladder_division_info.json'):
            p = server / 'responses' / p.name
        data = p.read_bytes()
        configs[rel] = (p, data, json.loads(data.decode('utf-8-sig')))

    # Exclude no source based on a content match: redact credentials and report
    # exactly which files changed, without recording any private value.
    entries, errors, fragments = [], [], []
    output.mkdir(parents=True)
    for relative, (p, category, original, text) in buffers.items():
        cleaned = text.replace('\r\n', '\n')
        for secret in sorted(secrets, key=len, reverse=True):
            cleaned = cleaned.replace(secret, PLACEHOLDER)
        cleaned = TOKEN.sub(PLACEHOLDER, cleaned)
        cleaned = PEM.sub(PLACEHOLDER, cleaned)
        if p.suffix == '.py':
            try:
                ast.parse(cleaned, filename=relative)
            except SyntaxError as exc:
                if relative == 'development/chain-volume/single_suffix.py':
                    relative += '.fragment'
                    category = 'source-fragment'
                    fragments.append(relative)
                else:
                    errors.append(dict(path=relative, line=exc.lineno, reason=exc.msg))
        data = cleaned.encode('utf8')
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        entries.append(dict(path=relative, category=category, source_sha256=sha(original),
                            sha256=sha(data), size=len(data),
                            credentials_redacted=cleaned != text.replace('\r\n', '\n')))
    for relative, (p, original, value) in configs.items():
        cleaned = sanitize_config(value)
        text = json.dumps(cleaned, ensure_ascii=False, indent=2) + '\n'
        for secret in sorted(secrets, key=len, reverse=True):
            text = text.replace(secret, PLACEHOLDER)
        text = TOKEN.sub(PLACEHOLDER, text)
        data = text.encode('utf8')
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        entries.append(dict(path=relative, category='configuration-template',
                            source_sha256=sha(original), sha256=sha(data), size=len(data),
                            credentials_redacted=PLACEHOLDER in text))
    for relative, p in compressed_inputs.items():
        data = p.read_bytes()
        value = json.loads(gzip.decompress(data))
        if sanitize_config(value) != value:
            raise RuntimeError('Compressed runtime data contains a credential; review required')
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        entries.append(dict(path=relative, category='runtime-data-template',
                            source_sha256=sha(data), sha256=sha(data), size=len(data),
                            credentials_redacted=False))
    changed = []
    for relative, (p, _, original, _) in buffers.items():
        if sha(p.read_bytes()) != sha(original):
            changed.append(relative)
    for relative, (p, original, _) in configs.items():
        if sha(p.read_bytes()) != sha(original):
            changed.append(relative)
    active = json.loads((server / 'hot_updates/active.json').read_text('utf8'))
    public_active = {k: active[k] for k in ('schema', 'abi', 'revision', 'code', 'routes')}
    public_active['scope'] = 'Source routing reference only; not a runtime descriptor or installation certificate.'
    active_data = buffers['server/' + active['code']][2]
    if sha(active_data) != active['sha256']:
        raise RuntimeError('Active source changed while exporting')
    (output / 'active-business-source.json').write_bytes(canonical(public_active) + b'\n')
    history = []
    for p in sorted((server / 'hot_updates/history').glob('*.json')):
        descriptor = json.loads(p.read_text('utf8'))
        history.append({k: descriptor[k] for k in ('schema', 'abi', 'revision', 'code', 'routes')})
    (output / 'business-source-history.json').write_bytes(
        json.dumps(dict(scope='Source routing references only; not runtime installation certificates',
                        revisions=history), ensure_ascii=False, indent=2).encode('utf8') + b'\n')
    report = dict(schema=1, status='PASS' if not changed and not errors else 'REVIEW_REQUIRED',
                  scope='Complete maintained server source plus authored development tools; no game installation or saves',
                  active_business_revision=active['revision'], entries=entries,
                  counts=dict(Counter(e['category'] for e in entries)),
                  syntax_errors=errors, concurrently_changed_files=changed,
                  source_fragments=fragments,
                  excluded=['player saves; shop export contains catalog definitions only', 'credentials and TLS keys',
                            'game binaries, databases, archives, models, textures and music',
                            'raw captures, dumps, scraped pages, training tables and images',
                            'third-party dependencies, generated test installs, backups',
                            'machine-specific installation manifests, receipts and certificates'])
    (output / 'source-inventory.json').write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode('utf8') + b'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'entries'}, ensure_ascii=True))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
