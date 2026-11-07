from pathlib import Path
import hashlib,json,tempfile
from unittest.mock import patch
import install as app
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks=[]
with tempfile.TemporaryDirectory(prefix='transaction-',dir=W) as tmp:
    root=Path(tmp);formal=root/'formal';formal.mkdir()
    with patch.object(app,'S',formal),patch.object(app.subprocess,'check_output',return_value='"fifazf.exe","123"'):
        result=app.main();assert result['status']=='DEFERRED_GAME_RUNNING' and not list(formal.iterdir())
    checks.append('Active game exits before shared locks/backups/formal writes; installer has no service stop/restart path')
    with app.release.locks(formal,'owner'):
        try:
            with app.release.locks(formal,'other'):raise AssertionError('Lock bypass')
        except FileExistsError:pass
        assert (formal/'.shop-release.lock').exists()
    assert not list(formal.iterdir())
    checks.append('Common dual-lock order and foreign-owner lock retained')
    def entries(case):
        folder=root/case;folder.mkdir();rows=[]
        for i in range(9):
            p=folder/str(i);p.write_bytes(b'old')
            rows.append(dict(root='client' if i<2 else 'server',relative=str(i),target=p,before=sha(p),after=hashlib.sha256(b'new').hexdigest(),data=b'new'))
        return rows
    for fail in (1,8,None):
        rows=entries('switch-'+str(fail))
        try:app.commit(rows,root/('backup-'+str(fail)),lambda:None,lambda:None,fail_after=fail)
        except OSError:assert fail
        else:assert fail is None
        for row in rows:assert row['target'].read_bytes()==(b'old' if fail else b'new')
    checks.append('Nine-file success and early/late failure restore only owned exact versions')
    rows=entries('later-edit')
    def verify():
        rows[0]['target'].write_bytes(b'later-owner');raise ValueError('Postcheck failed')
    try:app.commit(rows,root/'backup-later',verify,lambda:None)
    except ValueError:pass
    else:raise AssertionError('Expected validation failure')
    assert rows[0]['target'].read_bytes()==b'later-owner'
    assert all(row['target'].read_bytes()==b'old' for row in rows[1:])
    checks.append('Rollback retains a subsequent owner edit and restores the remaining owned files')
    rows=entries('mid-game');calls=[]
    def guard():
        calls.append(1)
        if len(calls)==2:raise RuntimeError('Game reopened')
    try:app.commit(rows,root/'backup-midgame',lambda:None,guard)
    except RuntimeError:pass
    else:raise AssertionError('Must stop publication when game reopens')
    assert all(row['target'].read_bytes()==b'old' for row in rows)
    checks.append('Game reopening during commit halts further switches and rolls back the partial owned transaction')
result=dict(status='PASS',checks=checks,formal_writes=False)
(W/'install-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
