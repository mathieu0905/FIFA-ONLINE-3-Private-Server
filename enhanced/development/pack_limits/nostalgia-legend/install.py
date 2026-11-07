"""Atomic, hash-pinned code/assets installer. Never restores or writes state/shop."""
from pathlib import Path
from contextlib import contextmanager
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
EXPECTED={('server',n) for n in ('http_config.py','play-local.bat','patches/nostalgia_legend_preflight.py')}
def validate_rows(rows):
    keys=[(r.get('root'),r.get('relative','').replace('\\','/').casefold()) for r in rows]
    if len(keys)!=3 or len(set(keys))!=3 or set(keys)!=EXPECTED:raise RuntimeError('Expected exactly three reviewed server-only targets')
    for row,key in zip(rows,keys):
        if set(row)!={'root','relative','parent_sha256','sha256'}:raise RuntimeError('Unexpected target fields')
        if (row['parent_sha256'] is not None)!=(key[1] in {'http_config.py','play-local.bat'}):raise RuntimeError('Append-only target parent mismatch')

def blocking_processes(rows):
    client=any(r.get('root')=='client' for r in rows)
    game="$_.Name -eq 'fifazf.exe' -or " if client else ''
    query="Get-CimInstance Win32_Process | Where-Object { "+game+"($_.Name -match '^python(w)?\\.exe$' -and $_.CommandLine -like '*D:\\FO3ID\\server*' -and $_.CommandLine -match '(http_config|messenger)\\.py') } | Select-Object -ExpandProperty ProcessId"
    return [int(value) for value in subprocess.check_output(['powershell.exe','-NoProfile','-Command',query],text=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0).split()]

@contextmanager
def publish_lock(server):
    owned=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            path=server/name
            try:handle=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
            except FileExistsError:raise RuntimeError('Another publisher holds '+name)
            payload=json.dumps(dict(pid=os.getpid(),release='nostalgia-legend-set-v1')).encode()
            owned.append((path,handle,payload))
            os.write(handle,payload);os.fsync(handle)
        yield
    finally:
        for path,handle,payload in reversed(owned):
            os.close(handle)
            if path.exists() and path.read_bytes()==payload:path.unlink()

def install(server,client,allow_fixture=False,fail_after=None):
    server=Path(server).resolve();client=Path(client).resolve()
    if allow_fixture and not all(p.is_relative_to(R/'install-fixture') for p in (server,client)):raise RuntimeError('Fixture roots escape named fixture')
    validate_rows(json.loads((R/'nostalgia-legend-release-manifest.json').read_text(encoding='utf8'))['files'])
    with publish_lock(server):return _install_locked(server,client,allow_fixture,fail_after)
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
UNSPECIFIED=object()
def atomic(path,data,expected=UNSPECIFIED):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.product-packs-tmp')
    created=False
    try:
        with temporary.open('xb') as f:
            created=True;f.write(data);f.flush();os.fsync(f.fileno())
        if expected is not UNSPECIFIED and (sha(path) if path.exists() else None)!=expected:raise RuntimeError('Target drift immediately before write: '+str(path))
        os.replace(temporary,path)
    finally:
        if created and temporary.exists():temporary.unlink()

