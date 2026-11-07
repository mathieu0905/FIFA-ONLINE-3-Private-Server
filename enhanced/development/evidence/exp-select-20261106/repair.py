from pathlib import Path
import datetime, hashlib, importlib.util, json, os, subprocess

S=Path('D:/FO3ID/server'); C=Path('D:/FO3ID/32795'); O=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(o): return json.dumps(o,ensure_ascii=False,indent=2).encode('utf-8')
def loadmod(p):
    spec=importlib.util.spec_from_file_location('gate_'+p.stem,p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def no_game():
    r=subprocess.run(['powershell','-NoProfile','-Command',"if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 1}"],capture_output=True)
    if r.returncode: raise RuntimeError('Game running; do not replace loaded resources')

no_game()
parent=loadmod(S/'patches/player_database_preflight.py')
before_gate=parent.preflight(S,C)
composition=parent.compose_manifest(S,C)
backup=S/'backups'/('exp-selection-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir()
target=C/'data/ui/TeamManagementExpCapsuleScreen.big'
source=S/'backups/xp30-batch-module-20261106-145705-239491/6.backup'
assert sha(target)=='1f39daf0895e1ac9de84f49873b9b91f12580093eda09be9c8143ab7516430c5'
assert sha(source)=='8b72154883406f94b68d5411ab7e9e5e9fa467676c7f4e34c55e2296090b93d8'
helper='patches/exp_selection_preflight.py'; manifest='patches/exp-selection-installed.json'; receipt='patches/exp-selection-receipt.json'
code=(S/'patches/player_database_preflight.py').read_text('utf-8')
code=code.replace('player-database-installed.json','exp-selection-installed.json').replace('player-database-receipt.json','exp-selection-receipt.json').replace('player_database_preflight.py','exp_selection_preflight.py').replace('INSTALLED_PLAYER_DATABASE','INSTALLED_EXP_SELECTION').replace('PLAYER_DATABASE_PREFLIGHT_PASS','EXP_SELECTION_PREFLIGHT_PASS')
code=code.replace("('server','gamedata/fifadb.sqlite'),('client','data/data_0.big')","('client','data/ui/teammanagementexpcapsulescreen.big'),('server','experience_levels.py')")
# Parent guards use canonical lowercase paths. Match without changing source case.
code=code.replace("r['relative'].replace('\\\\','/').casefold()", "r['relative'].replace('\\\\','/').casefold()")
play=S/'play-local.bat'; play_before=play.read_bytes()
needle=b'patches\\player_database_preflight.py'; assert play_before.count(needle)==1
play_after=play_before.replace(needle,b'patches\\exp_selection_preflight.py')
payloads={target:source.read_bytes(),S/helper:code.encode(),play:play_after}
guards=composition['guards']
for path,data in payloads.items():
    root,relative=('client',path.relative_to(C).as_posix()) if path.is_relative_to(C) else ('server',path.relative_to(S).as_posix())
    matching=[r for r in guards if r['root']==root and r['relative'].casefold()==relative.casefold()]
    assert len(matching)<=1
    if matching: matching[0]['sha256']=hashlib.sha256(data).hexdigest()
    else: guards.append(dict(root=root,relative=relative,sha256=hashlib.sha256(data).hexdigest()))
m=dict(schema=1,revision=backup.name,client=str(C),guards=guards,composition=composition,state_shop_replaced=False,repair='Restore original native EXP selection page; level30 Module/backend retained',native_status='PENDING',source=str(source))
payloads[S/manifest]=dump(m)
payloads[S/receipt]=dump(dict(status='INSTALLED_EXP_SELECTION',manifest_sha256=hashlib.sha256(payloads[S/manifest]).hexdigest(),revision=m['revision'],state_shop_replaced=False,backup=str(backup)))
baselines={str(p):sha(p) if p.exists() else None for p in payloads}
assets={n:sha(S/'gamedata'/n) for n in ('state.json','shop.json')}
for n in assets: (backup/n).write_bytes((S/'gamedata'/n).read_bytes())
for i,p in enumerate(payloads):
    if p.exists(): (backup/f'{i}.backup').write_bytes(p.read_bytes())
record=dict(before_gate=before_gate,baselines=baselines,asset_hashes_before=assets,files=[str(p) for p in payloads],backup=str(backup),state_shop_replaced=False)
(backup/'transaction.json').write_bytes(dump(record))
# Recheck full current parent immediately before applying; no historical package overwrite.
parent.preflight(S,C); no_game()
completed=[]
try:
    for i,(p,data) in enumerate(payloads.items()):
        assert (sha(p) if p.exists() else None)==baselines[str(p)],f'Concurrent change: {p}'
        tmp=p.with_name(p.name+'.exp-selection.tmp'); tmp.write_bytes(data); os.replace(tmp,p); completed.append((i,p))
    result=loadmod(S/helper).preflight(S,C)
except BaseException:
    for i,p in reversed(completed):
        if baselines[str(p)] is None: p.unlink()
        else: p.write_bytes((backup/f'{i}.backup').read_bytes())
    raise
record.update(status='INSTALLED',preflight=result,asset_hashes_after={n:sha(S/'gamedata'/n) for n in assets})
record['assets_byte_equal']=record['asset_hashes_after']==assets
(backup/'transaction.json').write_bytes(dump(record)); (O/'repair-result.json').write_bytes(dump(record))
print(json.dumps(dict(status=record['status'],preflight=result,backup=str(backup),assets_byte_equal=record['assets_byte_equal']),indent=2))
