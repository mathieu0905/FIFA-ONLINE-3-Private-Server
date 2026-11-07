from pathlib import Path
import tempfile,importlib.util,types,copy,json
O=Path(__file__).parent
spec=importlib.util.spec_from_file_location('capacity_install',O/'install_capacity.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
realS=m.S;passed=[]
with tempfile.TemporaryDirectory(prefix='fo3-capacity-io-') as tmp:
    r=Path(tmp);m.S=r/'server';m.C=r/'client';m.O=r/'evidence'
    for p in (m.S/'patches',m.S/'gamedata',m.S/'backups',m.C/'data/ui',m.O):p.mkdir(parents=True,exist_ok=True)
    (m.S/'http_config.py').write_bytes((realS/'http_config.py').read_bytes())
    (m.S/'patches/exp_batch_preflight.py').write_bytes((realS/'patches/exp_batch_preflight.py').read_bytes())
    (m.S/'play-local.bat').write_bytes(b'.venv\\Scripts\\python.exe patches\\fixture_preflight.py\r\n')
    (m.S/'patches/fixture_preflight.py').write_bytes(b'fixture placeholder')
    (m.S/'experience_levels.py').write_bytes(b'fixture placeholder')
    (m.C/'data/ui/teammanagementexpcapsulescreen.big').write_bytes(b'fixture placeholder')
    for name in ('state.json','shop.json'):(m.S/'gamedata'/name).write_text('{"synthetic":true}')
    baseline={p:p.read_bytes() for p in r.rglob('*') if p.is_file()}
    guards=[dict(root='server',relative=p.relative_to(m.S).as_posix(),sha256=m.sha(p)) for p in baseline if p.is_relative_to(m.S) and 'gamedata' not in p.parts]
    guards+=[dict(root='client',relative='data/ui/teammanagementexpcapsulescreen.big',sha256=m.sha(m.C/'data/ui/teammanagementexpcapsulescreen.big'))]
    def check(*args):
        for row in guards:assert m.sha((m.S if row['root']=='server' else m.C)/row['relative'])==row['sha256']
        return {'status':'FIXTURE_PARENT_PASS'}
    parent=types.SimpleNamespace(preflight=check,compose_manifest=lambda *args:dict(guards=copy.deepcopy(guards),receipt_policies=[],ancestry=[]))
    load=m.module;m.module=lambda p:parent if p.name=='fixture_preflight.py' else load(p)
    m.closed=lambda:(_ for _ in ()).throw(RuntimeError('game active'))
    try:m.apply();raise AssertionError()
    except RuntimeError as e:assert 'game active' in str(e)
    assert all(p.read_bytes()==v for p,v in baseline.items())
    passed.append('active game rejected before writes')
    m.closed=lambda:None;lock=m.S/'.shop-release.lock';lock.write_text('another task')
    try:m.apply();raise AssertionError()
    except FileExistsError:pass
    assert lock.read_text()=='another task';lock.unlink();passed.append('other writer lock preserved')
    replace=m.os.replace
    def fail(src,dst):
        if Path(dst)==m.S/m.HELPER:raise OSError('second switch')
        return replace(src,dst)
    m.os.replace=fail
    try:m.apply();raise AssertionError()
    except OSError:pass
    finally:m.os.replace=replace
    assert all(p.read_bytes()==v for p,v in baseline.items()) and not (m.S/m.HELPER).exists()
    passed.append('mid-transaction failure restores original HTTP without asset writes')
    result=m.apply();assert result['preflight']['status']=='PLAYER_CAPACITY_PREFLIGHT_PASS'
    assert b'MAX_PLAYERS = 2_147_483_647' in (m.S/'http_config.py').read_bytes()
    assert result['asset_hashes_before']==result['asset_hashes_after']
    passed.append('complete transaction; installed physical guards and asset-byte equality')
    after={p:p.read_bytes() for p in r.rglob('*') if p.is_file()};assert m.apply()['status']=='ALREADY_INSTALLED_NO_WRITES'
    assert all(p.read_bytes()==v for p,v in after.items());passed.append('duplicate install verifies and performs no payload writes')
(O/'install-tests.json').write_text(json.dumps(dict(status='TEMPORARY_CAPACITY_INSTALLER_PASS',checks=passed,production_writes=False),indent=2),'utf8')
print(json.dumps(passed,indent=2))