def _install_locked(server,client,allow_fixture=False,fail_after=None):
    roots={'server':Path(server).resolve(),'client':Path(client).resolve()}
    m=json.loads((R/'nostalgia-legend-release-manifest.json').read_text(encoding='utf8'))
    validate_rows(m['files'])
    v=load(R/'nostalgia_legend_preflight.py','product_install_validator')
    target_manifest=roots['server']/v.MANIFEST;target_receipt=roots['server']/v.RECEIPT
    if target_manifest.exists() or target_receipt.exists():
        assert target_manifest.read_bytes()==(R/'nostalgia-legend-release-manifest.json').read_bytes(),'Another product release is installed'
        return v.preflight(roots['server'],roots['client'])
    if not allow_fixture:
        blocked=blocking_processes(m['files'])
        if blocked:raise RuntimeError('Official managed services still active: '+str(blocked))
    parent=load(roots['server']/m['parent_preflight'],'install_parent')
    parent.preflight(roots['server'],roots['client'])
    composed,base=v._compose(roots['server'],roots['client'],m,installed=False)
    assert set(base.table(m['files']))==v.TARGETS
    for row in m['files']:
        destination=roots[row['root']]/row['relative'];source=R/'payload'/row['root']/row['relative']
        assert sha(source)==row['sha256'],'Candidate payload changed'
        assert (sha(destination) if destination.exists() else None)==row['parent_sha256'],'Live parent changed: '+str(destination)
    protected={name:sha(roots['server']/name) for name in ('gamedata/state.json','gamedata/shop.json') if (roots['server']/name).exists()}
    backup=R/'backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    # Read-only snapshots are evidence; rollback below only touches the whitelisted code/assets.
    for name in protected:
        destination=backup/'evidence'/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(roots['server']/name,destination)
    done=[]
    try:
        for index,row in enumerate(m['files']):
            destination=roots[row['root']]/row['relative'];source=R/'payload'/row['root']/row['relative']
            old=destination.read_bytes() if destination.exists() else None
            if old is not None:
                saved=backup/row['root']/row['relative'];saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(old)
            if (hashlib.sha256(old).hexdigest() if old is not None else None)!=row['parent_sha256']:raise RuntimeError('Target drift before backup: '+str(destination))
            atomic(destination,source.read_bytes(),expected=row['parent_sha256']);done.append((destination,old,row['sha256']))
            if fail_after==index+1:raise RuntimeError('Injected rollback test')
        manifest_bytes=(R/'nostalgia-legend-release-manifest.json').read_bytes()
        atomic(target_manifest,manifest_bytes,expected=None);done.append((target_manifest,None,hashlib.sha256(manifest_bytes).hexdigest()))
        receipt=dict(status='INSTALLED_NOSTALGIA_LEGEND_SET',release_id=m['release_id'],manifest_sha256=sha(target_manifest),state_shop_replaced=False)
        receipt_bytes=json.dumps(receipt,indent=2).encode()
        atomic(target_receipt,receipt_bytes,expected=None);done.append((target_receipt,None,hashlib.sha256(receipt_bytes).hexdigest()))
        result=v.preflight(roots['server'],roots['client'])
        for name,digest in protected.items():assert sha(roots['server']/name)==digest,'Live data changed during install'
    except BaseException as error:
        conflicts=[]
        for destination,old,after_hash in reversed(done):
            current=sha(destination) if destination.exists() else None
            if current!=after_hash:
                conflicts.append(dict(path=str(destination),expected_our_after=after_hash,current=current));continue
            if old is None:destination.unlink()
            else:
                try:atomic(destination,old,expected=after_hash)
                except BaseException as rollback_error:conflicts.append(dict(path=str(destination),error=str(rollback_error)))
        record=backup/'transaction.json'
        record.write_text(json.dumps(dict(status='ROLLBACK_CONFLICT_LATER_CHANGES_PRESERVED' if conflicts else 'ROLLED_BACK',error=str(error),conflicts=conflicts,
            targets=[dict(path=str(roots[row['root']]/row['relative']),before=row['parent_sha256'],our_after=row['sha256'],current=sha(roots[row['root']]/row['relative']) if (roots[row['root']]/row['relative']).exists() else None) for row in m['files']]),indent=2),encoding='utf8')
        if conflicts:raise RuntimeError('Rollback conflict; later changes preserved; review '+str(record)) from error
        raise
    report='install-fixture-result.json' if allow_fixture else 'installed-result.json'
    (R/report).write_text(json.dumps(dict(status='FIXTURE_INSTALLED' if allow_fixture else 'INSTALLED',backup=str(backup),preflight=result,protected=protected),ensure_ascii=False,indent=2),encoding='utf8')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--server',default=r'D:\FO3ID\server');p.add_argument('--client',default=r'D:\FO3ID\32795');p.add_argument('--fixture',action='store_true');args=p.parse_args()
    if args.fixture:
        assert Path(args.server).resolve().is_relative_to(R/'install-fixture') and Path(args.client).resolve().is_relative_to(R/'install-fixture')
    print(json.dumps(install(args.server,args.client,args.fixture),ensure_ascii=True))
