"""Install one UI delta and a new flat guard layer. Run only in assigned writer slot."""
from build import *
import os,datetime,shutil
OUT=ROOT
import importlib.util,re,subprocess
from contextlib import contextmanager
SERVER=Path(r'D:\FO3ID\server');CLIENT=Path(r'D:\FO3ID\32795')
SELF='patches/grade_color_preflight.py'
MANIFEST='patches/grade-color-installed.json';RECEIPT='patches/grade-color-receipt.json'
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
            body=encoded(dict(pid=os.getpid(),release='grade-color-v1'));os.write(fd,body);os.fsync(fd)
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
        parent=load(parentpath,'grade_color_parent');prior=parent.preflight(SERVER,CLIENT)
        c=parent.compose_manifest(SERVER,CLIENT)
        validator=load(SERVER/'patches/startup_market_preflight.py','grade_color_validator')
        assert validator.sha(SERVER/'patches/startup_market_preflight.py')=='49eafb6eaa5ec954bfc65c4460aec2a3f14e9bb93dbbf6547cedfded44393d8a'
        validator.verify_manifest(c,SERVER,CLIENT)
        report=build()
        source=(SERVER/'patches/exp_selection_preflight.py').read_text(encoding='utf8')
        source=source.replace('exp-selection-installed.json','grade-color-installed.json').replace('exp-selection-receipt.json','grade-color-receipt.json').replace('exp_selection_preflight.py','grade_color_preflight.py').replace('INSTALLED_EXP_SELECTION','INSTALLED_GRADE_COLOR').replace('EXP_SELECTION_PREFLIGHT_PASS','GRADE_COLOR_PREFLIGHT_PASS')
        source=source.replace('Exact-file read-only gate for a global player database revision.','Exact-file read-only gate for gold and chromatic enhancement badges.').replace("native_status='PENDING'","native_status='NOT_VERIFIED'")
        source=source.replace("('client','data/ui/teammanagementexpcapsulescreen.big')","('client','data/ui/components/tilelist.big')")
        assert "('server','patches/grade_color_preflight.py')" in source
        compile(source,SELF,'exec')
        newplay=oldplay.replace(oldcommand,b'patches\\grade_color_preflight.py')
        payloads={SERVER/SELF:source.encode('utf8'),play:newplay}
        for row in report['files']:
            body=Path(row['payload']).read_bytes()
            payloads[CLIENT/row['relative']]=body
            payloads[SERVER/row['installer_source']]=body
        guards=validator.table(c['guards'])
        for path,body in payloads.items():
            root='client' if path.is_relative_to(CLIENT) else 'server';base=CLIENT if root=='client' else SERVER
            rel=path.relative_to(base).as_posix();key=(root,rel.casefold())
            if key in guards:assert validator.sha(path)==guards[key]['sha256']
            elif path.exists():
                # Legacy install-grade20.ps1 reads these six source BIGs, which
                # older layers did not all guard. Pin only this explicit set.
                external={p:r['before_sha256'] for r in report['files'] for p in (SERVER/r['installer_source'],CLIENT/r['relative'])}
                assert path in external and sha(path.read_bytes())==external[path],('Unregistered existing target',str(path))
            guards[key]=dict(root=root,relative=rel,sha256=sha(body))
        c.update(guards=list(guards.values()),files_verified=False)
        c.setdefault('ancestry',[]).append(dict(layer='grade-color',native_status='NOT_VERIFIED'))
        revision='grade-color-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        m=dict(schema=1,revision=revision,client=str(CLIENT),state_shop_replaced=False,native_status='NOT_VERIFIED',
               guards=c['guards'],composition=c,parent_preflight=args.parent,parent_preflight_sha256=args.parent_sha)
        payloads[SERVER/MANIFEST]=encoded(m)
        payloads[SERVER/RECEIPT]=encoded(dict(status='INSTALLED_GRADE_COLOR',manifest_sha256=sha(payloads[SERVER/MANIFEST]),revision=revision,state_shop_replaced=False))
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
                tmp=path.with_name(path.name+'.grade-color.new');tmp.write_bytes(payloads[path]);os.replace(tmp,path);committed.append(path)
            result=load(SERVER/SELF,'grade_color_installed').preflight(SERVER,CLIENT)
        except BaseException:
            for path in reversed(committed):
                if path.read_bytes()!=payloads[path]:raise RuntimeError('Concurrent post-install change; refusing overwrite')
                if before[path] is None:path.unlink()
                else:
                    tmp=path.with_name(path.name+'.grade-color.rollback');tmp.write_bytes(before[path]);os.replace(tmp,path)
            raise
        report.update(installed=True,backup=str(backup),preflight=result,top_preflight=str(SERVER/SELF),top_manifest=str(SERVER/MANIFEST),top_receipt=str(SERVER/RECEIPT),services_restarted=False)
        (OUT/'installation.json').write_bytes(encoded(report));print(json.dumps({k:report[k] for k in ('installed','backup','preflight','top_preflight','top_manifest','top_receipt','services_restarted')},ensure_ascii=True))
if __name__=='__main__':main()
