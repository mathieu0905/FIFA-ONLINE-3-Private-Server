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
v=installer.load(R/'product_packs_preflight.py','fixture_validator')
m=json.loads((R/'product-packs-release-manifest.json').read_text(encoding='utf8'))
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
with patch.object(Path,'resolve',relocated):
    try:installer.install(roots['server'],roots['client'],True,fail_after=7)
    except RuntimeError as error:assert str(error)=='Injected rollback test'
    else:raise AssertionError('Rollback injection did not fire')
after={path.relative_to(F).as_posix():installer.sha(path) for path in F.rglob('*') if path.is_file()}
assert before==after,'Rollback did not restore complete fixture identity'
with patch.object(Path,'resolve',relocated):
    result=installer.install(roots['server'],roots['client'],True)
    again=installer.install(roots['server'],roots['client'],True)
assert result['files_verified'] and again['files_verified']
assert all(installer.sha(roots['server']/name)==before['server/'+name] for name in ('gamedata/state.json','gamedata/shop.json'))
(R/'install-test-results.json').write_text(json.dumps(dict(status='PASS',rollback=True,idempotent=True,formal_write_audit='NO_WRITES_OUTSIDE_ISOLATED_WORKSPACE',protected_fixture_state_shop_unchanged=True,physical=result),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PASS',guards=result.get('files'),rollback=True,idempotent=True)))
