"""Temp composition test specifically rejects losing the newer market seed policy."""
from pathlib import Path
import importlib.util,tempfile,types,copy,json
O=Path(__file__).parent
spec=importlib.util.spec_from_file_location('style_install',O/'install_native_style.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
realS=m.S;module=m.module
with tempfile.TemporaryDirectory(prefix='fo3-style-policy-') as tmp:
    root=Path(tmp);m.S=root/'server';m.C=root/'client';m.O=root/'workspace'
    for p in (m.S/'patches',m.S/'docs',m.S/'gamedata',m.C/'data/ui',m.O/'native-style-v6'):p.mkdir(parents=True)
    parent_name='patches/noninterrupt_preflight.py'
    (m.S/parent_name).write_bytes((realS/parent_name).read_bytes())
    (m.S/'patches/noninterrupt-receipt.json').write_text('{"status":"INSTALLED_NONINTERRUPT"}')
    (m.S/'play-local.bat').write_bytes(b'.venv\\Scripts\\python.exe patches\\noninterrupt_preflight.py\r\n')
    (m.S/'docs/工程经验与修改边界.txt').write_text('fixture')
    (m.O/'native-style-ledger.txt').write_text('fixture append')
    (m.C/'data/ui/TeamManagementExpCapsuleScreen.big').write_bytes((O/'loop-label-v5/TeamManagementExpCapsuleScreen.big').read_bytes())
    (m.O/'native-style-v6/TeamManagementExpCapsuleScreen.big').write_bytes((O/'native-style-v6/TeamManagementExpCapsuleScreen.big').read_bytes())
    for name in ('npc_exchange.py','market_simulation.py','gamedata/npc-market-seed.json.gz'):(m.S/name).write_text('fixture')
    (m.S/'market_price_store.py').write_text("def verify_seed(*args):\n raise RuntimeError('SEED_CHECK_RETAINED')\n")
    guards=[dict(root='server',relative=p.relative_to(m.S).as_posix(),sha256=m.sha(p)) for p in m.S.rglob('*') if p.is_file()]
    guards.append(dict(root='client',relative='data/ui/TeamManagementExpCapsuleScreen.big',sha256=m.sha(m.C/'data/ui/TeamManagementExpCapsuleScreen.big')))
    parent=types.SimpleNamespace(MANIFEST='patches/noninterrupt-installed.json',RECEIPT='patches/noninterrupt-receipt.json',SELF=parent_name,preflight=lambda *a:dict(status='NONINTERRUPT_PREFLIGHT_PASS'),compose_manifest=lambda *a:dict(guards=copy.deepcopy(guards),receipt_policies=[]))
    m.module=lambda p:parent if p==m.S/parent_name else module(p)
    _,files,_,_=m.plan()
    for p,data in files.items():p.write_bytes(data)
    try:module(m.S/m.HELPER).preflight(m.S,m.C);raise AssertionError('seed check was bypassed')
    except RuntimeError as e:assert str(e)=='SEED_CHECK_RETAINED',e
    assert 'verify_seed' in (m.S/m.HELPER).read_text('utf8')
    report=dict(status='PASS',checks=['latest parent full implementation retained','new child physical guards pass before seed validator','seed verifier is invoked and failure propagates'],production_files_written=False)
    (O/'native-style-v6/gate-policy-regression.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(report))
