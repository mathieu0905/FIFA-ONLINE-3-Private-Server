"""Exact, backed-up formal server update with inherited guards; no save replacement."""
from pathlib import Path
from contextlib import contextmanager, nullcontext
import argparse, datetime, importlib.util, json, os, re, shutil, subprocess, sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
OUT=R/'deployment-v4'
sys.path.insert(0,'D:/fifaol3');import install_bulk_seasons as tx
MANIFEST='patches/shop-value-installed.json';RECEIPT='patches/shop-value-receipt.json';SELF='patches/shop_value_preflight.py'
TARGETS={('server',x) for x in ('product_packs.py','pack_value.py','gamedata/shop_value_products.json','play-local.bat',SELF)}
_held_locks=set()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,d):tx.atomic_json(Path(p),d)
def load(p,n):
    spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def prepare():
    for path,digest in read(R/'baseline.json').items():
        if Path(path).name in ('product_packs.py','product_packs.json','product_chain_elite.json'):
            assert tx.sha(path)==digest,('Relevant source changed; rebase required',path)
    out=OUT;assert not out.exists();out.mkdir()
    template=Path('D:/fifaol3/season12-display/season_name_preflight.py').read_text('utf-8')
    template=template.replace('season-name','shop-value').replace('season_name','shop_value').replace('SEASON_NAME','SHOP_VALUE').replace('season name','shop value').replace('Season name','Shop value').replace('INSTALLED_SHOP_VALUE_CALLBACK','INSTALLED_SHOP_VALUE')
    template=template.replace("required={('client','data/ui/libs/module.big'),('server','play-local.bat'),('server',SELF.casefold())}",
       "required={('server',x) for x in ('product_packs.py','pack_value.py','gamedata/shop_value_products.json','play-local.bat',SELF.casefold())}")
    (out/'shop_value_preflight.py').write_text(template,'utf-8')
    play=(S/'play-local.bat').read_bytes();parents=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(parents)==1
    parent_relative='patches/'+parents[0].decode();parent=load(S/parent_relative,'shop_value_parent')
    proof=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
    parent_files={x:tx.sha(S/x) for x in (parent_relative,parent.MANIFEST,parent.RECEIPT)}
    (out/'play-local.bat').write_bytes(play.replace(b'patches\\'+parents[0],b'patches\\shop_value_preflight.py'))
    files=[]
    for relative,source in [('product_packs.py',R/'product_packs.py'),('pack_value.py',R/'pack_value.py'),('gamedata/shop_value_products.json',R/'shop_value_products.json'),('play-local.bat',out/'play-local.bat'),(SELF,out/'shop_value_preflight.py')]:
        files.append(dict(root='server',relative=relative,source=str(source.resolve()),parent_sha256=tx.digest(S/relative),sha256=tx.sha(source)))
    guards={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in composed['guards']}
    for row in files:guards[('server',row['relative'].casefold())]={k:row[k] for k in ('root','relative','sha256')}
    composed.update(guards=list(guards.values()),files_verified=False)
    composed.setdefault('ancestry',[]).append(dict(layer='shop-value-chain-state',parent=parent_files,native_status='PENDING'))
    m=dict(schema=1,revision='shop-value-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'),client=str(C),
       guards=list(guards.values()),composition=composed,files=files,parent_files=parent_files,parent_preflight=parent_relative,
       state_shop_replaced=False,scope='Cash shop valuation and chain state protocol only',native_status='PENDING')
    write(out/'manifest.json',m)
    write(out/'prepared.json',dict(manifest_sha256=tx.sha(out/'manifest.json'),parent_proof=proof,installer_sha256=tx.sha(__file__)))
    print(json.dumps(read(out/'prepared.json')))
def stopped():
    script="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'fifazf.exe' -or ($_.Name -match '^python(w)?\\.exe$' -and $_.CommandLine -match '(?i)D:\\\\FO3ID\\\\server\\\\(?:http_config|messenger)\\.py') } | Select-Object -ExpandProperty ProcessId"
    result=subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.strip():raise RuntimeError('Game or formal managed services still active: '+result.strip())
@contextmanager
def locks(server):
    owned=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            p=server/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY);payload=json.dumps(dict(pid=os.getpid(),task='shop-value')).encode();owned.append((p,fd,payload));os.write(fd,payload)
        _held_locks.add(server.resolve())
        yield
    finally:
        _held_locks.discard(server.resolve())
        for p,fd,payload in reversed(owned):
            os.close(fd)
            if p.exists() and p.read_bytes()==payload:p.unlink()
