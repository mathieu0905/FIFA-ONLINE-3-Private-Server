from pathlib import Path
import copy,importlib.util,json,os,shutil,sys,types
sys.dont_write_bytecode=True
import install as installer
R=Path(__file__).resolve().parent
S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
p=installer.p;m=p.read(R/'manifest.json')
parent=p.parent(S,m);composed,v=parent._compose(S,C,parent.read(S/parent.MANIFEST))
fixture=R/'install-fixture-v4'
assert not fixture.exists(),'Use a fresh isolated install fixture'
roots={'server':fixture/'server','client':fixture/'client'}
for e in composed['guards']:
    source=(S if e['root']=='server' else C)/e['relative'];dest=roots[e['root']]/e['relative']
    dest.parent.mkdir(parents=True,exist_ok=True)
    if source.stat().st_size>10000000:os.link(source,dest)
    else:shutil.copyfile(source,dest)
for name in m['parent_files']:
    dest=roots['server']/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/name,dest)
for source in (S/'patches').iterdir():
    if source.is_file() and source.suffix in ('.py','.json'):
        shutil.copyfile(source,roots['server']/'patches'/source.name)
s,c=roots['server'],roots['client']
# Historical pack receipts bind backup paths to the real root. Use the exact
# already validated current parent projection in this relocated transaction
# fixture; do not rewrite or weaken any historical production metadata.
original_parent=p.parent
def fixture_parent(server,manifest):
    original_parent(server,manifest)  # exact parent source/receipt SHA checks
    return types.SimpleNamespace(MANIFEST=parent.MANIFEST,read=p.read,
        _compose=lambda *args:(copy.deepcopy(composed),v))
p.parent=fixture_parent
installer.preview(s,c)
baseline={str(x):p.sha(x) for x in fixture.rglob('*') if x.is_file()}
try:installer.install(s,c,True,fail_after=4)
except RuntimeError as e:assert 'Injected failure' in str(e)
else:raise AssertionError('Failure was not injected')
for name,digest in baseline.items():assert p.sha(Path(name))==digest,name
assert not (s/p.RECEIPT).exists()
v.verify_manifest(composed,s,c)
result=installer.install(s,c,True)
assert result['status']=='INSTALLED'
assert installer.install(s,c,True)['status']=='ALREADY_INSTALLED'
target=s/'admin.py';saved=target.read_bytes();target.write_bytes(saved+b'\n# private tamper\n')
try:p.preflight(s,c)
except RuntimeError as e:assert 'admin.py' in str(e)
else:raise AssertionError('Tampering was accepted')
target.write_bytes(saved)
bad=copy.deepcopy(m);bad['files'][0]['parent_sha256']='0'*64
try:p._compose(s,c,bad)
except RuntimeError as e:assert 'parent SHA mismatch' in str(e)
else:raise AssertionError('Bad ancestor accepted')
bad=copy.deepcopy(m);bad['files'].append(dict(root='server',relative='gamedata/state.json',sha256='0'*64,parent_sha256=None))
try:p._compose(s,c,bad)
except RuntimeError as e:assert 'whitelist' in str(e)
else:raise AssertionError('State replacement accepted')
report=dict(status='PASS',checks=['full_current_parent_projection','injected_switch_failure_restores_original_files',
       'full_child_preflight','idempotent_install','tamper_refused','wrong_parent_refused','state_replacement_refused'],
       files=result['preflight']['files'])
(R/'install-test-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
