"""Real temporary-file transaction regression; never controls live services."""
from pathlib import Path
import hashlib, json, tempfile
from unittest.mock import patch
import install as target

def main():
    cases=[]
    with tempfile.TemporaryDirectory(prefix='fo3-team-bonus-tx-') as temp:
        root=Path(temp)
        with patch.object(target,'S',root):
            # Both locks are real exclusive files, acquired in the production order.
            for occupied in ('.shop-release.lock','.fo3-publish.lock'):
                lock=root/occupied; lock.write_bytes(b'other-owner')
                try:
                    with target.locks(): raise AssertionError('Lock conflict ignored')
                except FileExistsError: pass
                assert lock.read_bytes()==b'other-owner'
                assert sorted(p.name for p in root.iterdir())==[occupied]
                lock.unlink(); cases.append('Preserve occupied '+occupied)
            with target.locks():
                assert (root/'.shop-release.lock').exists() and (root/'.fo3-publish.lock').exists()
            assert not list(root.iterdir()); cases.append('Owned locks released')
            f=root/'cas';f.write_bytes(b'newer-owner')
            try: target.cas(f,b'old',b'ours');raise AssertionError('Stale baseline accepted')
            except RuntimeError: pass
            assert f.read_bytes()==b'newer-owner'; f.unlink();cases.append('CAS preserves concurrent later write')
            with patch.object(target,'closed',side_effect=RuntimeError('game active')),patch.object(target,'locks',side_effect=AssertionError('Locks entered before idle check')):
                try:target.main();raise AssertionError('Running game accepted')
                except RuntimeError as exc: assert str(exc)=='game active'
            assert not list(root.iterdir()); cases.append('Active game rejected before locks or writes')
            with patch.object(target,'closed'),patch.object(target,'run',side_effect=RuntimeError('protected stop refused')):
                try:target.stop();raise AssertionError('Refused stop accepted')
                except RuntimeError as exc:assert str(exc)=='protected stop refused'
            cases.append('Protected stop rejection propagates')
        for failure in (None,1,2,3,4):
            fixture=root/str(failure);fixture.mkdir()
            (fixture/'gamedata').mkdir();(fixture/'parent').write_bytes(b'parent')
            snapshot={'state.json':b'{"real":"latest"}','shop.json':b'{"stock":3}'}
            for name,body in snapshot.items():(fixture/'gamedata'/name).write_bytes(body)
            payloads={'http_config.py':b'after-http','doc':b'after-doc','new-gate.py':b'def preflight(s,c): return {"status":"PASS"}\n','play-local.bat':b'after-play'}
            before={'http_config.py':b'live-http','doc':b'live-doc','new-gate.py':None,'play-local.bat':b'live-play'}
            for rel,body in before.items():
                if body is not None:(fixture/rel).write_bytes(body)
            p=dict(payloads=payloads,before=before,parent='parent',parent_hash=target.sha(fixture/'parent'),revision='test',gate='new-gate.py',manifest='unused',receipt='unused')
            original_cas=target.cas; counter=[0]
            def failing_cas(*args):
                counter[0]+=1
                if counter[0]==failure:raise RuntimeError('Injected replace failure')
                return original_cas(*args)
            with patch.object(target,'S',fixture),patch.object(target,'closed'),patch.object(target,'run',return_value='PASS'),patch.object(target,'cas',side_effect=failing_cas):
                if failure:
                    try:target.apply(p,snapshot);raise AssertionError('Injected failure ignored')
                    except RuntimeError as exc:assert str(exc)=='Injected replace failure'
                    for rel,body in before.items():assert ((fixture/rel).read_bytes() if (fixture/rel).exists() else None)==body
                else:
                    result=target.apply(p,snapshot);assert result['status']=='INSTALLED'
                    for rel,body in payloads.items():assert (fixture/rel).read_bytes()==body
            for name,body in snapshot.items():assert (fixture/'gamedata'/name).read_bytes()==body
            cases.append('Successful file transaction and assets preserved' if failure is None else 'Rollback after replacement failure '+str(failure))
    report=dict(status='PASS',case_count=len(cases),cases=cases,installer_sha256=hashlib.sha256((target.R/'install.py').read_bytes()).hexdigest(),
                powershell='Game presence check uses Windows PowerShell 5.1; temporary file transactions use production Python CAS; no PowerShell file transactions',live_services_touched=False)
    (target.R/'transaction-tests.json').write_bytes(target.encoded(report)); print(json.dumps(report))
if __name__=='__main__':main()
