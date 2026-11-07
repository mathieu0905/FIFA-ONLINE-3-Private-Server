"""Transactional additive install. Default is dry-run; never restores state/shop."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parent
SERVER = Path(r'D:\FO3ID\server')
CLIENT = Path(r'D:\FO3ID\32795')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def atomic(path, raw):
    temp=path.with_name(path.name+'.pack-next')
    if temp.exists():raise RuntimeError('Stale installer staging file: '+str(temp))
    temp.write_bytes(raw)
    os.replace(temp,path)

parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
tested=read(ROOT/'test-results.json');assert tested['status']=='PASS' and tested['count']>=27
for name,digest in tested['tested_files'].items():assert sha(ROOT/name)==digest,'Candidate changed after test: '+name
guard_tests=read(ROOT/'preflight-tests.json')
assert guard_tests['status']=='PASS' and sha(ROOT/'pack_catalogue_preflight.py')==guard_tests['helper_sha256']
baseline=read(ROOT/'baseline.json');native=read(ROOT/'native/build-result.json')
assert sha(ROOT/'TeamManagementDraftPackScreen.big')==native['target_sha256'],'Native candidate changed after structural validation'
files=[(ROOT/'http_config.py',SERVER/'http_config.py','server','http_config.py'),
       (ROOT/'shop_season_names.py',SERVER/'shop_season_names.py','server','shop_season_names.py'),
       (ROOT/'pack_catalogue.py',SERVER/'pack_catalogue.py','server','pack_catalogue.py'),
       (ROOT/'pack_catalogue.json',SERVER/'gamedata/pack_catalogue.json','server','gamedata/pack_catalogue.json'),
       (ROOT/'pack_catalogue_preflight.py',SERVER/'patches/pack_catalogue_preflight.py','server','patches/pack_catalogue_preflight.py'),
       (ROOT/'TeamManagementDraftPackScreen.big',CLIENT/'data/ui/TeamManagementDraftPackScreen.big','client','data/ui/TeamManagementDraftPackScreen.big')]
if (SERVER/'patches/pack-catalogue-release-manifest.json').exists():
    assert all(target.exists() and sha(target)==sha(source) for source,target,_,_ in files),'Existing release differs; publish a new version'
    import pack_catalogue_preflight
    pack_catalogue_preflight.validate(SERVER,CLIENT)
    print(json.dumps({'status':'ALREADY_INSTALLED','writes':0}));raise SystemExit(0)
for name in ('http_config.py','shop_season_names.py'):assert sha(SERVER/name)==baseline[name],'Concurrent source edit: '+name
assert sha(CLIENT/'data/ui/TeamManagementDraftPackScreen.big')==native['source_sha256'],'Concurrent native edit'
manifest={'schema':1,'release_id':'20261106-season-choice-v1','parent_shop_manifest_sha256':sha(SERVER/'patches/shop-release-manifest.json'),
          'parent_roster_manifest_sha256':sha(SERVER/'patches/roster-release-manifest.json'),
          'state_shop_replaced':False,'test_report_sha256':sha(ROOT/'test-results.json'),'files':[
              {'root':root,'relative':rel,'sha256':sha(source),'parent_sha256':sha(target) if target.exists() else None}
              for source,target,root,rel in files]}
if not args.apply:
    print(json.dumps({'status':'DRY_RUN_PASS','files':len(files),'release_id':manifest['release_id']}));raise SystemExit(0)
backup=SERVER/'backups'/('pack-catalogue-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True)
protected=[SERVER/'gamedata/state.json',SERVER/'gamedata/shop.json',SERVER/'gamedata/pack_cadence.json']
protected_hashes={str(p):sha(p) for p in protected}
for p in protected:shutil.copyfile(p,backup/p.name)
changed=[]
try:
    for source,target,root,rel in files:
        raw=target.read_bytes() if target.exists() else None
        if raw is not None:
            saved=backup/root/rel;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(raw)
        atomic(target,source.read_bytes());changed.append((target,raw))
        assert sha(target)==sha(source)
    assert all(sha(p)==digest for p,digest in protected_hashes.items()),'Concurrent protected state change during install'
    target=SERVER/'patches/pack-catalogue-release-manifest.json'
    raw=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
    atomic(target,raw);changed.append((target,None))
    receipt={'status':'INSTALLED','release_id':manifest['release_id'],'manifest_sha256':sha(target),'backup':str(backup),
             'protocol_status':'PASS_27_CHECKS','native_status':'PENDING','state_shop_changed_by_installer':False}
    target=SERVER/'patches/pack-catalogue-release-installed.json'
    atomic(target,json.dumps(receipt,ensure_ascii=False,indent=2).encode());changed.append((target,None))
except BaseException:
    for target,raw in reversed(changed):
        if raw is None:target.unlink(missing_ok=True)
        else:atomic(target,raw)
    raise
(ROOT/'installation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
