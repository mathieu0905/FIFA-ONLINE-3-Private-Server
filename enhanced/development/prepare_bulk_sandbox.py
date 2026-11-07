"""Copy the current backend and inject bulk data only into a new private sandbox."""
from pathlib import Path
import argparse, hashlib, json, shutil, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
FORMAL = Path('D:/FO3ID/server')


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    candidate, out = args.candidate.resolve(), args.out.resolve()
    assert candidate.is_relative_to(ROOT / 'candidates') and out.is_relative_to(ROOT / 'private-servers') and not out.exists()
    manifest = json.loads((candidate / 'manifest.json').read_text('utf-8'))
    assert manifest['status'] == 'BULK_PRIVATE_DB_BUILT_NATIVE_PENDING'
    for rel, digest in manifest['files'].items():
        assert sha(candidate / rel) == digest, rel
    paths = [p for p in FORMAL.iterdir() if p.is_file() and p.suffix in ('.py', '.pem', '.cfg', '.ini', '.json')]
    for directory in ('gamedata', 'responses', 'certs', 'admin', 'patches'):
        paths.extend(p for p in (FORMAL / directory).rglob('*') if p.is_file() and p.suffix in ('.json', '.py', '.pem', '.html', '.htm', '.css', '.js', '.png', '.big', '.txt') and '__pycache__' not in p.parts and '.before' not in p.name)
    before = {str(p.relative_to(FORMAL)): sha(p) for p in paths}
    before['gamedata/fifadb.sqlite'] = sha(FORMAL / 'gamedata/fifadb.sqlite')
    out.mkdir(parents=True)
    for p in paths:
        target = out / p.relative_to(FORMAL)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        assert sha(target) == before[str(p.relative_to(FORMAL))]
    for name in ('fifadb.sqlite', 'custom_rosters.json'):
        shutil.copyfile(candidate / name, out / 'gamedata' / name)
    shutil.copyfile(candidate / 'static_roster.json', out / 'responses/static_roster.json')
    shutil.copyfile(candidate / 'legend_moments_bulk_npc.py', out / 'legend_moments_bulk_npc.py')
    sidecar = Path('D:/FO3QA/modern_player_integration_v2/search-sidecar-v1/modern_registry_search.py')
    assert sha(sidecar) == '02183980f2209cc1b248b41447ea88f52028cf16e777b4b795e53e0a539d6a9c'
    shutil.copyfile(sidecar, out / sidecar.name)
    http = out / 'http_config.py'
    text = http.read_text('utf-8')
    marker = 'if __name__ == "__main__":'
    assert text.count(marker) == 1
    text = text.replace(marker, 'import modern_registry_search\nmodern_registry_search.install(sys.modules[__name__])\nimport legend_moments_bulk_npc\nlegend_moments_bulk_npc.install(sys.modules[__name__])\n\n' + marker)
    http.write_text(text, 'utf-8')
    stable_keys = [k for k in before if k != 'gamedata/state.json']
    for relative in stable_keys:
        assert sha(FORMAL / relative) == before[relative], 'Formal source changed during clone; rebuild: ' + relative
    report = dict(status='PRIVATE_BULK_SANDBOX_PREPARED_NO_LISTENERS', candidate=str(candidate),
                  candidate_manifest_sha256=sha(candidate / 'manifest.json'), source_hashes=before,
                  state_copy_sha256=sha(out / 'gamedata/state.json'), shop_copy_sha256=sha(out / 'gamedata/shop.json'),
                  private_http_sha256=sha(http), production_written=False, listener_started=False)
    (out / 'prepare-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps({'status': report['status'], 'server': str(out), 'files': len(paths)}))
