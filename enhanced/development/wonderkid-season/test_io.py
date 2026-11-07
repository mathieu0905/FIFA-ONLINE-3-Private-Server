"""Exercise exact shared transaction switching and rollback; temporary files only."""
from pathlib import Path
import importlib.util,json,sys,tempfile
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,'D:/fifaol3');import install_bulk_seasons as tx
cases=[]
for fail in (1,2,4,None):
    T=Path(tempfile.mkdtemp(prefix='io-',dir=R));roots={'server':T/'server','client':T/'client'}
    for p in roots.values():p.mkdir()
    entries=[]
    for i,(root,rel) in enumerate([('server','gamedata/fifadb.sqlite'),('client','data/data_0.big'),('server','gamedata/npc-market-prices.sqlite'),('server','patches/new-gate.py')]):
        dest=roots[root]/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if i<3:dest.write_bytes(('before'+str(i)).encode())
        src=T/f'payload{i}';src.write_bytes(('after'+str(i)).encode())
        entries.append(dict(root=root,relative=rel,source=str(src),parent_sha256=tx.digest(dest),sha256=tx.sha(src)))
    backup=T/'backup';backup.mkdir()
    try:result=tx.commit_transaction(roots,entries,backup,lambda:None,fail_after=fail)
    except OSError:
        assert fail is not None
        assert all(tx.digest(tx.target(roots,r))==r['parent_sha256'] for r in entries)
    else:
        assert fail is None
        assert all(tx.sha(tx.target(roots,r))==r['sha256'] for r in entries)
        tx.restore_completed(roots,result,backup)
        assert all(tx.digest(tx.target(roots,r))==r['parent_sha256'] for r in entries)
    cases.append(dict(fail_after=fail,rollback_exact=True))
(R/'io-tests.json').write_text(json.dumps(dict(status='PASS',cases=cases,production_written=False),indent=2),'utf-8');print('IO_PASS')
