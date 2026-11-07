"""Install the batch page as a child of the actual current release; game must be closed.

Run without --apply to inspect a fresh plan. It never writes state/shop or starts services.
"""
from pathlib import Path
import sys,hashlib,json,importlib.util,re,subprocess,datetime,os
sys.dont_write_bytecode=True
S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');O=Path(__file__).parent
EXPECTED_PAGE='2555f22d92b0e7b0bcc29da37be1e1082271bdcad7d38dda6ba290e29fd0644c'
HELPER='patches/exp_batch_preflight.py';MANIFEST='patches/exp-batch-installed.json';RECEIPT='patches/exp-batch-receipt.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(x):return json.dumps(x,ensure_ascii=False,indent=2).encode('utf8')
def module(path):
    spec=importlib.util.spec_from_file_location('batch_gate_'+path.stem,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def game_closed():
    r=subprocess.run(['powershell','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 1}'],capture_output=True)
    if r.returncode:raise RuntimeError('Game is running. Do not install loaded UI resources or close the user game.')
def plan():
    play=S/'play-local.bat';raw=play.read_bytes()
    matches=list(re.finditer(rb'(?m)^\.venv\\Scripts\\python\.exe (patches\\[a-zA-Z0-9_]+_preflight\.py)\r?$',raw))
    assert len(matches)==1,'Unrecognized launcher; review its current entry before installation'
    old=matches[0].group(1).decode().replace('\\','/');parent=module(S/old)
    verified=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
    if old==HELPER:
        assert sha(C/'data/ui/TeamManagementExpCapsuleScreen.big')==EXPECTED_PAGE
        return parent,{},{},None
    if isinstance(composition,tuple):composition=composition[0]
    page=C/'data/ui/TeamManagementExpCapsuleScreen.big';payload=O/'batch-bound-v1'/page.name
    assert sha(page)=='8b72154883406f94b68d5411ab7e9e5e9fa467676c7f4e34c55e2296090b93d8','Current EXP page changed; rebase, never overwrite it'
    assert sha(payload)==EXPECTED_PAGE
    code=(S/'patches/exp_selection_preflight.py').read_text('utf8')
    code=code.replace('exp-selection-installed.json','exp-batch-installed.json').replace('exp-selection-receipt.json','exp-batch-receipt.json').replace('exp_selection_preflight.py','exp_batch_preflight.py').replace('INSTALLED_EXP_SELECTION','INSTALLED_EXP_BATCH').replace('EXP_SELECTION_PREFLIGHT_PASS','EXP_BATCH_PREFLIGHT_PASS')
    compile(code,str(S/HELPER),'exec')
    files={page:payload.read_bytes(),S/HELPER:code.encode(),play:raw.replace(matches[0].group(1),HELPER.replace('/','\\').encode())}
    guards=composition['guards'];seen=set()
    for g in guards:
        k=(g['root'],g['relative'].replace('\\','/').casefold());assert k not in seen;seen.add(k)
    for p,data in files.items():
        root,rel=('client',p.relative_to(C).as_posix()) if p.is_relative_to(C) else ('server',p.relative_to(S).as_posix())
        hits=[g for g in guards if g['root']==root and g['relative'].replace('\\','/').casefold()==rel.casefold()]
        h=hashlib.sha256(data).hexdigest()
        if hits:hits[0]['sha256']=h
        else:guards.append(dict(root=root,relative=rel,sha256=h))
    revision='exp-batch-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=S/'backups'/revision
    m=dict(schema=1,revision=revision,client=str(C),guards=guards,composition=composition,state_shop_replaced=False,parent=old,parent_verified=verified,native_status='PENDING_REAL_CLIENT_VERIFICATION',batch_scope='minus, plus, typed quantity, maximum, unified preview, expected snapshot, authoritative after/count')
    files[S/MANIFEST]=dump(m)
    files[S/RECEIPT]=dump(dict(status='INSTALLED_EXP_BATCH',manifest_sha256=hashlib.sha256(files[S/MANIFEST]).hexdigest(),revision=revision,state_shop_replaced=False,backup=str(backup)))
    base={str(p):sha(p) if p.exists() else None for p in files}
    return parent,files,base,backup

if __name__=='__main__':
    parent,files,base,backup=plan()
    if not files:
        print(json.dumps(dict(status='ALREADY_INSTALLED_NO_WRITES',preflight=parent.preflight(S,C)),indent=2));sys.exit()
    if '--apply' not in sys.argv:
        print(json.dumps(dict(status='PLAN_ONLY_NO_PRODUCTION_WRITES',files=list(base),before=base,after={str(p):hashlib.sha256(data).hexdigest() for p,data in files.items()}),indent=2));sys.exit()
    # Game-closed is required before creating even the release backup/lock.
    game_closed();lock=S/'.shop-release.lock'
    lock_payload=json.dumps(dict(pid=os.getpid(),release=backup.name))
    with lock.open('x') as f:f.write(lock_payload)
    done=[];temporary=[]
    try:
        parent.preflight(S,C);game_closed();backup.mkdir()
        for i,p in enumerate(files):
            if p.exists():(backup/f'{i}.backup').write_bytes(p.read_bytes())
        before={n:sha(S/'gamedata'/n) for n in ('state.json','shop.json')}
        tx=dict(before=base,files=list(base),asset_hashes_before=before,state_shop_replaced=False,status='INSTALLING')
        (backup/'transaction.json').write_bytes(dump(tx))
        # Select the new launcher only after its resource, helper and metadata exist.
        order=[p for p in files if p!=S/'play-local.bat']+[S/'play-local.bat']
        for p in order:
            i=list(files).index(p);data=files[p]
            assert (sha(p) if p.exists() else None)==base[str(p)],f'Concurrent modification: {p}'
            tmp=p.with_name(p.name+'.'+backup.name+'.tmp')
            with tmp.open('xb') as f:f.write(data)
            temporary.append((tmp,hashlib.sha256(data).hexdigest()))
            os.replace(tmp,p);done.append((i,p))
        result=module(S/HELPER).preflight(S,C)
        tx.update(status='INSTALLED',preflight=result,asset_hashes_after={n:sha(S/'gamedata'/n) for n in before})
        (backup/'transaction.json').write_bytes(dump(tx));(O/'batch-install-result.json').write_bytes(dump(tx))
        print(json.dumps(dict(status='INSTALLED',preflight=result,backup=str(backup)),indent=2))
    except BaseException:
        for tmp,digest in temporary:
            if tmp.exists() and sha(tmp)==digest:tmp.unlink()
        # Restore only payloads this transaction still owns, never a later writer's bytes.
        for i,p in reversed(done):
            assert sha(p)==hashlib.sha256(files[p]).hexdigest(),f'Concurrent writer owns rollback path: {p}'
            if base[str(p)] is None:p.unlink()
            else:
                tmp=p.with_name(p.name+'.exp-batch-rollback.tmp');tmp.write_bytes((backup/f'{i}.backup').read_bytes());os.replace(tmp,p)
        raise
    finally:
        if lock.exists() and lock.read_text()==lock_payload:lock.unlink()
