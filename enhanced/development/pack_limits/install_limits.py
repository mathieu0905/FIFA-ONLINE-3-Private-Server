"""Install a four-target quota child release; history and player saves remain untouched."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,os
ROOT=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def atomic(p,data):
    p=Path(p);tmp=p.with_name(p.name+'.quota-next')
    if tmp.exists():raise RuntimeError('Stale quota stage file')
    tmp.write_bytes(data);os.replace(tmp,p)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
test=read(ROOT/'test-results.json');assert test['status']=='PASS' and test['count']>=28
for n,digest in test['tested_files'].items():assert sha(ROOT/n)==digest,'Quota payload changed after test'
module=load(ROOT/'pack_limits_preflight.py','quota_candidate')
manifest_path=S/module.MANIFEST;receipt_path=S/module.RECEIPT
if receipt_path.exists():
    result=module.preflight(S,C);print(json.dumps(dict(status='ALREADY_INSTALLED',check=result['status'])));raise SystemExit(0)
assert not manifest_path.exists(),'Unregistered quota manifest'
changes=read(ROOT/'changes.json')
for n,row in changes.items():
    target=S/n if n=='play-local.bat' else S/'gamedata'/n
    assert sha(target)==row['before_sha256'],'Concurrent parent edit: '+n
parent=load(S/'patches/xp30_batch_preflight.py','quota_parent')
parent.preflight(S,C)
assert not (S/'patches/pack_limits_preflight.py').exists(),'Unregistered quota helper'
if not args.apply:print(json.dumps(dict(status='DRY_RUN_PASS',writes=6)));raise SystemExit(0)
lock=S/'.shop-release.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
backup=S/'backups'/('pack-limits-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
payload=[(ROOT/'pack_cadence.json',S/'gamedata/pack_cadence.json','gamedata/pack_cadence.json'),
         (ROOT/'pack_catalogue.json',S/'gamedata/pack_catalogue.json','gamedata/pack_catalogue.json'),
         (ROOT/'pack_limits_preflight.py',S/'patches/pack_limits_preflight.py','patches/pack_limits_preflight.py'),
         (ROOT/'play-local.bat',S/'play-local.bat','play-local.bat')]
manifest=dict(schema=1,release_id='20261106-pack-limits-expanded-v1',client_root=str(C),backup=str(backup),
    parents={n:sha(S/n) for n in ('patches/xp30_batch_preflight.py','patches/xp30-batch-release-manifest.json')},
    draw_rules_changed=False,state_replaced=False,limits={n:read(ROOT/n)['limits'] for n in ('pack_cadence.json','pack_catalogue.json')},
    test_sha256=sha(ROOT/'test-results.json'),files=[dict(root='server',relative=rel,sha256=sha(src),parent_sha256=sha(dst) if dst.exists() else None) for src,dst,rel in payload])
saved=[];protected={n:sha(S/'gamedata'/n) for n in ('state.json','shop.json')}
try:
    for src,dst,rel in payload:
        raw=dst.read_bytes() if dst.exists() else None
        if raw is not None:
            old=backup/(dst.name if dst.name in ('pack_cadence.json','pack_catalogue.json') else rel)
            old.parent.mkdir(parents=True,exist_ok=True);old.write_bytes(raw)
    for src,dst,rel in payload[:-1]:
        raw=dst.read_bytes() if dst.exists() else None;atomic(dst,src.read_bytes());saved.append((dst,raw))
    atomic(manifest_path,json.dumps(manifest,ensure_ascii=False,indent=2).encode());saved.append((manifest_path,None))
    receipt=dict(status='INSTALLED',release_id=manifest['release_id'],manifest_sha256=sha(manifest_path),backup=str(backup),state_written=False)
    atomic(receipt_path,json.dumps(receipt,ensure_ascii=False,indent=2).encode());saved.append((receipt_path,None))
    src,dst,_=payload[-1];raw=dst.read_bytes();atomic(dst,src.read_bytes());saved.append((dst,raw))
    result=module.preflight(S,C)
    assert all(sha(S/'gamedata'/n)==digest for n,digest in protected.items()),'Concurrent player asset change during install'
except BaseException:
    for target,raw in reversed(saved):
        if raw is None:target.unlink(missing_ok=True)
        else:atomic(target,raw)
    raise
finally:lock.unlink(missing_ok=True)
(ROOT/'installation.json').write_text(json.dumps(dict(receipt=receipt,preflight=result),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='INSTALLED',backup=str(backup),preflight=result['status']),ensure_ascii=True))
