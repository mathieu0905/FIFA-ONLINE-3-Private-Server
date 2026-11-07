from pathlib import Path
import json, uuid
import install_bulk_seasons as release

root = Path(__file__).resolve().parent / 'transaction-tests' / uuid.uuid4().hex
root.mkdir(parents=True)
results = []
for size, failure in [(0, None), (1, None), (7, 1), (7, 7), (1004, None)]:
    case = root / f'n{size}-failure{failure}'
    roots = {name: case / name for name in ('server', 'client')}
    for p in roots.values():
        p.mkdir(parents=True)
    backup = case / 'backup'; backup.mkdir()
    source = case / 'sources'; source.mkdir()
    plans = []
    original = {}
    for i in range(size):
        kind = 'client' if i % 2 else 'server'
        relative = f'payloads/test-{i}.bin'
        dest = roots[kind] / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        before = None
        if i % 3:
            dest.write_bytes(('old' + str(i)).encode())
            before = release.sha(dest)
        original[(kind, relative)] = before
        src = source / f'{i}.bin'; src.write_bytes(('new' + str(i)).encode())
        plans.append(dict(root=kind, relative=relative, source=str(src), sha256=release.sha(src), parent_sha256=before))
    try:
        tx = release.commit_transaction(roots, plans, backup, lambda: None, fail_after=failure)
        assert failure is None
        assert all(release.digest(release.target(roots, r)) == r['sha256'] for r in plans)
        release.restore_completed(roots, tx, backup)
    except OSError as error:
        assert failure is not None and 'Injected' in str(error)
    assert all(release.digest(roots[kind] / relative) == value for (kind, relative), value in original.items())
    results.append(dict(size=size, failure=failure, old_bytes_and_absence_restored=True))
for relative in ('gamedata/state.json', 'gamedata/shop.json', '../outside.bin', 'D:/outside.bin'):
    try:
        release.target(roots, dict(root='server', relative=relative))
    except AssertionError:
        continue
    raise AssertionError('Forbidden target accepted: ' + relative)
report = dict(status='PASS_PRIVATE_BULK_INSTALL_TRANSACTION', cases=results, state_shop_and_escape_targets_rejected=True)
(root / 'result.json').write_text(json.dumps(report, indent=2), 'utf-8')
Path(__file__).with_name('install-transaction-PASS.json').write_text(json.dumps(report, indent=2), 'utf-8')
print(json.dumps(report))
