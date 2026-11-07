from pathlib import Path
import tempfile,sys,json,os
from unittest.mock import patch
sys.path.insert(0,r'D:\fifaol3');import install_bulk_seasons as tx
sys.path.insert(0,str(Path(__file__).parent));import install
checks=[]
with tempfile.TemporaryDirectory(prefix='protection40-install-') as f:
 root=Path(f);roots={'server':root/'server','client':root/'client'}
 for r in roots.values():r.mkdir()
 source=root/'payload';source.mkdir()
 for failure in (1,10,None):
  entries=[]
  for n in range(11):
   r='client' if n in (2,3) else 'server';dest=roots[r]/('file'+str(n));dest.write_bytes(b'old'+str(n).encode())
   src=source/str(n);src.write_bytes(b'new'+str(n).encode())
   entries.append(dict(root=r,relative=dest.name,source=str(src),parent_sha256=tx.sha(dest),sha256=tx.sha(src)))
  backup=root/('backup'+str(failure));backup.mkdir()
  try:result=tx.commit_transaction(roots,entries,backup,lambda:None,fail_after=failure)
  except OSError:assert failure is not None
  else:assert failure is None
  for row in entries:
   assert tx.sha(tx.target(roots,row))==row['parent_sha256' if failure else 'sha256']
 checks.append('Early and late atomic switch failures restore only owned files; complete eleven-file transaction succeeds')
 try:
  with install.locks(roots['server']):
   assert (roots['server']/'.shop-release.lock').exists()
   try:
    with install.locks(roots['server']):raise AssertionError('lock bypass')
   except FileExistsError:pass
   assert (roots['server']/'.shop-release.lock').exists()
 finally:assert not list(roots['server'].glob('*.lock'))
 (roots['server']/'.fo3-publish.lock').write_bytes(b'other-owner')
 try:
  with install.locks(roots['server']):raise AssertionError('lock bypass')
 except FileExistsError:pass
 assert not (roots['server']/'.shop-release.lock').exists() and (roots['server']/'.fo3-publish.lock').read_bytes()==b'other-owner'
 checks.append('Two common locks serialize publishers and never remove another owner lock')
 for bad in ['state.json','shop.json','state.json.bak1','../outside',r'C:\\outside']:
  try:tx.target(roots,dict(root='server',relative=bad))
  except AssertionError:pass
  else:raise AssertionError(bad)
 checks.append('Asset replacement and escaping paths rejected')
 with patch.object(install.subprocess,'check_output',return_value='"fifazf.exe","123"'):
  try:install.gameclosed()
  except RuntimeError:pass
  else:raise AssertionError('running client must block installation')
 checks.append('Running-game boundary rejects installation without killing client')
result=dict(status='PASS',checks=checks)
Path(__file__).with_name('install-tests.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
