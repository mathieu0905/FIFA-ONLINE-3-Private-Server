"""CAS release transaction shared by bootstrap installation and live business publishing."""
from pathlib import Path
from contextlib import contextmanager
import copy, datetime, hashlib, importlib.util, json, os, re

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def body(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf8')

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.hot-' + str(os.getpid()) + '.tmp')
    try:
        with tmp.open('xb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

@contextmanager
def locks(server, task):
    held = []
    try:
        for name in ('.shop-release.lock', '.fo3-publish.lock'):
            p = server / name
            token = body(dict(task=task, pid=os.getpid()))
            fd = os.open(p, os.O_EXCL | os.O_CREAT | os.O_WRONLY | os.O_BINARY)
            held.append((p, fd, token)); os.write(fd, token); os.fsync(fd)
        yield
    finally:
        for p, fd, token in reversed(held):
            os.close(fd)
            if p.exists() and p.read_bytes() == token:
                p.unlink()

def commit(server, client, tag, payload, activate=None, fail_after=None):
    """Caller holds shared locks. Payload is {server-relative path: bytes}.

    activate(proof) optionally supplies mutable active.json, committed last.
    Neither services nor live assets are opened for writing here.
    """
    server, client = Path(server), Path(client)
    play = (server / 'play-local.bat').read_bytes()
    matches = re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py', play)
    if len(matches) != 1:
        raise RuntimeError('Unrecognized current release entry')
    parent_rel = matches[0].decode().replace('\\', '/')
    parent = load(server / parent_rel, 'hot_parent_' + tag)
    prior = parent.preflight(server, client)
    composition = copy.deepcopy(parent.compose_manifest(server, client))
    table = {(g['root'], g['relative'].replace('\\', '/').casefold()): g for g in composition['guards']}
    if len(table) != len(composition['guards']):
        raise RuntimeError('Duplicate inherited guard')
    revision = tag + '-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    stem = revision.replace('-', '_')
    helper = 'patches/' + stem + '_preflight.py'
    manifest = 'patches/' + revision + '-installed.json'
    receipt = 'patches/' + revision + '-receipt.json'
    old_receipt = json.loads((server / parent.RECEIPT).read_text('utf8'))
    code = (server / parent_rel).read_text('utf8')
    code = code.replace(parent.MANIFEST, manifest).replace(parent.RECEIPT, receipt).replace(parent.SELF, helper)
    code = code.replace(old_receipt['status'], 'INSTALLED_HOT_BUSINESS').replace(prior['status'], 'HOT_BUSINESS_PREFLIGHT_PASS')
    compile(code, helper, 'exec')
    payload = dict(payload)
    payload[helper] = code.encode('utf8')
    payload['play-local.bat'] = play.replace(matches[0], helper.replace('/', '\\').encode())
    entries = []
    def entry(relative, data, guarded=True):
        target = (server / relative).resolve()
        if not target.is_relative_to(server.resolve()) or target == server.resolve():
            raise ValueError('Release path escape')
        before = sha(target) if target.exists() else None
        after = hashlib.sha256(data).hexdigest()
        if guarded:
            key = ('server', relative.casefold())
            if key in table and table[key]['sha256'] != before:
                raise RuntimeError('Changed guarded baseline: ' + relative)
            if key not in table and before is not None:
                raise RuntimeError('Unregistered existing file: ' + relative)
            table[key] = dict(root='server', relative=relative, sha256=after)
        entries.append(dict(relative=relative, target=target, before=before, after=after, data=data))
    for relative, data in payload.items():
        entry(relative, data)
    composition.update(guards=list(table.values()), files_verified=False)
    composition.setdefault('ancestry', []).append(dict(layer=tag, native_status='PENDING'))
    policy = dict(root='server', relative=parent.RECEIPT, installation_fields={k: v for k, v in old_receipt.items() if k != 'native_status'})
    if not any(p['root'] == policy['root'] and p['relative'] == policy['relative'] for p in composition.setdefault('receipt_policies', [])):
        composition['receipt_policies'].append(policy)
    mb = body(dict(schema=1, revision=revision, client=str(client), state_shop_replaced=False,
                   guards=composition['guards'], composition=composition, parent_preflight=parent_rel))
    rb = body(dict(status='INSTALLED_HOT_BUSINESS', revision=revision, manifest_sha256=hashlib.sha256(mb).hexdigest(), state_shop_replaced=False, native_status='PENDING'))
    proof = dict(manifest=manifest, receipt=receipt, manifest_sha256=hashlib.sha256(mb).hexdigest(), receipt_sha256=hashlib.sha256(rb).hexdigest())
    # Metadata has an external receipt binding and must not self-hash into its manifest.
    entry(manifest, mb, False); entry(receipt, rb, False)
    entries.sort(key=lambda e: e['relative'] == 'play-local.bat')
    if activate:
        entry('hot_updates/active.json', body(activate(proof)), False)
    backup = server / 'backups' / revision
    backup.mkdir(parents=True, exist_ok=False)
    journal = [{k: str(v) if isinstance(v, Path) else v for k, v in e.items() if k != 'data'} for e in entries]
    for i, e in enumerate(entries):
        if (sha(e['target']) if e['target'].exists() else None) != e['before']:
            raise RuntimeError('Concurrent edit before backup')
        if e['before'] is not None:
            (backup / str(i)).write_bytes(e['target'].read_bytes())
    atomic(backup / 'transaction.json', body(dict(status='PREPARED', files=journal)))
    done = []
    try:
        for i, e in enumerate(entries):
            if (sha(e['target']) if e['target'].exists() else None) != e['before']:
                raise RuntimeError('Concurrent edit during publication')
            atomic(e['target'], e['data']); done.append(i)
            if fail_after == i + 1:
                raise OSError('Injected failure')
        result = load(server / helper, 'hot_final_' + tag).preflight(server, client)
        atomic(backup / 'transaction.json', body(dict(status='INSTALLED', files=journal)))
    except BaseException:
        retained = []
        for i in reversed(done):
            e = entries[i]
            if not e['target'].exists() or sha(e['target']) != e['after']:
                retained.append(str(e['target'])); continue
            if e['before'] is None:
                e['target'].unlink()
            else:
                atomic(e['target'], (backup / str(i)).read_bytes())
        atomic(backup / 'transaction.json', body(dict(status='ROLLED_BACK', later_changes_retained=retained, files=journal)))
        raise
    return dict(status='INSTALLED_HOT_BUSINESS', preflight=result, backup=str(backup),
                top_preflight=str(server / helper), top_manifest=str(server / manifest), top_receipt=str(server / receipt),
                composition_available=True, function_signatures=dict(preflight='server=None,client=None', compose_manifest='server=None,client=None'),
                files={str(p): sha(p) for p in (server / helper, server / manifest, server / receipt, server / 'play-local.bat')},
                state_shop_written=False, services_action='No service start/stop/restart', native_verified=False,
                proof=proof)
