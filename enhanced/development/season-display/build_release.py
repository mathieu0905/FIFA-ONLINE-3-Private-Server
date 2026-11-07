from pathlib import Path
import argparse, importlib.util, json, re, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
S = Path('D:/FO3ID/server'); C = Path('D:/FO3ID/32795')


def read(p):
    return json.loads(p.read_text('utf-8-sig'))


def load(p, name):
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(); candidate = args.candidate.resolve(); out = args.out.resolve()
    assert candidate.is_relative_to(ROOT) and out.is_relative_to(ROOT) and not out.exists()
    child = load(ROOT / 'moments_display_preflight.py', 'moments_candidate_preflight')
    sha = child.sha
    proof = read(candidate / 'manifest.json')
    for rel, digest in proof['files'].items():
        assert sha(candidate / rel) == digest
    for path, digest in proof['source_hashes'].items():
        assert sha(path) == digest, ('Candidate input changed', path)
    play = (S / 'play-local.bat').read_text('utf-8')
    matches = re.findall(r'patches\\([A-Za-z0-9_]+_preflight\.py)', play)
    assert len(matches) == 1
    parent_relative = 'patches/' + matches[0]
    parent = load(S / parent_relative, 'moments_release_parent')
    parent_check = parent.preflight(S, C)
    out.mkdir(parents=True)
    rows = []

    def add(root, relative, source):
        target = (S if root == 'server' else C) / relative
        before = sha(target) if target.is_file() else None
        digest = sha(source)
        if before == digest:
            return
        rows.append(dict(root=root, relative=relative, source=str(Path(source).resolve()), parent_sha256=before, sha256=digest))

    for source, relative in [('fifadb.sqlite', 'gamedata/fifadb.sqlite'), ('custom_rosters.json', 'gamedata/custom_rosters.json'),
                             ('server_display_zh.json', 'server_display_zh.json'), ('Label.big', 'patches/Label.big')]:
        add('server', relative, candidate / source)
    add('client', 'data/data_0.big', candidate / 'data_0.big')
    add('client', 'data/ui/components/Label.big', candidate / 'Label.big')
    for lang in ('chi', 'eng', 'ind', 'kor', 'tha', 'vie'):
        add('client', f'data/ui/localization/{lang}.big', candidate / f'{lang}.big')
    for prefix in ('_cache/games/fo3id', '_cache/cdn'):
        for size, letter in [('small', 's'), ('large', 'l')]:
            add('client', f'{prefix}/externalAssets/crests/{size}/{letter}999984.png', candidate / f'crests/{size}/{letter}999984.png')
    (out / 'play-local.bat').write_text(play.replace('patches\\' + matches[0], 'patches\\moments_display_preflight.py'), 'utf-8', newline='')
    add('server', 'play-local.bat', out / 'play-local.bat')
    add('server', child.SELF, ROOT / 'moments_display_preflight.py')
    m = dict(schema=1, phase='MOMENTS_DISPLAY_FIX', release_id=out.name, client_root=str(C), parent_preflight=parent_relative,
             parent_files={rel: sha(S / rel) for rel in (parent_relative, parent.MANIFEST, parent.RECEIPT)},
             files=rows, target_policy=[dict(root=r['root'], relative=r['relative']) for r in rows],
             state_shop_replaced=False, season_id=84, affected_cards=123, affiliation_teamid=999984,
             candidate=str(candidate), candidate_sha256=sha(candidate / 'manifest.json'), native_status='PENDING')
    (out / 'moments-display-release-manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), 'utf-8')
    composed, validator = child._compose(S, C, m, installed=False)
    replacements = validator.table(rows); before_rows = []
    for row in composed['guards']:
        key = validator.canonical(row)
        if key in replacements:
            previous = replacements[key]['parent_sha256']
            if previous is None:
                continue
            row = dict(row, sha256=previous)
        before_rows.append(row)
    composed['guards'] = before_rows; validator.verify_manifest(composed, S, C)
    print(json.dumps(dict(status='MOMENTS_DISPLAY_RELEASE_DRYRUN_PASS', release=str(out), payloads=len(rows), parent=parent_relative,
                          manifest_sha256=sha(out / 'moments-display-release-manifest.json'))))
