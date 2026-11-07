"""Temporary I/O tests of the exact installer; no production mutation or service launch."""
from pathlib import Path
import importlib.util,tempfile,shutil,json,sys,types,copy
O=Path(__file__).parent;SCRIPT=O/'install_batch.py';source=SCRIPT.read_text('utf8');main=source.split("if __name__=='__main__':",1)[1]
def load():
    spec=importlib.util.spec_from_file_location('batch_installer',SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
passed=[]
with tempfile.TemporaryDirectory(prefix='fo3-batch-io-') as tmp:
    root=Path(tmp);m=load();realS=m.S;realC=m.C;m.S=root/'server';m.C=root/'client';m.S.mkdir();m.C.mkdir();(m.S/'patches').mkdir();(m.S/'gamedata').mkdir();(m.S/'backups').mkdir();(m.C/'data/ui').mkdir(parents=True)
    m.O=root/'workspace';(m.O/'batch-bound-v1').mkdir(parents=True)
    shutil.copyfile(O/'batch-bound-v1/TeamManagementExpCapsuleScreen.big',m.O/'batch-bound-v1/TeamManagementExpCapsuleScreen.big')
    for rel in ('gamedata/state.json','gamedata/shop.json'):(m.S/rel).write_text('{"synthetic":"never production"}')
    (m.S/'experience_levels.py').write_bytes((realS/'experience_levels.py').read_bytes())
    (m.S/'patches/exp_selection_preflight.py').write_bytes((realS/'patches/exp_selection_preflight.py').read_bytes())
    (m.S/'patches/fixture_preflight.py').write_text('fixture gate placeholder')
    (m.S/'play-local.bat').write_bytes(b'.venv\\Scripts\\python.exe patches\\fixture_preflight.py\r\n')
    page=m.C/'data/ui/TeamManagementExpCapsuleScreen.big';page.write_bytes((realS/'backups/xp30-batch-module-20261106-145705-239491/6.backup').read_bytes())
    expected=[dict(root='server',relative=rel,sha256=m.sha(m.S/rel)) for rel in ('experience_levels.py','patches/exp_selection_preflight.py','patches/fixture_preflight.py','play-local.bat')]+[dict(root='client',relative='data/ui/teammanagementexpcapsulescreen.big',sha256=m.sha(page))]
    # Actual disk filesystem is case sensitive on some test hosts, preserve native spelling.
    expected[-1]['relative']='data/ui/TeamManagementExpCapsuleScreen.big'
    def parent_check(*args):
        for r in expected:assert m.sha((m.S if r['root']=='server' else m.C)/r['relative'])==r['sha256']
        return dict(status='FIXTURE_PARENT_PASS',files=len(expected))
    parent=types.SimpleNamespace(preflight=parent_check,compose_manifest=lambda *args:dict(guards=copy.deepcopy(expected),receipt_policies=[],ancestry=[]))
    origmodule=m.module;m.module=lambda p:parent if p.name=='fixture_preflight.py' else origmodule(p)
    baseline={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    def run():
        argv=sys.argv;sys.argv=[str(SCRIPT),'--apply']
        try:exec(compile('if True:'+main,'<exact installer main>','exec'),m.__dict__)
        finally:sys.argv=argv
    m.game_closed=lambda:(_ for _ in ()).throw(RuntimeError('fixture game running'))
    try:run();raise AssertionError('should reject running game')
    except RuntimeError as e:assert 'game running' in str(e)
    assert all(Path(p).read_bytes()==b for p,b in baseline.items()) and not (m.S/'.shop-release.lock').exists()
    passed.append('running game rejects before lock, backup or payload write')
    m.game_closed=lambda:None
    lock=m.S/'.shop-release.lock';lock.write_text('other publisher')
    try:run();raise AssertionError('should reject existing publisher')
    except FileExistsError:pass
    assert lock.read_text()=='other publisher' and all(Path(p).read_bytes()==b for p,b in baseline.items())
    lock.unlink();passed.append('shared release lock conflict preserves other publisher lock and all files')
    replace=m.os.replace
    def fail_second(src,dst):
        if Path(dst)==m.S/m.HELPER:raise OSError('injected second switch failure')
        return replace(src,dst)
    m.os.replace=fail_second
    try:run();raise AssertionError('should fail')
    except OSError as e:assert 'injected' in str(e)
    finally:m.os.replace=replace
    assert all(Path(p).read_bytes()==b for p,b in baseline.items()) and not (m.S/m.HELPER).exists()
    passed.append('second file switch failure restores original page and leaves all assets unchanged')
    run();assert m.sha(page)==m.EXPECTED_PAGE
    gate=origmodule(m.S/m.HELPER);r=gate.preflight(m.S,m.C);assert r['status']=='EXP_BATCH_PREFLIGHT_PASS'
    passed.append('complete real file transaction and installed physical preflight pass')
    after={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    try:run()
    except SystemExit as e:assert not e.code
    assert all(Path(p).read_bytes()==b for p,b in after.items())
    passed.append('second install verifies existing page and performs zero writes')
    for rel in ('gamedata/state.json','gamedata/shop.json'):assert (m.S/rel).read_bytes()==baseline[str(m.S/rel)]
    passed.append('state and shop fixture bytes untouched throughout all transactions')
    old=page.read_bytes();page.write_bytes(old+b'corrupt')
    try:gate.preflight(m.S,m.C);raise AssertionError('must reject tampered page')
    except RuntimeError:pass
    page.write_bytes(old);passed.append('physical gate rejects tampered resource')
result=dict(status='TEMPORARY_INSTALLER_IO_PASS',checks=passed,production_writes=False)
(O/'batch-install-tests.json').write_text(json.dumps(result,indent=2),'utf8');print(json.dumps(result,indent=2))
