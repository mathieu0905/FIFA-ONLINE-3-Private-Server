"""Narrow moments display release, using the tested bulk file transaction core."""
from pathlib import Path
import argparse, datetime, importlib.util, json, os, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import install_bulk_seasons as transaction
MANIFEST = 'patches/moments-display-release-manifest.json'
RECEIPT = 'patches/moments-display-release-installed.json'
SELF = 'patches/moments_display_preflight.py'


def loader(folder):
    m = transaction.read(folder / 'moments-display-release-manifest.json')
    row = next(r for r in m['files'] if r['root'] == 'server' and r['relative'] == SELF)
    assert transaction.sha(row['source']) == row['sha256']
    spec = importlib.util.spec_from_file_location('sealed_moments_display_child', row['source'])
    child = importlib.util.module_from_spec(spec); spec.loader.exec_module(child)
    return child, m


def preview(folder, roots):
    child, m = loader(folder)
    assert m['phase'] == 'MOMENTS_DISPLAY_FIX' and m['state_shop_replaced'] is False
    assert m['affected_cards'] == 123 and m['affiliation_teamid'] == 999984
    assert len(m['files']) == len({(r['root'], r['relative'].casefold()) for r in m['files']})
    for row in m['files']:
        assert transaction.sha(row['source']) == row['sha256']
        assert transaction.digest(transaction.target(roots, row)) == row['parent_sha256'], 'Current source changed: ' + row['relative']
    composed, validator = child._compose(roots['server'], roots['client'], m, installed=False)
    replacements = validator.table(m['files']); before = []
    for row in composed['guards']:
        key = validator.canonical(row)
        if key in replacements:
            digest = replacements[key]['parent_sha256']
            if digest is None:
                continue
            row = dict(row, sha256=digest)
        before.append(row)
    composed['guards'] = before
    proof = validator.verify_manifest(composed, **roots)
    assert not (roots['server'] / MANIFEST).exists() and not (roots['server'] / RECEIPT).exists()
    return child, m, proof


def install(folder, apply=False, review_sha=None):
    folder = Path(folder).resolve()
    roots = {'server': Path('D:/FO3ID/server').resolve(), 'client': Path('D:/FO3ID/32795').resolve()}
    child, m = loader(folder)
    if (roots['server'] / RECEIPT).exists():
        assert transaction.sha(roots['server'] / MANIFEST) == transaction.sha(folder / 'moments-display-release-manifest.json')
        return dict(status='ALREADY_INSTALLED_MOMENTS_DISPLAY', preflight=child.preflight(**roots))
    child, m, proof = preview(folder, roots)
    if not apply:
        return dict(status='DRYRUN_MOMENTS_DISPLAY_PASS', payloads=len(m['files']), parent_preflight=proof)
    assert review_sha == transaction.sha(folder / 'moments-display-release-manifest.json')
    transaction.stopped()
    lock = roots['server'] / '.shop-release.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)
    try:
        transaction.stopped(); preview(folder, roots)
        backup = roots['server'] / 'backups' / ('moments-display-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir(parents=True)
        protected_files = [roots['server'] / f'gamedata/{n}' for n in ('state.json', 'shop.json', 'pack_cadence.json')]
        protected_files.extend([roots['server'] / 'http_config.py', roots['client'] / 'data/ui/libs/Module.big', roots['client'] / 'data/ui/TeamManagementExpCapsuleScreen.big'])
        protected = {str(p): transaction.sha(p) for p in protected_files}
        import shutil
        for name in ('state.json', 'shop.json'):
            shutil.copyfile(roots['server'] / 'gamedata' / name, backup / ('audit-' + name))
        receipt = dict(status='INSTALLED_MOMENTS_DISPLAY_FIX', release_id=m['release_id'], manifest_sha256=review_sha,
                       backup=str(backup), affected_cards=123, affiliation_teamid=999984, native_status='PENDING', state_shop_replaced=False)
        transaction.atomic_json(backup / 'receipt-candidate.json', receipt)
        entries = [dict(r) for r in m['files']] + [dict(root='server', relative=MANIFEST, source=str(folder / 'moments-display-release-manifest.json'), parent_sha256=None, sha256=review_sha),
                   dict(root='server', relative=RECEIPT, source=str(backup / 'receipt-candidate.json'), parent_sha256=None, sha256=transaction.sha(backup / 'receipt-candidate.json'))]

        def validate():
            transaction.stopped(); preview(folder, roots)
            assert all(transaction.sha(path) == digest for path, digest in protected.items())

        tx = transaction.commit_transaction(roots, entries, backup, validate)
        try:
            proof = child.preflight(**roots)
            assert all(transaction.sha(path) == digest for path, digest in protected.items())
            tx.update(status='installed', protected=protected, preflight=proof)
            transaction.atomic_json(backup / 'transaction.json', tx)
        except BaseException:
            transaction.restore_completed(roots, tx, backup)
            tx['status'] = 'rolled_back'; transaction.atomic_json(backup / 'transaction.json', tx)
            raise
        return dict(status='INSTALLED_MOMENTS_DISPLAY_NATIVE_PENDING', backup=str(backup), preflight=proof, protected_unchanged=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--review-sha')
    args = parser.parse_args()
    print(json.dumps(install(args.release, args.apply, args.review_sha), ensure_ascii=True))
