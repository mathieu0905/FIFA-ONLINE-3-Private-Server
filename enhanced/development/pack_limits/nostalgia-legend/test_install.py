from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,sys
from unittest.mock import patch
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
def audit(event,args):
    if event=='open':
        name,mode,flags=args
        if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(name)).resolve().is_relative_to(R):raise PermissionError('Fixture cannot write outside its workspace')
sys.addaudithook(audit)
import install as installer
v=installer.load(R/'nostalgia_legend_preflight.py','fixture_validator')
m=json.loads((R/'nostalgia-legend-release-manifest.json').read_text(encoding='utf8'))
S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
parent=installer.load(S/m['parent_preflight'],'fixture_parent')
c,base=v.project_parent(parent,S,C,json.loads((S/m['parent_manifest']).read_text(encoding='utf-8-sig')))
F=R/'install-fixture'/datetime.datetime.now().strftime('%H%M%S-%f');roots={'server':F/'server','client':F/'client'}
assert not F.exists(),'Use a fresh, explicitly named fixture directory'
def link(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    if not destination.exists():
        if source.suffix.lower() in ('.py','.json','.html','.bat','.ps1'):shutil.copyfile(source,destination)
        else:os.link(source,destination)
for row in c['guards']:
    source={'server':S,'client':C}[row['root']]/row['relative']
    if installer.sha(source)!=row['sha256']:
        # Reconstruct the immutable parent for this offline I/O test if another
        # authorized publisher has advanced a mutable working file meanwhile.
        matches=[p/row['root']/row['relative'] for p in (R/'backups').iterdir()]
        source=next(p for p in matches if p.is_file() and installer.sha(p)==row['sha256'])
    link(source,roots[row['root']]/row['relative'])
for source in (S/'patches').rglob('*'):
    if source.is_file() and source.suffix in ('.py','.json'):link(source,roots['server']/source.relative_to(S))
for name in ('gamedata/state.json','gamedata/shop.json'):
    link(S/name,roots['server']/name)
for row in m['files']:
    source={'server':S,'client':C}[row['root']]/row['relative']
    if source.exists():link(source,roots[row['root']]/row['relative'])
receipt=json.loads((S/'patches/pack-catalogue-release-installed.json').read_text(encoding='utf-8-sig'))
backup=Path(receipt['backup'])
for source in backup.rglob('*'):
    if source.is_file():link(source,roots['server']/source.relative_to(S))
# An ancestor receipt deliberately pins an absolute backup path. Relocate only
# that path inside this fixture; the receipt and all frozen bytes remain exact.
original_resolve=Path.resolve
def relocated(path,*args,**kwargs):
    value=original_resolve(path,*args,**kwargs)
    return roots['server']/value.relative_to(S) if value.is_relative_to(S/'backups') else value
before={path.relative_to(F).as_posix():installer.sha(path) for path in F.rglob('*') if path.is_file()}
fault_samples=[]
with patch.object(Path,'resolve',relocated):
    for lock_name,other in (('.shop-release.lock','.fo3-publish.lock'),('.fo3-publish.lock','.shop-release.lock')):
        lock=roots['server']/lock_name;lock.write_bytes(b'other publisher')
        try:installer.install(roots['server'],roots['client'],True)
        except RuntimeError as error:assert 'Another publisher' in str(error)
        else:raise AssertionError('Common lock must block')
        assert lock.read_bytes()==b'other publisher' and not (roots['server']/other).exists()
        lock.unlink()
    fault_samples.append('Common shop and fo3 conflicts preserve foreign locks and release own partial acquisition')
    first=roots['server']/m['files'][0]['relative'];old_first=first.read_bytes();original_atomic=installer.atomic
    newer=b'legitimate edit immediately before elite write'
    def drift_before(path,data,**kwargs):
        if path==first:first.write_bytes(newer)
        return original_atomic(path,data,**kwargs)
    with patch.object(installer,'atomic',side_effect=drift_before):
        try:installer.install(roots['server'],roots['client'],True)
        except RuntimeError as error:assert 'Target drift immediately before write' in str(error)
        else:raise AssertionError('Immediate target drift was overwritten')
    assert first.read_bytes()==newer
    original_atomic(first,old_first,expected=installer.sha(first))
    fault_samples.append('Each target commit rechecks expected hash and preserves a just-arrived legitimate edit')
    second=roots['server']/m['files'][1]['relative'];newer=b'legitimate edit after elite first write'
    def drift_on_rollback(path,data,**kwargs):
        if path==second:
            first.write_bytes(newer);raise RuntimeError('injected second target failure')
        return original_atomic(path,data,**kwargs)
    with patch.object(installer,'atomic',side_effect=drift_on_rollback):
        try:installer.install(roots['server'],roots['client'],True)
        except RuntimeError as error:assert 'Rollback conflict; later changes preserved' in str(error)
        else:raise AssertionError('Rollback overwrote a newer writer')
    assert first.read_bytes()==newer and installer.sha(second)==m['files'][1]['parent_sha256']
    journals=sorted((R/'backups').glob('*/transaction.json'),key=lambda p:p.stat().st_mtime_ns)
    journal=json.loads(journals[-1].read_text())
    assert journal['status']=='ROLLBACK_CONFLICT_LATER_CHANGES_PRESERVED' and journal['conflicts'][0]['current']==installer.sha(first)
    assert not (roots['server']/'.shop-release.lock').exists() and not (roots['server']/'.fo3-publish.lock').exists()
    original_atomic(first,old_first,expected=installer.sha(first))
    fault_samples.append('Rollback refuses to overwrite later changes, releases both locks and retains review journal')
with patch.object(Path,'resolve',relocated):
    try:installer.install(roots['server'],roots['client'],True,fail_after=3)
    except RuntimeError as error:assert str(error)=='Injected rollback test'
    else:raise AssertionError('Rollback injection did not fire')
after={path.relative_to(F).as_posix():installer.sha(path) for path in F.rglob('*') if path.is_file()}
assert before==after,'Rollback did not restore complete fixture identity'
with patch.object(Path,'resolve',relocated):
    result=installer.install(roots['server'],roots['client'],True)
    again=installer.install(roots['server'],roots['client'],True)
assert result['files_verified'] and again['files_verified']
assert all(installer.sha(roots['server']/name)==before['server/'+name] for name in ('gamedata/state.json','gamedata/shop.json'))
(R/'install-test-results.json').write_text(json.dumps(dict(status='PASS',rollback=True,idempotent=True,concurrency_fault_samples=fault_samples,installer_sha256=installer.sha(R/'install.py'),formal_write_audit='NO_WRITES_OUTSIDE_ISOLATED_WORKSPACE',protected_fixture_state_shop_unchanged=True,physical=result),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PASS',guards=result.get('files'),rollback=True,idempotent=True)))
