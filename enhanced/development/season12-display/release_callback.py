"""Prepare or apply a narrow client-only transaction. Never controls services or game."""
from pathlib import Path
import argparse, datetime, importlib.util, json, os, re, shutil, subprocess, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'D:/fifaol3')
import install_bulk_seasons as tx
S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
MANIFEST='patches/season-name-installed.json';RECEIPT='patches/season-name-receipt.json';SELF='patches/season_name_preflight.py'
ALLOWED={('client','data/ui/libs/Module.big'),('server','play-local.bat'),('server',SELF)}
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):tx.atomic_json(Path(p),v)
def gameclosed():
    command="$p=@(Get-Process -Name fifazf,fifaonline3,fifa3 -ErrorAction SilentlyContinue); if($p.Count -gt 0){$p | Select-Object Id,ProcessName | ConvertTo-Json -Compress; exit 9}; exit 0"
    p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError('Game active or process check failed: '+p.stdout+p.stderr)
def prepare(out,candidate=ROOT/'callback-v1'):
    assert out.is_relative_to(ROOT) and not out.exists();out.mkdir()
    candidate=candidate.resolve();assert candidate.is_relative_to(ROOT)
    build=read(candidate/'build.json');replay=read(candidate/'replay.json')
    assert replay['status']=='ACTUAL_CALLBACK_BYTECODE_REPLAY_PASS' and replay['changed_seasons']==[12,13,84]
    assert tx.sha(C/'data/ui/libs/Module.big')==build['source_sha256']
    assert tx.sha(candidate/'Module.big')==build['module_sha256']
    play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches\\([A-Za-z0-9_]+_preflight\.py)',play);assert len(names)==1
    parent_rel='patches/'+names[0].decode();parent=load(S/parent_rel,'season_name_parent')
    parentcheck=parent.preflight(S,C);comp=parent.compose_manifest(S,C)
    rows=[]
    def add(root,rel,source):
        target=(S if root=='server' else C)/rel
        rows.append(dict(root=root,relative=rel,source=str(source),parent_sha256=tx.sha(target) if target.exists() else None,sha256=tx.sha(source)))
    shutil.copyfile(candidate/'Module.big',out/'Module.big')
    shutil.copyfile(ROOT/'season_name_preflight.py',out/'season_name_preflight.py')
    (out/'play-local.bat').write_bytes(play.replace(b'patches\\'+names[0],b'patches\\season_name_preflight.py'))
    add('client','data/ui/libs/Module.big',out/'Module.big');add('server',SELF,out/'season_name_preflight.py');add('server','play-local.bat',out/'play-local.bat')
    guards={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']}
    for row in rows:guards[(row['root'],row['relative'].casefold())]={k:row[k] for k in ('root','relative','sha256')}
    parents={rel:tx.sha(S/rel) for rel in [parent_rel,parent.MANIFEST,parent.RECEIPT]}
    ancestry=list(comp.get('ancestry',[]))+[dict(preflight=parent_rel,files=parents)]
    comp.update(guards=list(guards.values()),ancestry=ancestry)
    revision='season-name-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    m=dict(schema=1,revision=revision,client=str(C),guards=list(guards.values()),composition=comp,
      files=rows,parent_files=parents,parent_preflight=parent_rel,state_shop_replaced=False,
      scope='Only PlayerListUtil.method12 callback text for seasons12/13/84',native_status='PENDING')
    write(out/'manifest.json',m)
    write(out/'prepare.json',dict(status='PREPARED',parent_check=parentcheck,manifest_sha256=tx.sha(out/'manifest.json'),installer_sha256=tx.sha(__file__)))
    print(json.dumps(read(out/'prepare.json')))
def preview(out,roots):
    m=read(out/'manifest.json');assert m['schema']==1 and m['state_shop_replaced'] is False
    assert {(r['root'],r['relative']) for r in m['files']}==ALLOWED and len(m['files'])==3
    assert not (roots['server']/MANIFEST).exists() and not (roots['server']/RECEIPT).exists()
    for rel,digest in m['parent_files'].items():assert tx.sha(roots['server']/rel)==digest,('Parent changed',rel)
    parent=load(roots['server']/m['parent_preflight'],'season_name_apply_parent');proof=parent.preflight(**roots)
    for row in m['files']:
        assert tx.sha(row['source'])==row['sha256']
        assert tx.digest(tx.target(roots,row))==row['parent_sha256'],('Payload parent changed',row['relative'])
    return m,proof
def apply(out,review_sha=None,window=None):
    roots=dict(server=S.resolve(),client=C.resolve())
    if (S/RECEIPT).exists():
        assert tx.sha(S/MANIFEST)==tx.sha(out/'manifest.json')
        return load(S/SELF,'season_name_installed').preflight(**roots)
    m,proof=preview(out,roots)
    if not review_sha:return dict(status='DRYRUN_PASS',parent=proof,manifest_sha256=tx.sha(out/'manifest.json'))
    assert review_sha==tx.sha(out/'manifest.json')
    assert window and window=='root-exclusive-gameclosed-no-restart', 'Coordinator resource window required'
    gameclosed();lock=S/'.shop-release.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        gameclosed();preview(out,roots)
        backup=S/'backups'/m['revision'];backup.mkdir()
        audit={n:tx.sha(S/'gamedata'/n) for n in ('state.json','shop.json')}
        receipt=dict(status='INSTALLED_SEASON_NAME_CALLBACK',revision=m['revision'],manifest_sha256=review_sha,
          backup=str(backup),state_shop_replaced=False,native_status='PENDING')
        write(backup/'receipt-candidate.json',receipt)
        entries=list(m['files'])+[
          dict(root='server',relative=MANIFEST,source=str(out/'manifest.json'),parent_sha256=None,sha256=review_sha),
          dict(root='server',relative=RECEIPT,source=str(backup/'receipt-candidate.json'),parent_sha256=None,sha256=tx.sha(backup/'receipt-candidate.json'))]
        def validate():gameclosed();preview(out,roots)
        transaction=tx.commit_transaction(roots,entries,backup,validate)
        try:
            child=load(S/SELF,'season_name_installed');proof=child.preflight(**roots)
            transaction.update(status='installed',preflight=proof,state_shop_before=audit,
              state_shop_after={n:tx.sha(S/'gamedata'/n) for n in audit},state_shop_written=False,service_restart=False)
            write(backup/'transaction.json',transaction)
        except BaseException:
            tx.restore_completed(roots,transaction,backup);transaction['status']='rolled_back';write(backup/'transaction.json',transaction);raise
        result=dict(status='INSTALLED_SEASON_NAME_NATIVE_PENDING',preflight=proof,backup=str(backup),restart=False)
        write(ROOT/'installed.json',result);return result
    finally:lock.unlink(missing_ok=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','preview','apply']);p.add_argument('--release',type=Path,default=ROOT/'release-v1');p.add_argument('--candidate',type=Path,default=ROOT/'callback-v1');p.add_argument('--review-sha');p.add_argument('--window');a=p.parse_args()
    if a.action=='prepare':prepare(a.release.resolve(),a.candidate)
    else:print(json.dumps(apply(a.release.resolve(),a.review_sha if a.action=='apply' else None,a.window)))
