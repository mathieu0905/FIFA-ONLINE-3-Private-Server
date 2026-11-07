"""Remove the 200-card policy cap using the maximum signed-32 client wire capacity.

Only one existing business line changes; every market/pack/claim/admin cap shares it.
No live save is written, no client resource is touched, no process is started/stopped.
"""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,re,subprocess,sys
sys.dont_write_bytecode=True
S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');O=Path(__file__).parent
HELPER='patches/player_capacity_preflight.py';MANIFEST='patches/player-capacity-installed.json';RECEIPT='patches/player-capacity-receipt.json'
LIMIT=2_147_483_647
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(x):return json.dumps(x,ensure_ascii=False,indent=2).encode('utf8')
def module(p):
    spec=importlib.util.spec_from_file_location('capacity_'+p.stem,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def closed():
    r=subprocess.run(['powershell','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 1}'],capture_output=True)
    if r.returncode:raise RuntimeError('Game active. Coordinate the necessary server reload; never force exit.')
def plan():
    raw=(S/'play-local.bat').read_bytes();matches=list(re.finditer(rb'(?m)^\.venv\\Scripts\\python\.exe (patches\\[a-zA-Z0-9_]+_preflight\.py)\r?$',raw));assert len(matches)==1
    old=matches[0].group(1).decode().replace('\\','/');parent=module(S/old);verified=parent.preflight(S,C)
    if old==HELPER:return parent,{},{},None
    composition=parent.compose_manifest(S,C)
    if isinstance(composition,tuple):composition=composition[0]
    source=(S/'http_config.py').read_bytes()
    needle=b'MAX_PLAYERS = 200  # coach.limits.players (squad size; user: "max skuad naikan", was 60)'
    assert source.count(needle)==1,'Capacity implementation changed; inspect and rebase'
    updated=source.replace(needle,b'MAX_PLAYERS = 2_147_483_647  # No 200-card policy cap; signed-32 client-compatible capacity sentinel.')
    compile(updated,str(S/'http_config.py'),'exec')
    code=(S/'patches/exp_batch_preflight.py').read_text('utf8')
    code=code.replace('exp-batch-installed.json','player-capacity-installed.json').replace('exp-batch-receipt.json','player-capacity-receipt.json').replace('exp_batch_preflight.py','player_capacity_preflight.py').replace('INSTALLED_EXP_BATCH','INSTALLED_PLAYER_CAPACITY').replace('EXP_BATCH_PREFLIGHT_PASS','PLAYER_CAPACITY_PREFLIGHT_PASS')
    code=code.replace("('server','experience_levels.py')","('server','experience_levels.py'),('server','http_config.py')")
    compile(code,str(S/HELPER),'exec')
    payloads={S/'http_config.py':updated,S/HELPER:code.encode(),S/'play-local.bat':raw.replace(matches[0].group(1),HELPER.replace('/','\\').encode())}
    guards=composition['guards'];seen=set()
    for row in guards:
        k=(row['root'],row['relative'].replace('\\','/').casefold());assert k not in seen;seen.add(k)
    for p,data in payloads.items():
        rel=p.relative_to(S).as_posix();hits=[g for g in guards if g['root']=='server' and g['relative'].replace('\\','/').casefold()==rel.casefold()];assert len(hits)<=1
        if hits:hits[0]['sha256']=hashlib.sha256(data).hexdigest()
        else:guards.append(dict(root='server',relative=rel,sha256=hashlib.sha256(data).hexdigest()))
    rev='player-capacity-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=S/'backups'/rev
    m=dict(schema=1,revision=rev,client=str(C),guards=guards,composition=composition,parent=old,parent_verified=verified,state_shop_replaced=False,wire_capacity=LIMIT,previous_policy_capacity=200,native_status='PENDING',scope='Only MAX_PLAYERS constant; FIRST_TEAM_MAX inherits it. All known cap checks use the same constant; no save rewrite.')
    payloads[S/MANIFEST]=dump(m);payloads[S/RECEIPT]=dump(dict(status='INSTALLED_PLAYER_CAPACITY',revision=rev,manifest_sha256=hashlib.sha256(payloads[S/MANIFEST]).hexdigest(),state_shop_replaced=False,backup=str(backup)))
    return parent,payloads,{str(p):sha(p) if p.exists() else None for p in payloads},backup
def apply():
    closed();lock=S/'.shop-release.lock';token=dump(dict(pid=os.getpid(),release='player-capacity'))
    with lock.open('xb') as f:f.write(token)
    committed=[];temp=[]
    try:
        parent,payloads,base,backup=plan()
        if not payloads:return dict(status='ALREADY_INSTALLED_NO_WRITES',preflight=parent.preflight(S,C))
        parent.preflight(S,C);closed();backup.mkdir()
        data_before={n:(S/'gamedata'/n).read_bytes() for n in ('state.json','shop.json')}
        for n,data in data_before.items():(backup/n).write_bytes(data)
        indices={p:i for i,p in enumerate(payloads)}
        for p,i in indices.items():
            if p.exists():(backup/f'{i}.backup').write_bytes(p.read_bytes())
        tx=dict(status='APPLYING',files=base,asset_hashes_before={n:hashlib.sha256(v).hexdigest() for n,v in data_before.items()},backup=str(backup),state_shop_replaced=False)
        (backup/'transaction.json').write_bytes(dump(tx))
        for p in [p for p in payloads if p!=S/'play-local.bat']+[S/'play-local.bat']:
            assert (sha(p) if p.exists() else None)==base[str(p)],f'Concurrent target change: {p}'
            t=p.with_name(p.name+'.'+backup.name+'.tmp')
            with t.open('xb') as f:f.write(payloads[p])
            temp.append(t);os.replace(t,p);committed.append(p)
        result=module(S/HELPER).preflight(S,C)
        tx.update(status='INSTALLED_RELOAD_PENDING',preflight=result,asset_hashes_after={n:sha(S/'gamedata'/n) for n in data_before})
        (backup/'transaction.json').write_bytes(dump(tx));(O/'installation.json').write_bytes(dump(tx));return tx
    except BaseException:
        for t in temp:
            if t.exists():t.unlink()
        for p in reversed(committed):
            assert sha(p)==hashlib.sha256(payloads[p]).hexdigest(),'Later writer owns rollback path'
            if base[str(p)] is None:p.unlink()
            else:
                t=p.with_name(p.name+'.capacity-rollback.tmp');t.write_bytes((backup/f'{indices[p]}.backup').read_bytes());os.replace(t,p)
        raise
    finally:
        if lock.exists() and lock.read_bytes()==token:lock.unlink()
if __name__=='__main__':
    if '--apply' in sys.argv:result=apply()
    else:
        parent,payloads,base,backup=plan();result=dict(status='PLAN_ONLY_NO_WRITES',files=base,wire_capacity=LIMIT,parent=parent.__file__)
    print(json.dumps(result,ensure_ascii=True,indent=2))
