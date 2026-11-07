"""Failure-injection transaction checks on disposable files, never formal data."""
from pathlib import Path
import hashlib,json,sys,tempfile
R=Path(__file__).resolve().parent;sys.path.insert(0,'D:/FO3ID/server')
from player_editor.publish_database import transaction
checks=[]
with tempfile.TemporaryDirectory(prefix='nostalgia-tx-',dir=R) as folder:
 root=Path(folder);payload=root/'payload';target=root/'target';payload.mkdir();target.mkdir()
 pairs=[];originals={}
 for i in range(194):
  a=payload/f'{i}.bin';b=target/f'{i}.bin';a.write_bytes(('new-'+str(i)).encode())
  if i%3:b.write_bytes(('old-'+str(i)).encode());originals[str(b)]=b.read_bytes()
  else:originals[str(b)]=None
  pairs.append((a,b))
 def unchanged():assert all((Path(n).read_bytes() if Path(n).exists() else None)==data for n,data in originals.items())
 # Late failure must restore both replaced resources and previously absent faces.
 try:transaction(pairs,root/'rollback',lambda:None,fail_after=191)
 except RuntimeError as e:assert 'Injected' in str(e)
 else:raise AssertionError('Late transaction failure was not raised')
 unchanged();checks.append('late failure restores old resources and removes only newly created targets')
 def reject():raise RuntimeError('Post-install composed gate rejected')
 try:transaction(pairs,root/'postcheck',reject)
 except RuntimeError as e:assert 'composed gate' in str(e)
 else:raise AssertionError('Postcheck failure was not raised')
 unchanged();checks.append('post-install gate failure rolls back all 194 targets')
 transaction(pairs,root/'success',lambda:all(b.read_bytes()==a.read_bytes() for a,b in pairs))
 assert all(b.read_bytes()==a.read_bytes() for a,b in pairs);checks.append('complete transaction installs every exact payload')
 report=dict(status='PASS',targets=len(pairs),checks=checks,synthetic_only=True,production_written=False)
 (R/'transaction-result.json').write_text(json.dumps(report,indent=2),'utf-8');print(json.dumps(report,indent=2))
