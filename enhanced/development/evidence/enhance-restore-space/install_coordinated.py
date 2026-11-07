"""Install one UI delta and a new flat guard layer. Run only in assigned writer slot."""
from patch_restore_space import *
import importlib.util,re,subprocess
from contextlib import contextmanager
SERVER=Path(r'D:\FO3ID\server');CLIENT=Path(r'D:\FO3ID\32795')
SELF='patches/restore_space_preflight.py'
MANIFEST='patches/restore-space-installed.json';RECEIPT='patches/restore-space-receipt.json'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def encoded(o):return (json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def closed():
    q=subprocess.run(['powershell.exe','-NoProfile','-Command',"if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 1}"],creationflags=subprocess.CREATE_NO_WINDOW)
    if q.returncode:raise RuntimeError('Game must be closed normally')
@contextmanager
def locks():
    owned=[]
    try:
        for name in ['.shop-release.lock','.fo3-publish.lock']:
            p=SERVER/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_BINARY',0))
            body=encoded(dict(pid=os.getpid(),release='restore-space-v1'));os.write(fd,body);os.fsync(fd)
            owned.append((p,fd,body))
        yield
    finally:
        for p,fd,body in reversed(owned):
            os.close(fd)
            if p.exists() and p.read_bytes()==body:p.unlink()
def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--parent',required=True);ap.add_argument('--parent-sha',required=True);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
    parentpath=(SERVER/args.parent).resolve()
    assert parentpath.is_relative_to(SERVER/'patches')
    assert sha(parentpath.read_bytes())==args.parent_sha
    with locks():
        closed()
        play=SERVER/'play-local.bat';oldplay=play.read_bytes()
        oldcommand=('patches\\'+parentpath.name).encode()
        assert oldplay.count(oldcommand)==1,'Parent is not the current launcher selection'
        parent=load(parentpath,'restore_space_parent');prior=parent.preflight(SERVER,CLIENT)
        c=parent.compose_manifest(SERVER,CLIENT)
        validator=load(SERVER/'patches/startup_market_preflight.py','restore_space_validator')
        assert validator.sha(SERVER/'patches/startup_market_preflight.py')=='49eafb6eaa5ec954bfc65c4460aec2a3f14e9bb93dbbf6547cedfded44393d8a'
        validator.verify_manifest(c,SERVER,CLIENT)
        report,staged=build()
        source=(SERVER/'patches/exp_selection_preflight.py').read_text(encoding='utf8')
        source=source.replace('exp-selection-installed.json','restore-space-installed.json').replace('exp-selection-receipt.json','restore-space-receipt.json').replace('exp_selection_preflight.py','restore_space_preflight.py').replace('INSTALLED_EXP_SELECTION','INSTALLED_RESTORE_SPACE').replace('EXP_SELECTION_PREFLIGHT_PASS','RESTORE_SPACE_PREFLIGHT_PASS')
        source=source.replace('Exact-file read-only gate for a global player database revision.','Exact-file read-only gate for the recovery animation Space shortcut.').replace("native_status='PENDING'","native_status='SKIPPED_BY_USER'")
        source=source.replace("('client','data/ui/teammanagementexpcapsulescreen.big')","('client','data/ui/teammanagementplayerenhancingpopupscreen.big')")
        assert "('server','patches/restore_space_preflight.py')" in source
        compile(source,SELF,'exec')
        newplay=oldplay.replace(oldcommand,b'patches\\restore_space_preflight.py')
        payloads={TARGET:staged.read_bytes(),SERVER/SELF:source.encode('utf8'),play:newplay}
        guards=validator.table(c['guards'])
        for path,body in payloads.items():
            root='client' if path.is_relative_to(CLIENT) else 'server';base=CLIENT if root=='client' else SERVER
            rel=path.relative_to(base).as_posix();key=(root,rel.casefold())
            if key in guards:assert validator.sha(path)==guards[key]['sha256']
            else:assert not path.exists(),'New guard helper already exists'
            guards[key]=dict(root=root,relative=rel,sha256=sha(body))
        c.update(guards=list(guards.values()),files_verified=False)
        c.setdefault('ancestry',[]).append(dict(layer='restore-space',native_status='SKIPPED_BY_USER'))
        revision='restore-space-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        m=dict(schema=1,revision=revision,client=str(CLIENT),state_shop_replaced=False,native_status='SKIPPED_BY_USER',
               guards=c['guards'],composition=c,parent_preflight=args.parent,parent_preflight_sha256=args.parent_sha)
        payloads[SERVER/MANIFEST]=encoded(m)
        payloads[SERVER/RECEIPT]=encoded(dict(status='INSTALLED_RESTORE_SPACE',manifest_sha256=sha(payloads[SERVER/MANIFEST]),revision=revision,state_shop_replaced=False))
        for path in [SERVER/MANIFEST,SERVER/RECEIPT]:assert not path.exists()
        (OUT/'coordinated-plan.json').write_bytes(encoded(dict(parent=args.parent,prior=prior,revision=revision,files={str(p):sha(b) for p,b in payloads.items()})))
        if not args.apply:print('Prepared; no formal payload written');return
        closed();validator.verify_manifest(parent.compose_manifest(SERVER,CLIENT),SERVER,CLIENT)
        backup=SERVER/'backups'/revision;backup.mkdir();before={p:p.read_bytes() if p.exists() else None for p in payloads}
        for i,(p,body) in enumerate(before.items()):
            if body is not None:(backup/(str(i)+'-'+p.name)).write_bytes(body)
        committed=[]
        order=[p for p in payloads if p!=play]+[play]
        try:
            for path in order:
                assert (path.read_bytes() if path.exists() else None)==before[path],'Concurrent target change'
                tmp=path.with_name(path.name+'.restore-space.new');tmp.write_bytes(payloads[path]);os.replace(tmp,path);committed.append(path)
            result=load(SERVER/SELF,'restore_space_installed').preflight(SERVER,CLIENT)
        except BaseException:
            for path in reversed(committed):
                if path.read_bytes()!=payloads[path]:raise RuntimeError('Concurrent post-install change; refusing overwrite')
                if before[path] is None:path.unlink()
                else:
                    tmp=path.with_name(path.name+'.restore-space.rollback');tmp.write_bytes(before[path]);os.replace(tmp,path)
            raise
        report.update(installed=True,backup=str(backup),preflight=result,top_preflight=str(SERVER/SELF),top_manifest=str(SERVER/MANIFEST),top_receipt=str(SERVER/RECEIPT),services_restarted=False)
        (OUT/'installation.json').write_bytes(encoded(report));print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
