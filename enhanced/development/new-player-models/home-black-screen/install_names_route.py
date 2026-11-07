"""Install the minimal names-query compatibility delta on the current formal release."""
from pathlib import Path
from contextlib import contextmanager
import datetime, hashlib, importlib.util, json, os, re, subprocess, sys, tempfile
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
SELF='patches/names_route_preflight.py';MANIFEST='patches/names-route-installed.json';RECEIPT='patches/names-route-receipt.json'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def encoded(o):return (json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def closed():
    q=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 1}'],creationflags=subprocess.CREATE_NO_WINDOW)
    if q.returncode:raise RuntimeError('Game must be closed normally')
@contextmanager
def locks(task='names-route'):
    owned=[]
    try:
        for name in ['.shop-release.lock','.fo3-publish.lock']:
            p=S/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY)
            body=encoded(dict(pid=os.getpid(),task=task,thread='01a1b189-f47d-7e90-9ace-ae0950b51062'))
            os.write(fd,body);os.fsync(fd);owned.append((p,fd,body))
        yield
    finally:
        for p,fd,body in reversed(owned):
            os.close(fd)
            if p.exists() and p.read_bytes()==body:p.unlink()
def atomic(path,body):
    fd,name=tempfile.mkstemp(prefix=path.name+'.names-route-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(body);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
def commit(payloads,before,order,fail_at=None):
    committed=[]
    try:
        for i,p in enumerate(order):
            if (p.read_bytes() if p.exists() else None)!=before[p]:raise RuntimeError('Concurrent target change: '+str(p))
            if i==fail_at:raise RuntimeError('Injected commit failure')
            atomic(p,payloads[p]);committed.append(p)
    except BaseException:
        for p in reversed(committed):
            if not p.exists() or p.read_bytes()!=payloads[p]:raise RuntimeError('Later edit retained; rollback refused: '+str(p))
            if before[p] is None:p.unlink()
            else:atomic(p,before[p])
        raise
    return committed
def test_commit():
    with tempfile.TemporaryDirectory(prefix='names-route-io-') as temp:
        paths=[Path(temp)/'module',Path(temp)/'new-gate',Path(temp)/'play']
        paths[0].write_bytes(b'old');paths[2].write_bytes(b'oldplay')
        before={p:p.read_bytes() if p.exists() else None for p in paths};payloads={p:('new'+str(i)).encode() for i,p in enumerate(paths)}
        for step in range(3):
            try:commit(payloads,before,paths,fail_at=step)
            except RuntimeError as error:assert str(error)=='Injected commit failure'
            assert all((p.read_bytes() if p.exists() else None)==before[p] for p in paths)
        paths[0].write_bytes(b'external')
        try:commit(payloads,before,paths)
        except RuntimeError as error:assert 'Concurrent target change' in str(error)
        else:raise AssertionError('Drift was not rejected')
        assert paths[0].read_bytes()==b'external'
        paths[0].write_bytes(b'old');commit(payloads,before,paths)
        assert all(p.read_bytes()==payloads[p] for p in paths)
    return dict(failure_rollback_steps=3,concurrent_drift_preserved=True,successful_commit=True)
def main():
    checks=test_commit();closed()
    build=json.loads((ROOT/'names-route-build.json').read_text('utf8'))
    with locks():
        closed();play=S/'play-local.bat';oldplay=play.read_bytes()
        parentrel=re.search(rb'\.venv\\Scripts\\python\.exe (patches\\\w+_preflight\.py)',oldplay).group(1).decode().replace('\\','/')
        parentpath=S/parentrel;parent=load(parentpath,'names_route_parent');prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
        # Fresh payload against the current Module and DB; never restore an old parent.
        load(ROOT/'build_names_route.py','names_route_build').build()
        build=json.loads((ROOT/'names-route-build.json').read_text('utf8'))
        target=Path(build['target']);body=Path(build['payload']).read_bytes()
        assert sha(target)==build['before_sha256'] and digest(body)==build['after_sha256']
        source=(S/'patches/reward_upgrade_preflight.py').read_text('utf8')
        source=source.replace('reward-upgrade-installed.json','names-route-installed.json').replace('reward-upgrade-receipt.json','names-route-receipt.json').replace('reward_upgrade_preflight.py','names_route_preflight.py')
        source=source.replace('INSTALLED_REWARD_UPGRADE','INSTALLED_NAMES_ROUTE').replace('REWARD_UPGRADE_PREFLIGHT_PASS','NAMES_ROUTE_PREFLIGHT_PASS')
        source=source.replace('additive official club-career update','localized names-query compatibility fix').replace('manutd-legends','names-route').replace('Club-history','Names-route')
        source=source.replace("('server',SELF)}","('server',SELF),('client','data/ui/libs/module.big')}")
        compile(source,SELF,'exec')
        newplay=oldplay.replace(parentrel.replace('/','\\').encode(),SELF.replace('/','\\').encode())
        assert oldplay!=newplay
        revision='names-route-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        doc=S/'docs/工程经验与修改边界.txt'
        note=('\n\nFO3-UI-NAMES（'+revision+'，正式安装，native待人类重启验证）：\n'
          '真实23:57:32 telemetry/ui/errors：进入首页前 PLAYERGRADE 回调上下文报 no such table: names。当前正式6语言DB均有names，离线完整性与5569父guards通过，不能据此认定模型导致此UI报错。\n'
          '兼容修复仅Module ConnectionPool.execute前插入姓名查询路由：eng/chi/tha/vie/ind的精确FROM names空格查询走fifadb中names+locale表，整表66280行逐列等价已验证；其余数据库、非姓名SQL和kor原路径保持（kor有9条本地化差异，已严格排除）。无新method/trait/签名，原方法全部原指令与分支重定位保持；仅一个DoABC tag修改，其它SWF tag和BIG成员保持。真实新增前缀字节码回放、五语全行及查询等价、缺表失败样本和原子临时I/O回滚/并发漂移检查通过。\n'
          '不写DB/data0/state/shop，不更换真实球员/卡实例/余额/阵容，不重启服务、不操作GUI。贝林首页带球导致全屏黑屏/退出仍单独未修复，不能将本次姓名修复声称为模型或比赛通过。证据 D:/fifaol3/new-player-models/home-black-screen/names-route-build.json、names-route-installed.json；复验正式patches/names_route_preflight.py。\n')
        payloads={target:body,S/SELF:source.encode('utf8'),doc:doc.read_bytes()+note.encode('utf8'),play:newplay}
        guards={}
        for g in composition['guards']:
            key=(g['root'],g['relative'].replace('\\','/').casefold())
            if key in guards:assert guards[key]['sha256']==g['sha256']
            guards[key]=dict(g)
        for p,b in payloads.items():
            root='client' if p.is_relative_to(C) else 'server';base=C if root=='client' else S;rel=p.relative_to(base).as_posix();key=(root,rel.casefold())
            if key in guards:assert sha(p)==guards[key]['sha256']
            elif p.exists():assert p==doc,'Unexpected unregistered target'
            guards[key]=dict(root=root,relative=rel,sha256=digest(b))
        composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='names-route',native_status='PENDING'))
        parentreceipt=json.loads((S/parent.RECEIPT).read_text('utf8'))
        composition.setdefault('receipt_policies',[]).append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in parentreceipt.items() if k!='native_status'}))
        manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parentrel,parent_preflight_sha256=sha(parentpath))
        payloads[S/MANIFEST]=encoded(manifest)
        payloads[S/RECEIPT]=encoded(dict(status='INSTALLED_NAMES_ROUTE',manifest_sha256=digest(payloads[S/MANIFEST]),revision=revision,state_shop_replaced=False,native_status='PENDING'))
        for p in (S/SELF,S/MANIFEST,S/RECEIPT):assert not p.exists()
        before={p:p.read_bytes() if p.exists() else None for p in payloads}
        protected={str(p):sha(p) for p in (S/'gamedata/state.json',S/'gamedata/shop.json',S/'gamedata/fifadb.sqlite',C/'data/data_0.big')}
        backup=S/'backups'/revision;backup.mkdir()
        for i,(p,b) in enumerate(before.items()):
            if b is not None:(backup/(str(i)+'-'+p.name)).write_bytes(b)
        (backup/'before.json').write_bytes(encoded({str(p):digest(b) if b is not None else None for p,b in before.items()}))
        closed();parent.preflight(S,C)
        order=[p for p in payloads if p!=play]+[play]
        committed=commit(payloads,before,order)
        try:result=load(S/SELF,'names_route_installed').preflight(S,C)
        except BaseException:
            restore={p:before[p] for p in committed if before[p] is not None}
            for p in reversed(committed):
                if p.read_bytes()!=payloads[p]:raise RuntimeError('Concurrent post-version retained')
                if before[p] is None:p.unlink()
                else:atomic(p,before[p])
            raise
        after={p:sha(Path(p)) for p in protected}
        assert after[str(S/'gamedata/fifadb.sqlite')]==protected[str(S/'gamedata/fifadb.sqlite')]
        assert after[str(C/'data/data_0.big')]==protected[str(C/'data/data_0.big')]
        report=dict(status='INSTALLED_NATIVE_PENDING',revision=revision,backup=str(backup),preflight=result,top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',
            hashes={str(p):sha(p) for p in (S/SELF,S/MANIFEST,S/RECEIPT,play,target)},protected_before=protected,protected_after=after,formal_written=[str(p) for p in payloads],services_restarted=False,gui_used=False,state_shop_written=False,model_crash_fixed=False,transaction_tests=checks)
        (ROOT/'names-route-installed.json').write_bytes(encoded(report));print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
