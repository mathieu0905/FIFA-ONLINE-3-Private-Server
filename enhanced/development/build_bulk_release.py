"""Freeze a main-version installation delta on the latest returned XP30 baseline."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, shutil, sqlite3, subprocess, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
WORK = Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
SERVER = Path('D:/FO3ID/server')
CLIENT = Path('D:/FO3ID/32795')
CANDIDATE = ROOT / 'candidates/bulk-seasons-v2'
sys.path.insert(0, str(WORK / 'work/season_expansion'))
import roster_import as codec


def read(p):
    return json.loads(p.read_text('utf-8-sig'))


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')


def load(p, name):
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def build(out):
    out = out.resolve()
    assert out.is_relative_to(ROOT / 'releases') and not out.exists()
    # Temporary diagnostic layers must first be returned by their owner.
    play = (SERVER / 'play-local.bat').read_text('utf-8')
    assert 'patches\\xp30_batch_preflight.py' in play, 'Wait for XP owner to restore the full registered baseline'
    parent = load(SERVER / 'patches/xp30_batch_preflight.py', 'bulk_release_xp')
    before = parent.preflight(SERVER, CLIENT)
    parent_composed = parent.compose_manifest(SERVER, CLIENT)
    validator = parent.parent(SERVER, parent.read(SERVER / parent.MANIFEST))
    parent_guards = validator.table(parent_composed['guards'])
    candidate = read(CANDIDATE / 'manifest.json')
    for rel, digest in candidate['files'].items():
        assert codec.sha(CANDIDATE / rel) == digest, rel
    with sqlite3.connect((CANDIDATE / 'fifadb.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        db.execute('attach database ? as formal', ((SERVER / 'gamedata/fifadb.sqlite').as_uri() + '?mode=ro',))
        for (table,) in db.execute("select name from formal.sqlite_master where type='table'").fetchall():
            assert not db.execute(f'select * from formal."{table}" except select * from main."{table}" limit 1').fetchone(), table
        original_ids = {r[0] for r in db.execute('select spid from formal.players')}
        new_ids = sorted(r[0] for r in db.execute('select spid from players') if r[0] not in original_ids)
    current_registry = read(SERVER / 'gamedata/custom_rosters.json')
    target_registry = read(CANDIDATE / 'custom_rosters.json')
    assert all(r in target_registry['cards'] for r in current_registry['cards'])
    out.mkdir(parents=True)
    payload = out / 'payload'
    payload.mkdir()
    # Compose names on the effective XP30/AI-filter Module, not the old 23-level candidate.
    ui_module = load(WORK / 'work/season_expansion/rebase_season_ui.py', 'bulk_release_ui')
    ui = ui_module.build(CLIENT / 'data/ui/libs/Module.big', CLIENT / '_cache/games/fo3id/externalAssets/language_chi.big', out / 'ui', [12, 13, 84])
    rows = []

    def add(root, relative, source):
        source = source.resolve()
        target = (SERVER if root == 'server' else CLIENT) / relative
        previous = codec.sha(target) if target.is_file() else None
        digest = codec.sha(source)
        if previous == digest:
            return
        key = (root, relative.casefold())
        if key in parent_guards:
            assert previous == parent_guards[key]['sha256'], ('parent guard', key)
        assert key not in {(r['root'], r['relative'].casefold()) for r in rows}
        rows.append(dict(root=root, relative=relative, source=str(source), sha256=digest, parent_sha256=previous))

    for relative in ('fifadb.sqlite', 'custom_rosters.json'):
        add('server', 'gamedata/' + relative, CANDIDATE / relative)
    add('server', 'responses/static_roster.json', CANDIDATE / 'static_roster.json')
    add('client', 'data/data_0.big', CANDIDATE / 'data_0.big')
    add('client', 'data/ui/libs/Module.big', out / 'ui/Module.big')
    language = out / 'ui/language_chi.big'
    add('server', 'patches/language_chi.big', language)
    for prefix in ('_cache/games/fo3id', '_cache/cdn'):
        add('client', prefix + '/externalAssets/language_chi.big', language)
        for image in sorted((CANDIDATE / 'assets/players').glob('*.png')):
            add('client', prefix + '/externalAssets/players/' + image.name, image)
    check = read(SERVER / 'patches/验证结果.json')
    check.update(result_keys=ui['language_keys_after'], package_bytes=language.stat().st_size, sha256=codec.sha(language),
                 latest_roster_import='bulk-seasons-504-v1', bulk_native_validation='pending')
    write(payload / 'language-check.json', check)
    add('server', 'patches/验证结果.json', payload / 'language-check.json')
    # Preserve every already-installed 3D member; only add the reviewed missing models.
    big, decrypt, *_ = codec.load_codecs(SERVER)
    model_report = []
    models = read(Path(candidate['model_manifest']))
    for archive in models['archives']:
        source = Path(archive['target'])
        assert codec.sha(source) == archive['target_sha256']
        relative = 'data/' + source.name
        current = CLIENT / relative
        old = {e[0]: e for e in big.entries(current)}
        new = {e[0]: e for e in big.entries(source)}
        assert old.keys() <= new.keys(), relative
        with current.open('rb') as f, source.open('rb') as g:
            for name, entry in old.items():
                newer = new[name]
                f.seek(entry[1]); g.seek(newer[1])
                assert f.read(entry[2]) == g.read(newer[2]), ('installed model member differs', relative, name)
        model_report.append(dict(relative=relative, preserved_compressed_members=len(old), additions=len(new) - len(old)))
        add('client', relative, source)
    # Check every current player/language row and all unrelated compressed data0 members.
    a, b = big.entries(CLIENT / 'data/data_0.big'), big.entries(CANDIDATE / 'data_0.big')
    allowed = {codec.MEMBER, 'data/fifarna/lua/assets/player.lua'} | {f'data/db2/{x}.db.db2' for x in ('eng', 'chi', 'ind', 'kor', 'tha', 'vie')}
    assert [r[0] for r in a] == [r[0] for r in b]
    with (CLIENT / 'data/data_0.big').open('rb') as f, (CANDIDATE / 'data_0.big').open('rb') as g:
        for old, new in zip(a, b):
            if old[0] not in allowed:
                f.seek(old[1]); g.seek(new[1]); assert f.read(old[2]) == g.read(new[2]), old[0]
    for member in sorted(allowed - {'data/fifarna/lua/assets/player.lua'}):
        with sqlite3.connect(':memory:') as db:
            decoded = bytes(decrypt.decrypt(big.read(CANDIDATE / 'data_0.big', member)))
            db.deserialize(b'SQLite format 3\0' + decoded[16:])
            old = bytes(decrypt.decrypt(big.read(CLIENT / 'data/data_0.big', member)))
            old_path = out / (member.rsplit('/', 1)[-1] + '.before.sqlite')
            old_path.write_bytes(b'SQLite format 3\0' + old[16:])
            db.execute('attach database ? as old', (str(old_path),))
            for (table,) in db.execute("select name from old.sqlite_master where type='table'").fetchall():
                assert not db.execute(f'select * from old."{table}" except select * from main."{table}" limit 1').fetchone(), (member, table)
    # The only backend change is to install registry search and limited-card NPC boundaries.
    text = (SERVER / 'http_config.py').read_text('utf-8')
    marker = 'if __name__ == "__main__":'
    assert text.count(marker) == 1 and 'legend_moments_bulk_npc.install' not in text
    hook = '\nimport modern_registry_search\nmodern_registry_search.install(sys.modules[__name__])\nimport legend_moments_bulk_npc\nlegend_moments_bulk_npc.install(sys.modules[__name__])\n\n'
    (payload / 'http_config.py').write_text(text.replace(marker, hook + marker), 'utf-8')
    add('server', 'http_config.py', payload / 'http_config.py')
    add('server', 'legend_moments_bulk_npc.py', CANDIDATE / 'legend_moments_bulk_npc.py')
    add('server', 'modern_registry_search.py', Path('D:/FO3QA/modern_player_integration_v2/search-sidecar-v1/modern_registry_search.py'))
    add('server', 'patches/bulk_seasons_preflight.py', ROOT / 'bulk_seasons_preflight.py')
    (payload / 'play-local.bat').write_text(play.replace('patches\\xp30_batch_preflight.py', 'patches\\bulk_seasons_preflight.py'), 'utf-8', newline='')
    add('server', 'play-local.bat', payload / 'play-local.bat')
    parent_files = {name: codec.sha(SERVER / name) for name in ('patches/xp30_batch_preflight.py', 'patches/xp30-batch-release-manifest.json')}
    parent_receipt = read(SERVER / 'patches/xp30-batch-release-installed.json')
    manifest = dict(schema=1, phase='MAIN_BULK_SEASONS', release_id=out.name, client_root=str(CLIENT), server_root=str(SERVER),
                    candidate_manifest_sha256=codec.sha(CANDIDATE / 'manifest.json'), parent_files=parent_files,
                    parent_receipt_identity={k: v for k, v in parent_receipt.items() if k != 'native_status'},
                    target_policy=[dict(root=r['root'], relative=r['relative']) for r in rows], files=rows,
                    added_spids=new_ids, registered_cards=504, state_shop_replaced=False, native_status='PENDING',
                    artifact_proofs={'resource': codec.sha(ROOT / 'bulk-seasons-v2-resources-PASS.json'), 'structure': codec.sha(CANDIDATE / 'manifest.json')})
    write(out / 'bulk-seasons-release-manifest.json', manifest)
    proof = dict(status='FROZEN_MAIN_BULK_CANDIDATE_NOT_INSTALLED', preflight_before=before, model_members=model_report,
                 data0_non_target_compressed_members_preserved=263, all_current_player_and_language_rows_preserved=True,
                 xp_methods_and_ai_filter_preserved=True, writes=len(rows) + 2, new_cards=len(new_ids), state_shop_replaced=False)
    write(out / 'build-report.json', proof)
    # A dry compose checks ancestry and every target parent, but does not claim installation.
    child = load(ROOT / 'bulk_seasons_preflight.py', 'bulk_release_child')
    composed, v = child._compose(SERVER, CLIENT, manifest, installed=False)
    rowmap = v.table(rows)
    before_rows = []
    for entry in composed['guards']:
        key = v.canonical(entry)
        if key in rowmap:
            previous = rowmap[key]['parent_sha256']
            if previous is None:
                assert not v.path({'server': SERVER, 'client': CLIENT}, entry).exists()
                continue
            entry = dict(entry, sha256=previous)
        before_rows.append(entry)
    composed['guards'] = before_rows
    v.verify_manifest(composed, SERVER, CLIENT)
    print(json.dumps(dict(status=proof['status'], release=str(out), new_cards=len(new_ids), payloads=len(rows), manifest_sha256=codec.sha(out / 'bulk-seasons-release-manifest.json'))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    build(parser.parse_args().out)
