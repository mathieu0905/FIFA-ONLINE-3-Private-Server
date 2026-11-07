"""Sealed, reversible main-version bulk roster transaction. Default read-only preview."""
from pathlib import Path
import argparse, datetime, hashlib, importlib.util, json, os, shutil, socket, subprocess, sys, uuid
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
MANIFEST = 'patches/bulk-seasons-release-manifest.json'
RECEIPT = 'patches/bulk-seasons-release-installed.json'
SELF = 'patches/bulk_seasons_preflight.py'


def sha(p):
    with Path(p).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def digest(p):
    return sha(p) if Path(p).is_file() else None


def read(p):
    return json.loads(Path(p).read_text('utf-8-sig'))


def atomic_json(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_name(p.name + '.bulk-' + uuid.uuid4().hex)
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, p)
    finally:
        temporary.unlink(missing_ok=True)


def target(roots, row):
    assert row['root'] in roots
    relative = row['relative'].replace('\\', '/')
    assert relative and ':' not in relative and not relative.startswith('/') and '..' not in Path(relative).parts
    result = (roots[row['root']] / relative).resolve()
    assert result.is_relative_to(roots[row['root']]) and result != roots[row['root']]
    assert result.name not in ('state.json', 'shop.json'), 'Bulk publisher cannot target user assets'
    assert not result.name.startswith(('state.json.', 'shop.json.'))
    return result


def stopped():
    listing = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq fifazf.exe', '/FO', 'CSV', '/NH'], text=True, errors='replace')
    assert 'fifazf.exe' not in listing.lower(), 'Exit the game normally before installation'
    net = subprocess.check_output(['netstat', '-ano', '-p', 'tcp'], text=True, errors='replace')
    for line in net.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0] == 'TCP' and fields[3] == 'LISTENING':
            assert int(fields[1].rsplit(':', 1)[1]) not in (443, 8088, 18088, 28000, 28001, 28002), 'Stop the current FO3 services before installing'


