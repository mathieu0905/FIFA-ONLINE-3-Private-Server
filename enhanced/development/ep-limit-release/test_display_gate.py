from pathlib import Path
import copy,importlib.util,json,os,shutil,sys,types
sys.dont_write_bytecode=True
O=Path(sys.argv[1]).resolve();S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
spec=importlib.util.spec_from_file_location('display_installer',O/'install.py');i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i)
p=i.p;m=p.read(O/'manifest.json');parent=p.parent(S,m);composed,v=parent._compose(S,C)
F=O/'gate-fixture';assert not F.exists()
roots={'server':F/'server','client':F/'client'}
for e in composed['guards']+composed.get('receipt_policies',[])+m['files']+[dict(root='server',relative=n) for n in m['parent_files']]:
    src=(S if e['root']=='server' else C)/e['relative'];dest=roots[e['root']]/e['relative']
    if not src.exists() or dest.exists():continue
    dest.parent.mkdir(parents=True,exist_ok=True)
    if src.stat().st_size>10000000:os.link(src,dest)
    else:shutil.copyfile(src,dest)
original_parent=p.parent
def fixture_parent(server,manifest):
    original_parent(server,manifest)
    return types.SimpleNamespace(_compose=lambda *args:(copy.deepcopy(composed),v))
p.parent=fixture_parent
s,c=roots['server'],roots['client'];i.preview(s,c)
baseline={str(f):p.sha(f) for f in F.rglob('*') if f.is_file()}
try:i.install(s,c,True,fail_after=3)
except RuntimeError as e:assert 'Injected failure' in str(e)
else:raise AssertionError('Injection did not happen')
for path,h in baseline.items():assert p.sha(Path(path))==h,path
result=i.install(s,c,True);assert result['status']=='INSTALLED'
assert i.install(s,c,True)['status']=='ALREADY_INSTALLED'
target=c/'data/ui/MenuScreen.big';saved=target.read_bytes();target.write_bytes(saved+b'\0')
try:p.preflight(s,c)
except RuntimeError as e:assert 'MenuScreen.big' in str(e)
else:raise AssertionError('Tamper accepted')
target.write_bytes(saved)
report=dict(status='PASS',full_current_parent_physical_dryrun=True,relocated_fixture_uses_frozen_checked_parent_projection=True,
    switch_failure_rollback=True,idempotent_install=True,screen_tamper_rejected=True,files=result['preflight']['files'])
(O/'gate-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
