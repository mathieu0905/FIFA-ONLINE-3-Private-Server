"""Atomic, hash-pinned code/assets installer. Never restores or writes state/shop."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.product-packs-tmp')
    with temporary.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)

def install(server,client,allow_fixture=False,fail_after=None):
    roots={'server':Path(server).resolve(),'client':Path(client).resolve()}
    m=json.loads((R/'product-packs-release-manifest.json').read_text(encoding='utf8'))
    v=load(R/'product_packs_preflight.py','product_install_validator')
    target_manifest=roots['server']/v.MANIFEST;target_receipt=roots['server']/v.RECEIPT
    if target_manifest.exists() or target_receipt.exists():
        assert target_manifest.read_bytes()==(R/'product-packs-release-manifest.json').read_bytes(),'Another product release is installed'
        return v.preflight(roots['server'],roots['client'])
    if not allow_fixture:
        query="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'fifazf.exe' -or ($_.CommandLine -like '*D:\\FO3ID\\server*' -and $_.CommandLine -match '(http_config|messenger)\\.py') } | Select-Object -ExpandProperty ProcessId"
        # Only install after the coordinating owner has stopped game and official services.
        output=subprocess.check_output(['powershell.exe','-NoProfile','-Command',query],text=True)
        if output.strip():raise RuntimeError('Game/official services still active; wait for coordinated stop: '+output.strip())
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
            atomic(destination,source.read_bytes());done.append((destination,old))
            if fail_after==index+1:raise RuntimeError('Injected rollback test')
        atomic(target_manifest,(R/'product-packs-release-manifest.json').read_bytes());done.append((target_manifest,None))
        receipt=dict(status='INSTALLED_INDEPENDENT_PRODUCT_PACKS',release_id=m['release_id'],manifest_sha256=sha(target_manifest),state_shop_replaced=False)
        atomic(target_receipt,json.dumps(receipt,indent=2).encode());done.append((target_receipt,None))
        result=v.preflight(roots['server'],roots['client'])
        for name,digest in protected.items():assert sha(roots['server']/name)==digest,'Live data changed during install'
    except BaseException:
        for destination,old in reversed(done):
            if old is None:destination.unlink()
            else:atomic(destination,old)
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
