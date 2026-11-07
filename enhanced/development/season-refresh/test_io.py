"""Exercise the exact transaction core over temporary same-layout paths."""
from pathlib import Path
import json,sys,tempfile
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));import deploy
d=deploy.d;folder=Path(tempfile.mkdtemp(prefix='io-',dir=R));roots=dict(server=folder/'server',client=folder/'client')
for p in roots.values():p.mkdir()
entries=[]
for n,(root,rel) in enumerate(sorted(d.TARGETS)):
    target=roots[root]/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(('old'+str(n)).encode())
    source=folder/('payload'+str(n));source.write_bytes(('new'+str(n)).encode())
    entries.append(dict(root=root,relative=rel,source=str(source),parent_sha256=d.tx.sha(target),sha256=d.tx.sha(source)))
checks=[]
for fail in (1,2,len(entries)):
    backup=folder/('failure'+str(fail));backup.mkdir()
    try:d.tx.commit_transaction(roots,[dict(r) for r in entries],backup,lambda:None,fail_after=fail)
    except OSError as e:assert 'Injected' in str(e)
    else:raise AssertionError('Missing injected failure')
    assert all(d.tx.sha(d.tx.target(roots,r))==r['parent_sha256'] for r in entries)
    checks.append('Atomic rollback after '+str(fail)+' writes')
backup=folder/'success';backup.mkdir();tx=d.tx.commit_transaction(roots,[dict(r) for r in entries],backup,lambda:None)
assert all(d.tx.sha(d.tx.target(roots,r))==r['sha256'] for r in entries)
d.tx.restore_completed(roots,tx,backup);assert all(d.tx.sha(d.tx.target(roots,r))==r['parent_sha256'] for r in entries)
checks.append('Successful write then inverse rollback')
with d.locks(roots['server']):
    assert (roots['server']/'.shop-release.lock').exists() and (roots['server']/'.fo3-publish.lock').exists()
assert not (roots['server']/'.shop-release.lock').exists()
checks.append('Common lock ordering and cleanup')
d.write(R/'io-tests.json',dict(status='PASS',checks=checks,production_written=False));print(json.dumps(dict(status='PASS',checks=checks)))
