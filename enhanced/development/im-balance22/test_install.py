"""Exercise the IM transaction with actual temporary server/client files only."""
from pathlib import Path
import json,tempfile,types
from unittest.mock import patch
import install as target

def main():
    cases=[]
    with tempfile.TemporaryDirectory(prefix='im-balance-tx-') as temp:
        root=Path(temp)
        for failure in (None,*range(1,10)):
            folder=root/str(failure);server=folder/'server';client=folder/'client';server.mkdir(parents=True);client.mkdir()
            (server/'gamedata').mkdir();(server/'parent.py').write_bytes(b'parent')
            snapshot={'state.json':b'{"asset":"fresh-progress"}','shop.json':b'{"owned":12}'}
            for name,body in snapshot.items():(server/'gamedata'/name).write_bytes(body)
            cert={'status':'PLAYER_IMPORT_FULL_PASS'}
            payloads={server/'gamedata/fifadb.sqlite':b'newdb',server/'gamedata/custom_rosters.json':b'newregistry',client/'data_0.big':b'newbig',
                      server/'gamedata/player-import-validation.json':json.dumps(cert).encode(),server/'doc':b'newdoc',
                      server/'gate.py':b'newgate',server/'manifest.json':b'newmanifest',server/'receipt.json':b'newreceipt',server/'play-local.bat':b'newplay'}
            before={p:(None if p.name in ('gate.py','manifest.json','receipt.json') else b'latest-'+p.name.encode()) for p in payloads}
            for p,body in before.items():
                if body is not None:p.write_bytes(body)
            p=dict(payloads=payloads,before=before,parent='parent.py',parent_hash=target.sha(server/'parent.py'),revision='test',gate='gate.py',manifest='manifest.json',receipt='receipt.json')
            count=[0];cas=target.tx.cas
            def fail_cas(*args):
                count[0]+=1
                if count[0]==failure:raise RuntimeError('Injected commit failure')
                return cas(*args)
            def fake_load(path,name):
                if path.name=='check.py':return types.SimpleNamespace(validate=lambda *a,**kw:cert)
                return types.SimpleNamespace(preflight=lambda *a:{'status':'PASS'})
            with patch.object(target,'S',server),patch.object(target,'C',client),patch.object(target.tx,'closed'),patch.object(target.tx,'run',return_value='PASS'),patch.object(target.tx,'cas',side_effect=fail_cas),patch.object(target,'load',side_effect=fake_load):
                if failure:
                    try:target.apply(p,snapshot);raise AssertionError('Commit failure ignored')
                    except RuntimeError as exc:assert str(exc)=='Injected commit failure'
                    for path,body in before.items():assert (path.read_bytes() if path.exists() else None)==body
                else:
                    assert target.apply(p,snapshot)['status']=='INSTALLED'
                    for path,body in payloads.items():assert path.read_bytes()==body
            for name,body in snapshot.items():assert (server/'gamedata'/name).read_bytes()==body
            cases.append('Success with unchanged latest assets' if failure is None else 'Rollback preserves latest server/client/metadata/assets at step '+str(failure))
        lockroot=root/'locks';lockroot.mkdir()
        with patch.object(target,'S',lockroot):
            for name in ('.shop-release.lock','.fo3-publish.lock'):
                path=lockroot/name;path.write_bytes(b'other-owner')
                try:
                    with target.locks():raise AssertionError('Conflict ignored')
                except FileExistsError:pass
                assert path.read_bytes()==b'other-owner'
                assert len(list(lockroot.iterdir()))==1;path.unlink();cases.append('Preserved occupied '+name)
        with patch.object(target.tx,'closed',side_effect=RuntimeError('game active')),patch.object(target,'locks',side_effect=AssertionError('Lock before idle gate')):
            try:target.main();raise AssertionError('Active game ignored')
            except RuntimeError as exc:assert str(exc)=='game active'
        cases.append('Game running rejected before any formal activity')
    result=dict(status='PASS',case_count=len(cases),cases=cases,installer_sha256=target.sha(target.R/'install.py'),
                utilities_sha256=target.sha(Path(r'D:\fifaol3\team-bonus20\install.py')),live_services_touched=False)
    target.save(target.R/'transaction-tests.json',result);print(json.dumps(result))
if __name__=='__main__':main()
