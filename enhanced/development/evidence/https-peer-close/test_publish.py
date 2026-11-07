from pathlib import Path
import importlib.util,tempfile,types,copy,json
O=Path(__file__).parent;spec=importlib.util.spec_from_file_location('tls_publish',O/'install_fix.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);c=m.core;realS=c.S;tests=[]
with tempfile.TemporaryDirectory(prefix='fo3-http-publish-') as tmp:
    r=Path(tmp);c.S=r/'server';c.C=r/'client';c.O=r/'reports'
    for p in (c.S/'patches',c.S/'gamedata',c.S/'backups',c.C/'data/ui',c.O):p.mkdir(parents=True,exist_ok=True)
    for rel in ('http_config.py','patches/player_capacity_preflight.py'):(c.S/rel).write_bytes((realS/rel).read_bytes())
    (c.S/'experience_levels.py').write_text('synthetic')
    (c.S/'patches/fixture_preflight.py').write_text('synthetic')
    (c.S/'play-local.bat').write_bytes(b'.venv\\Scripts\\python.exe patches\\fixture_preflight.py\r\n')
    (c.C/'data/ui/teammanagementexpcapsulescreen.big').write_bytes(b'synthetic')
    for n in ('state.json','shop.json'):(c.S/'gamedata'/n).write_bytes(b'{"synthetic":true}')
    before={p:p.read_bytes() for p in r.rglob('*') if p.is_file()}
    guards=[dict(root='server',relative=p.relative_to(c.S).as_posix(),sha256=c.sha(p)) for p in before if p.is_relative_to(c.S) and 'gamedata' not in p.parts]+[dict(root='client',relative='data/ui/teammanagementexpcapsulescreen.big',sha256=c.sha(c.C/'data/ui/teammanagementexpcapsulescreen.big'))]
    def check(*args):
        for row in guards:assert c.sha((c.S if row['root']=='server' else c.C)/row['relative'])==row['sha256']
        return {'status':'FIXTURE_PARENT_PASS'}
    parent=types.SimpleNamespace(preflight=check,compose_manifest=lambda *args:dict(guards=copy.deepcopy(guards),ancestry=[],receipt_policies=[]))
    loader=c.module;c.module=lambda p:parent if p.name=='fixture_preflight.py' else loader(p)
    lock=c.S/'.shop-release.lock';lock.write_text('other owner')
    try:c.apply();raise AssertionError('lock conflict must reject')
    except FileExistsError:pass
    assert lock.read_text()=='other owner';lock.unlink();tests.append('existing publisher lock preserved')
    replace=c.os.replace
    def fail(a,b):
        if Path(b)==c.S/c.HELPER:raise OSError('injected switch failure')
        return replace(a,b)
    c.os.replace=fail
    try:c.apply();raise AssertionError('failure injection did not fail')
    except OSError:pass
    finally:c.os.replace=replace
    assert all(p.read_bytes()==v for p,v in before.items());tests.append('partial write rolls back exact original HTTP and leaves assets intact')
    result=c.apply();assert result['preflight']['status']=='HTTP_DISCONNECT_PREFLIGHT_PASS';assert result['asset_hashes_before']==result['asset_hashes_after'];tests.append('complete exact publisher succeeds with physical guard and unchanged asset bytes')
    after={p:p.read_bytes() for p in r.rglob('*') if p.is_file()};assert c.apply()['status']=='ALREADY_INSTALLED_NO_WRITES';assert all(p.read_bytes()==v for p,v in after.items());tests.append('second apply verifies and performs zero payload writes')
    (c.S/'http_config.py').write_bytes(b'tamper')
    try:loader(c.S/c.HELPER).preflight(c.S,c.C);raise AssertionError('tampered source accepted')
    except RuntimeError:pass
    tests.append('installed source tampering is rejected')
(O/'publisher-tests.json').write_text(json.dumps(dict(status='HTTP_DISCONNECT_PUBLISHER_IO_PASS',checks=tests,production_writes=False),indent=2),'utf8');print(json.dumps(tests,indent=2))
