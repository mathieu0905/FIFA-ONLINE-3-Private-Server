from pathlib import Path
import hashlib,json,shutil,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');P=R/'sandbox/server'
assert not P.exists();P.mkdir(parents=True)
for f in [*S.glob('*.py'),*S.glob('*.json')]:shutil.copyfile(f,P/f.name)
for folder in ('gamedata','responses','admin','tools'):
    shutil.copytree(S/folder,P/folder,ignore=shutil.ignore_patterns('__pycache__','*.bak*','*.log','migration-backups','replays'))
shutil.copyfile(R/'pack_value.py',P/'pack_value.py')
baseline={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [S/'product_packs.py',S/'http_config.py',S/'gamedata/product_packs.json',S/'gamedata/product_chain_elite.json',S/'play-local.bat']}
(R/'baseline.json').write_text(json.dumps(baseline,indent=2),'utf-8')
print('Sandbox prepared from installed files; no service started.')