def preview(roots):
    out=OUT;m=read(out/'manifest.json')
    assert {(r['root'],r['relative']) for r in m['files']}==TARGETS and len(m['files'])==5
    assert m['state_shop_replaced'] is False
    for x,digest in m['parent_files'].items():assert tx.sha(roots['server']/x)==digest,('Parent changed',x)
    parent=load(roots['server']/m['parent_preflight'],'shop_value_current_parent');proof=parent.preflight(**roots)
    for row in m['files']:
        assert tx.sha(row['source'])==row['sha256']
        assert tx.digest(tx.target(roots,row))==row['parent_sha256'],('Formal file changed',row['relative'])
    assert not (roots['server']/MANIFEST).exists() and not (roots['server']/RECEIPT).exists()
    return m,proof
def install(server=S,client=C,review_sha=None,fixture=False,fail_after=None):
    roots=dict(server=Path(server).resolve(),client=Path(client).resolve());out=OUT
    if fixture:assert all(p.is_relative_to(R/'install-tests') for p in roots.values())
    else:assert roots==dict(server=S.resolve(),client=C.resolve())
    if (roots['server']/RECEIPT).exists():
        assert tx.sha(roots['server']/MANIFEST)==tx.sha(out/'manifest.json')
        return load(roots['server']/SELF,'shop_value_existing').preflight(**roots)
    m,parentproof=preview(roots)
    if review_sha is None:return dict(status='DRYRUN_PASS',parent=parentproof,manifest_sha256=tx.sha(out/'manifest.json'))
    assert review_sha==tx.sha(out/'manifest.json')
    if not fixture:stopped()
    with (nullcontext() if roots['server'] in _held_locks else locks(roots['server'])):
        if not fixture:stopped()
        preview(roots)
        backup=roots['server']/'backups'/(m['revision']+'-attempt-'+datetime.datetime.now().strftime('%H%M%S-%f'));backup.mkdir(parents=True)
        protected={n:tx.sha(roots['server']/'gamedata'/n) for n in ('state.json','shop.json')}
        for n in protected:shutil.copyfile(roots['server']/'gamedata'/n,backup/('audit-'+n))
        receipt=dict(status='INSTALLED_SHOP_VALUE',revision=m['revision'],manifest_sha256=review_sha,backup=str(backup),state_shop_replaced=False,native_status='PENDING')
        write(backup/'receipt-candidate.json',receipt)
        entries=list(m['files'])+[
          dict(root='server',relative=MANIFEST,source=str(out/'manifest.json'),parent_sha256=None,sha256=review_sha),
          dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json'))]
        def validate():
            if not fixture:stopped()
            preview(roots)
            drift=[n for n,v in protected.items() if tx.sha(roots['server']/'gamedata'/n)!=v]
            if drift:
                details={}
                for n in drift:
                    before=read(backup/('audit-'+n));after=read(roots['server']/'gamedata'/n)
                    details[n]=dict(before=protected[n],after=tx.sha(roots['server']/'gamedata'/n),changed_keys=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)])
                write(backup/'precommit-drift.json',details)
            assert all(tx.sha(roots['server']/'gamedata'/n)==v for n,v in protected.items())
        transaction=tx.commit_transaction(roots,entries,backup,validate,fail_after=fail_after)
        try:
            proof=load(roots['server']/SELF,'shop_value_installed').preflight(**roots)
            assert all(tx.sha(roots['server']/'gamedata'/n)==v for n,v in protected.items())
            transaction.update(status='installed',preflight=proof,protected=protected,state_shop_written=False)
            write(backup/'transaction.json',transaction)
        except BaseException:
            tx.restore_completed(roots,transaction,backup);transaction['status']='rolled_back';write(backup/'transaction.json',transaction);raise
        result=dict(status='INSTALLED_SHOP_VALUE_NATIVE_PENDING',backup=str(backup),preflight=proof,state_shop_unchanged=True)
        if not fixture:write(R/'installed.json',result)
        return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','preview','apply']);p.add_argument('--review-sha');a=p.parse_args()
    if a.action=='prepare':prepare()
    else:print(json.dumps(install(review_sha=a.review_sha if a.action=='apply' else None)))
