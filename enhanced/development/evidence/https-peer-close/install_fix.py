"""Use the validated atomic five-file publisher for a server-only disconnect boundary.
No process is started/stopped by this publisher. Reload timing is coordinated separately.
"""
from pathlib import Path
import importlib.util,re,hashlib,json,sys,datetime,ast
sys.dont_write_bytecode=True
O=Path(__file__).parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
spec=importlib.util.spec_from_file_location('atomic_capacity_publisher',O.parent/'player-capacity/install_capacity.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
core.S=S;core.C=C;core.O=O
core.HELPER='patches/http_disconnect_preflight.py';core.MANIFEST='patches/http-disconnect-installed.json';core.RECEIPT='patches/http-disconnect-receipt.json'
def plan():
    raw=(core.S/'play-local.bat').read_bytes();hits=list(re.finditer(rb'(?m)^\.venv\\Scripts\\python\.exe (patches\\[a-zA-Z0-9_]+_preflight\.py)\r?$',raw));assert len(hits)==1
    parent_name=hits[0].group(1).decode().replace('\\','/');parent=core.module(core.S/parent_name);verified=parent.preflight(core.S,core.C)
    if parent_name==core.HELPER:return parent,{},{},None
    composed=parent.compose_manifest(core.S,core.C)
    if isinstance(composed,tuple):composed=composed[0]
    binding=json.loads((O/'source-binding.json').read_text('utf8'))
    assert core.sha(core.S/'http_config.py')==binding['source_sha256'],'Current HTTP changed; rebuild and rerun TLS tests'
    updated=(O/'http_config.fixed.py').read_bytes();compile(updated,'http_config.py','exec')
    oldtree=ast.parse((core.S/'http_config.py').read_text('utf-8-sig'));newtree=ast.parse(updated.decode('utf-8-sig'))
    h=next(n for n in newtree.body if isinstance(n,ast.ClassDef) and n.name=='H');h.body=[n for n in h.body if not isinstance(n,ast.FunctionDef) or n.name!='handle']
    assert ast.dump(oldtree)==ast.dump(newtree),'Only H.handle may change'
    code=(core.S/'patches/player_capacity_preflight.py').read_text('utf8')
    code=code.replace('player-capacity-installed.json','http-disconnect-installed.json').replace('player-capacity-receipt.json','http-disconnect-receipt.json').replace('player_capacity_preflight.py','http_disconnect_preflight.py').replace('INSTALLED_PLAYER_CAPACITY','INSTALLED_HTTP_DISCONNECT').replace('PLAYER_CAPACITY_PREFLIGHT_PASS','HTTP_DISCONNECT_PREFLIGHT_PASS')
    compile(code,core.HELPER,'exec')
    payloads={core.S/'http_config.py':updated,core.S/core.HELPER:code.encode(),core.S/'play-local.bat':raw.replace(hits[0].group(1),core.HELPER.replace('/','\\').encode())}
    seen=set();guards=composed['guards']
    for row in guards:
        key=(row['root'],row['relative'].replace('\\','/').casefold());assert key not in seen;seen.add(key)
    for p,data in payloads.items():
        rel=p.relative_to(core.S).as_posix();rows=[r for r in guards if r['root']=='server' and r['relative'].replace('\\','/').casefold()==rel.casefold()];assert len(rows)<=1
        digest=hashlib.sha256(data).hexdigest()
        if rows:rows[0]['sha256']=digest
        else:guards.append(dict(root='server',relative=rel,sha256=digest))
    revision='http-disconnect-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup=core.S/'backups'/revision
    m=dict(schema=1,revision=revision,client=str(core.C),guards=guards,composition=composed,parent=parent_name,parent_verified=verified,state_shop_replaced=False,native_status='PENDING',scope='H.handle catches known peer disconnect exceptions only; no response retries or business mutation changes')
    payloads[core.S/core.MANIFEST]=core.dump(m);payloads[core.S/core.RECEIPT]=core.dump(dict(status='INSTALLED_HTTP_DISCONNECT',manifest_sha256=hashlib.sha256(payloads[core.S/core.MANIFEST]).hexdigest(),revision=revision,state_shop_replaced=False,backup=str(backup)))
    return parent,payloads,{str(p):core.sha(p) if p.exists() else None for p in payloads},backup
core.plan=plan
original_dump=core.dump
def release_dump(value):
    if isinstance(value,dict) and value.get('release')=='player-capacity':value={**value,'release':'http-disconnect'}
    return original_dump(value)
core.dump=release_dump
# This change edits only server source/metadata. A running client is safe until reload,
# which this installer never performs. The shared lock and fresh-parent checks remain.
core.closed=lambda:None
if __name__=='__main__':
    if '--apply' in sys.argv:print(json.dumps(core.apply(),indent=2))
    else:
        p,files,base,b=plan();print(json.dumps(dict(status='PLAN_ONLY_NO_WRITES',parent=p.__file__,files=base),indent=2))
