"""Sparse hard-linked file fixtures exercise real guarded transactions, no services."""
from pathlib import Path
import json,os,shutil,sys,tempfile
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));import deploy as d
root=R/'install-tests';root.mkdir(exist_ok=True);run=Path(tempfile.mkdtemp(prefix='run-',dir=root))
m=d.read(d.OUT/'manifest.json');digest=d.tx.sha(d.OUT/'manifest.json');results=[]
def fixture(label):
    s=run/label/'server';c=run/label/'client';s.mkdir(parents=True);c.mkdir()
    rows=m['guards']+m['composition'].get('receipt_policies',[])
    for row in rows:
        source=(d.S if row['root']=='server' else d.C)/row['relative'];target=(s if row['root']=='server' else c)/row['relative']
        if not source.exists() or target.exists():continue
        target.parent.mkdir(parents=True,exist_ok=True);os.link(source,target)
    for name in ('state.json','shop.json'):
        target=s/'gamedata'/name;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copyfile(d.S/'gamedata'/name,target)
    return s,c
for label,fail in [('rollback1',1),('rollback5',5),('rollback7',7),('success',None)]:
    s,c=fixture(label);before={n:d.tx.sha(s/'gamedata'/n) for n in ('state.json','shop.json')}
    if fail:
        try:d.install(s,c,digest,fixture=True,fail_after=fail)
        except OSError as e:assert 'Injected' in str(e)
        else:raise AssertionError('Fault not raised')
        for row in m['files']:assert d.tx.digest(d.tx.target(dict(server=s,client=c),row))==row['parent_sha256']
        assert not (s/d.MANIFEST).exists() and not (s/d.RECEIPT).exists()
    else:
        out=d.install(s,c,digest,fixture=True);assert out['status']=='INSTALLED_SHOP_VALUE_NATIVE_PENDING'
        assert d.install(s,c,digest,fixture=True)['status']=='SHOP_VALUE_PREFLIGHT_PASS'
        p=s/'product_packs.py';tmp=p.with_name(p.name+'.tamper-test');tmp.write_bytes(b'tampered');os.replace(tmp,p)
        try:d.load(s/d.SELF,'tampered_fixture_guard').preflight(s,c)
        except RuntimeError:pass
        else:raise AssertionError('Tampered source accepted')
    assert before=={n:d.tx.sha(s/'gamedata'/n) for n in before}
    assert not (s/'.shop-release.lock').exists() and not (s/'.fo3-publish.lock').exists()
    results.append(dict(case=label,status='PASS'))
s,c=fixture('stale');p=s/m['parent_preflight'];tmp=p.with_name(p.name+'.test');tmp.write_bytes(b'drift');os.replace(tmp,p)
try:d.preview(dict(server=s,client=c))
except AssertionError:pass
else:raise AssertionError('Stale parent accepted')
results.append(dict(case='stale-parent-rejected',status='PASS'))
s,c=fixture('outer-lock')
with d.locks(s):
    assert d.install(s,c,digest,fixture=True)['status']=='INSTALLED_SHOP_VALUE_NATIVE_PENDING'
    assert (s/'.shop-release.lock').exists() and (s/'.fo3-publish.lock').exists()
assert not (s/'.shop-release.lock').exists() and not (s/'.fo3-publish.lock').exists()
results.append(dict(case='cutover-keeps-both-outer-locks-through-install',status='PASS'))
try:d.stopped()
except RuntimeError:results.append(dict(case='live-managed-service-blocked',status='PASS'))
else:raise AssertionError('Service guard did not detect current formal services')
report=dict(status='PASS',cases=results,temporary_files=str(run),no_service_actions=True,production_written=False)
d.write(R/'install-tests.json',report);print(json.dumps(report))