def loader(folder):
    manifest = read(folder / 'bulk-seasons-release-manifest.json')
    entry = next(r for r in manifest['files'] if r['root'] == 'server' and r['relative'] == SELF)
    assert sha(entry['source']) == entry['sha256']
    spec = importlib.util.spec_from_file_location('sealed_bulk_preflight', entry['source'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module, manifest


def preview(folder, roots):
    child, m = loader(folder)
    assert m['state_shop_replaced'] is False and m['registered_cards'] == 504
    rows = m['files']
    assert len({(r['root'], r['relative'].casefold()) for r in rows}) == len(rows)
    for row in rows:
        assert sha(row['source']) == row['sha256'], row['source']
        assert digest(target(roots, row)) == row['parent_sha256'], 'Parent changed: ' + row['relative']
    composed, validator = child._compose(roots['server'], roots['client'], m, installed=False)
    replacements = validator.table(rows)
    before = []
    for entry in composed['guards']:
        key = validator.canonical(entry)
        if key in replacements:
            previous = replacements[key]['parent_sha256']
            if previous is None:
                continue
            entry = dict(entry, sha256=previous)
        before.append(entry)
    composed['guards'] = before
    result = validator.verify_manifest(composed, roots['server'], roots['client'])
    assert not (roots['server'] / MANIFEST).exists() and not (roots['server'] / RECEIPT).exists()
    return child, m, result


def commit_transaction(roots, entries, backup, validate, fail_after=None):
    """All staging and backups precede the first switch; failed switches restore only files."""
    for index, entry in enumerate(entries):
        dest = target(roots, entry)
        assert digest(dest) == entry['parent_sha256']
        stage = backup / f'{index:04}.stage'
        shutil.copyfile(entry['source'], stage)
        assert sha(stage) == entry['sha256']
        entry['stage'] = stage.name
        entry['backup'] = f'{index:04}.before'
        if entry['parent_sha256'] is not None:
            shutil.copyfile(dest, backup / entry['backup'])
            assert sha(backup / entry['backup']) == entry['parent_sha256']
    validate()
    for entry in entries:
        assert digest(target(roots, entry)) == entry['parent_sha256']
        assert sha(entry['source']) == entry['sha256']
    tx = dict(status='prepared', server=str(roots['server']), client=str(roots['client']), entries=entries, completed=[])
    atomic_json(backup / 'transaction.json', tx)
    try:
        for index, entry in enumerate(entries):
            dest = target(roots, entry)
            assert digest(dest) == entry['parent_sha256']
            dest.parent.mkdir(parents=True, exist_ok=True)
            stage = dest.with_name(dest.name + '.bulk-install-' + uuid.uuid4().hex)
            try:
                shutil.copyfile(backup / entry['stage'], stage)
                assert sha(stage) == entry['sha256']
                os.replace(stage, dest)
            finally:
                stage.unlink(missing_ok=True)
            tx['completed'].append(index)
            atomic_json(backup / 'transaction.json', tx)
            if fail_after == index + 1:
                raise OSError('Injected bulk switch failure')
        return tx
    except BaseException:
        restore_completed(roots, tx, backup)
        tx['status'] = 'rolled_back'
        atomic_json(backup / 'transaction.json', tx)
        raise


def restore_completed(roots, tx, backup):
    for index in reversed(tx['completed']):
        entry = tx['entries'][index]
        dest = target(roots, entry)
        assert digest(dest) == entry['sha256'], 'Later edit preserved during rollback'
        if entry['parent_sha256'] is None:
            dest.unlink()
        else:
            source = backup / entry['backup']
            assert sha(source) == entry['parent_sha256']
            temp = dest.with_name(dest.name + '.bulk-restore-' + uuid.uuid4().hex)
            try:
                shutil.copyfile(source, temp); os.replace(temp, dest)
            finally:
                temp.unlink(missing_ok=True)


def install(folder, server, client, apply=False, review_sha=None):
    folder = Path(folder).resolve()
    roots = {'server': Path(server).resolve(), 'client': Path(client).resolve()}
    assert roots['server'] != roots['client'] and not roots['server'].is_relative_to(roots['client']) and not roots['client'].is_relative_to(roots['server'])
    child, m = loader(folder)
    if (roots['server'] / RECEIPT).exists():
        assert sha(roots['server'] / MANIFEST) == sha(folder / 'bulk-seasons-release-manifest.json')
        return dict(status='ALREADY_INSTALLED_BULK_SEASONS', preflight=child.preflight(**roots))
    child, m, result = preview(folder, roots)
    if not apply:
        return dict(status='DRYRUN_BULK_SEASONS_PASS', payloads=len(m['files']), new_cards=len(m['added_spids']), parent_preflight=result,
                    manifest_sha256=sha(folder / 'bulk-seasons-release-manifest.json'))
    assert review_sha == sha(folder / 'bulk-seasons-release-manifest.json'), 'Supply the exact reviewed manifest hash'
    stopped()
    lock = roots['server'] / '.shop-release.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)
    try:
        stopped(); child, m, _ = preview(folder, roots)
        backup = roots['server'] / 'backups' / ('bulk-seasons-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir(parents=True)
        protected = {name: sha(roots['server'] / 'gamedata' / name) for name in ('state.json', 'shop.json', 'pack_cadence.json')}
        for name in protected:
            shutil.copyfile(roots['server'] / 'gamedata' / name, backup / ('audit-' + name))
        receipt = dict(status='INSTALLED_BULK_SEASONS', release_id=m['release_id'], manifest_sha256=review_sha,
                       backup=str(backup), added_spids=m['added_spids'], registered_cards=504, native_status='PENDING', state_shop_replaced=False)
        atomic_json(backup / 'receipt-candidate.json', receipt)
        entries = [dict(r) for r in m['files']] + [dict(root='server', relative=MANIFEST, source=str(folder / 'bulk-seasons-release-manifest.json'), parent_sha256=None, sha256=review_sha),
                   dict(root='server', relative=RECEIPT, source=str(backup / 'receipt-candidate.json'), parent_sha256=None, sha256=sha(backup / 'receipt-candidate.json'))]

        def validate():
            stopped(); preview(folder, roots)
            assert all(sha(roots['server'] / 'gamedata' / n) == h for n, h in protected.items())

        tx = commit_transaction(roots, entries, backup, validate)
        try:
            verification = child.preflight(**roots)
            assert all(sha(roots['server'] / 'gamedata' / n) == h for n, h in protected.items())
            tx.update(status='installed', protected=protected, preflight=verification)
            atomic_json(backup / 'transaction.json', tx)
        except BaseException:
            restore_completed(roots, tx, backup)
            tx['status'] = 'rolled_back'; atomic_json(backup / 'transaction.json', tx)
            raise
        return dict(status='INSTALLED_BULK_SEASONS_NATIVE_PENDING', backup=str(backup), new_cards=len(m['added_spids']), preflight=verification, state_shop_unchanged=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True, type=Path)
    parser.add_argument('--server', default='D:/FO3ID/server')
    parser.add_argument('--client', default='D:/FO3ID/32795')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--review-sha')
    args = parser.parse_args()
    print(json.dumps(install(args.release, args.server, args.client, args.apply, args.review_sha), ensure_ascii=True))
