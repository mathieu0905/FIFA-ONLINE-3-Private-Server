"""Exercise the real installer against filesystem-only fixtures; no private services."""
from pathlib import Path
import copy, json, os, sys, tempfile
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));import release_callback as rel
S,C=rel.S,rel.C
release=ROOT/'release-v1';manifest=rel.read(release/'manifest.json');digest=rel.tx.sha(release/'manifest.json')
run=Path(tempfile.mkdtemp(prefix='release-test-',dir=ROOT));results=[]
original_commit=rel.tx.commit_transaction
def fixture(label):
    base=run/label;s=base/'server';c=base/'client';s.mkdir(parents=True);c.mkdir();(s/'backups').mkdir()
    for row in manifest['guards']+manifest['composition'].get('receipt_policies',[]):
        origin=(S if row['root']=='server' else C)/row['relative']
        target=(s if row['root']=='server' else c)/row['relative']
        if not origin.exists() or target.exists():continue
        target.parent.mkdir(parents=True,exist_ok=True);os.link(origin,target)
    for name in ('state.json','shop.json'):
        target=s/'gamedata'/name;target.parent.mkdir(parents=True,exist_ok=True)
        # The installation never writes these links, including on rollback.
        if not target.exists():os.link(S/'gamedata'/name,target)
    return s,c
def check_assets(s,before):
    assert {n:rel.tx.sha(s/'gamedata'/n) for n in before}==before
def replace(p,data):
    stage=p.with_name(p.name+'.test');stage.write_bytes(data);os.replace(stage,p)
try:
    for label,fail in [('fail1',1),('fail3',3),('fail5',5),('success',None)]:
        s,c=fixture(label);rel.S,rel.C=s,c;rel.gameclosed=lambda:None
        before={n:rel.tx.sha(s/'gamedata'/n) for n in ('state.json','shop.json')}
        old={r['relative']:rel.tx.digest((s if r['root']=='server' else c)/r['relative']) for r in manifest['files']}
        if fail:
            def failure(roots,entries,backup,validate,fail_after=fail):
                return original_commit(roots,entries,backup,validate,fail_after=fail_after)
            rel.tx.commit_transaction=failure
            try:rel.apply(release,digest,'root-exclusive-gameclosed-no-restart')
            except OSError as exc:assert 'Injected' in str(exc)
            else:raise AssertionError('Fault was not raised')
            for r in manifest['files']:assert rel.tx.digest((s if r['root']=='server' else c)/r['relative'])==old[r['relative']]
            assert not (s/rel.MANIFEST).exists() and not (s/rel.RECEIPT).exists()
        else:
            rel.tx.commit_transaction=original_commit
            result=rel.apply(release,digest,'root-exclusive-gameclosed-no-restart');assert result['status']=='INSTALLED_SEASON_NAME_NATIVE_PENDING'
            assert rel.apply(release,digest,'root-exclusive-gameclosed-no-restart')['status']=='SEASON_NAME_PREFLIGHT_PASS'
            child=rel.load(s/rel.SELF,'fixture_child');composed=child.compose_manifest(s,c)
            assert len(composed['guards'])==len(manifest['guards'])+2
            path=c/'data/ui/libs/Module.big';replace(path,b'tampered')
            try:child.preflight(s,c)
            except RuntimeError:pass
            else:raise AssertionError('Tampered Module accepted')
        check_assets(s,before);results.append(dict(case=label,status='PASS'))
    rel.tx.commit_transaction=original_commit
    s,c=fixture('game-active');rel.S,rel.C=s,c
    def active():raise RuntimeError('simulated active game')
    rel.gameclosed=active
    try:rel.apply(release,digest,'root-exclusive-gameclosed-no-restart')
    except RuntimeError as exc:assert 'active game' in str(exc)
    else:raise AssertionError('Active game accepted')
    assert not (s/rel.RECEIPT).exists();results.append(dict(case='game-active-rejected-before-write',status='PASS'))
    # Fresh source mismatches fail before any transaction.
    s,c=fixture('stale-parent');replace(s/manifest['parent_preflight'],b'changed')
    try:rel.preview(release,dict(server=s,client=c))
    except AssertionError:pass
    else:raise AssertionError('Stale parent accepted')
    results.append(dict(case='stale-parent-rejected',status='PASS'))
finally:
    rel.S,rel.C=S,C;rel.tx.commit_transaction=original_commit
report=dict(status='RELEASE_FIXTURE_PASS',fixtures=str(run),cases=results,production_written=False,service_actions=False)
rel.write(ROOT/'release-tests.json',report);print(json.dumps(report))
