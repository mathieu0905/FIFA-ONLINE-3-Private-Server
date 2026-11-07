from pathlib import Path
import tempfile,sys,json
from unittest.mock import patch
W=Path(__file__).resolve().parent;sys.path[:0]=[str(W),r'D:\fifaol3'];import install;import install_bulk_seasons as tx
checks=[]
with tempfile.TemporaryDirectory(prefix='installer-',dir=W) as t:
 root=Path(t);server=root/'server';server.mkdir()
 with patch.object(install,'S',server),patch.object(install.subprocess,'check_output',return_value='"fifazf.exe","123"'):
  out=install.install();assert out['status']=='DEFERRED' and not list(server.iterdir())
 checks.append('Active game returns DEFERRED before locks/backups/any formal write; no stop/start code exists')
 with install.locks(server):
  try:
   with install.locks(server):raise AssertionError('lock bypass')
  except FileExistsError:pass
  assert (server/'.shop-release.lock').exists()
 assert not list(server.iterdir())
 checks.append('Common lock order and other-owner lock preserved')
 roots={'server':server,'client':root/'client'};roots['client'].mkdir();payload=root/'payload';payload.mkdir()
 for fail in (1,8,None):
  entries=[]
  for n in range(9):
   r='client' if n in (0,1) else 'server';p=roots[r]/str(n);p.write_bytes(b'old');s=payload/str(n);s.write_bytes(b'new');entries.append(dict(root=r,relative=str(n),source=str(s),parent_sha256=tx.sha(p),sha256=tx.sha(s)))
  backup=root/str(fail);backup.mkdir()
  try:tx.commit_transaction(roots,entries,backup,lambda:None,fail_after=fail)
  except OSError:assert fail is not None
  else:assert fail is None
  for e in entries:assert tx.sha(tx.target(roots,e))==e['parent_sha256' if fail else 'sha256']
 checks.append('Nine-file native transaction success and early/late failure rollback preserve exact owned versions')
r=dict(status='PASS',checks=checks);(W/'install-tests.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
