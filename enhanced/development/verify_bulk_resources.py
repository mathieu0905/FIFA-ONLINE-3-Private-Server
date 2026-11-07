"""Read-only identity, language, portrait and model dependency checks for the full batch."""
from pathlib import Path
import argparse, hashlib, json, sqlite3, sys
from PIL import Image

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
WORK = Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path.insert(0, str(WORK / 'work/season_expansion'))
import roster_import as codec

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate', required=True, type=Path)
args = parser.parse_args()
candidate = args.candidate.resolve()
assert candidate.is_relative_to(ROOT / 'candidates')
manifest = json.loads((candidate / 'manifest.json').read_text('utf-8'))
registry = json.loads((candidate / 'custom_rosters.json').read_text('utf-8'))
for relative, digest in manifest['files'].items():
    assert codec.sha(candidate / relative) == digest, relative
ids = {r['base_playerid'] for r in registry['cards']}
languages = []
b, d, *_ = codec.load_codecs(Path('D:/FO3ID/server'))
for lang in ['eng', 'chi', 'ind', 'kor', 'tha', 'vie']:
    raw = bytes(d.decrypt(b.read(candidate / 'data_0.big', f'data/db2/{lang}.db.db2')))
    with sqlite3.connect(':memory:') as db:
        db.deserialize(b'SQLite format 3\0' + raw[16:])
        assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
        for pid in ids:
            row = db.execute('select full,short from names where playerid=?', (pid,)).fetchone()
            assert row and row[0] and '\ufffd' not in row[0] and '?' not in row[0], (lang, pid, row)
    languages.append(dict(language=lang, player_identities=len(ids), missing_names=0))
portraits = []
for p in (candidate / 'assets/players').glob('*.png'):
    with Image.open(p) as image:
        image.verify()
    with Image.open(p) as image:
        assert image.width > 0 and image.height > 0 and image.format == 'PNG'
        portraits.append(dict(spid=int(p.stem[1:]), width=image.width, height=image.height, sha256=codec.sha(p)))
assert len(portraits) == manifest['net_new_vs_formal']
new = {r['fo3_spid'] for r in registry['cards']} - {13020801, 13028130, 13158023}
assert {r['spid'] for r in portraits} == new
model_manifest = Path(manifest['model_manifest'])
assert codec.sha(model_manifest) == manifest['model_manifest_sha256']
models = json.loads(model_manifest.read_text('utf-8'))
archives = []
for row in models['archives']:
    path = Path(row['target'])
    assert codec.sha(path) == row['target_sha256']
    archives.append(dict(path=str(path), sha256=row['target_sha256']))
report = dict(status='PASS_BULK_RESOURCES_NATIVE_PENDING', registered_cards=len(registry['cards']),
              distinct_identities=len(ids), six_client_language_databases=languages, portraits_checked=len(portraits),
              portraits=portraits, converted_model_archive_dependencies=archives,
              source_manifest_sha256=codec.sha(candidate / 'manifest.json'), production_written=False,
              native_verified=False, match_verified=False)
out = ROOT / (candidate.name + '-resources-PASS.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps({k: report[k] for k in ('status', 'registered_cards', 'distinct_identities', 'portraits_checked')}))
