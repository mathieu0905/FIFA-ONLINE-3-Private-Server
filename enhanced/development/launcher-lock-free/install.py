from pathlib import Path
import copy, datetime, hashlib, importlib.util, json, os, re, sys
sys.dont_write_bytecode=True
R=Path(__file__).parent; S=Path('D:/FO3ID/server'); C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(R.parent/'manutd-legends'))
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
tx=load(R.parent/'manutd-legends/install.py','transaction')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
SELF='patches/launch_readonly_preflight.py'; MANIFEST='patches/launch-readonly-installed.json'; RECEIPT='patches/launch-readonly-receipt.json'

def build():
    source=S/'launcher/fo3_control.py'; raw=source.read_bytes(); code=raw.decode('utf8').replace('\r\n','\n')
    start=code.index('    validate()\n',code.index('def start_client():'))
    end=code.index('    env=dict(os.environ,__COMPAT_LAYER=',start)
    code=code[:start]+'''    # Launch installed files only. Publication owns resource installation and checks.
    # A release lock must never turn an ordinary client launch into a write transaction.
    closed()
'''+code[end:]
    needle="    lock=None;token=json.dumps(dict(pid=os.getpid(),task='native-launcher-'+args.action))"
    replacement='''    if args.action=='client-start':
        start_client();return
    if args.action=='server-start' and ready():
        say('服务端已经运行，无需重复启动。');return
'''+needle
    assert code.count(needle)==1;code=code.replace(needle,replacement)
    needle="            with lock.open('x') as f:f.write(token)"
    assert code.count(needle)==1
    code=code.replace(needle,"""            try:
                with lock.open('x') as f:f.write(token)
            except FileExistsError:
                raise RuntimeError('正在发布更新，暂不能启动或停止服务端；已有服务就绪时仍可打开客户端。') from None""")
    compile(code,str(source),'exec');(R/'fo3_control.py').write_text(code,'utf8')
    (R/'baseline.json').write_bytes(body({str(source):sha(source)}))
    return raw,code.encode('utf8')

def main():
    before_control,new_control=build()
    if '--build' in sys.argv:return
    held=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            p=S/name; token=body(dict(task='launch-readonly',pid=os.getpid()))
            fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);held.append((p,fd,token));os.write(fd,token);os.fsync(fd)
        coord=json.loads((R.parent/'coordination-current.json').read_text('utf8'))
        assert not coord.get('current_unhanded_writers') and coord.get('next_formal_writer') is None,'Another installation window is assigned'
        assert (S/'launcher/fo3_control.py').read_bytes()==before_control,'Launcher changed; rebase'
        play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1
        parent_rel=matches[0].decode().replace('\\','/');parent=load(S/parent_rel,'current_parent');prior=parent.preflight(S,C)
        composition=copy.deepcopy(parent.compose_manifest(S,C));table={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in composition['guards']};assert len(table)==len(composition['guards'])
        helper=(S/parent_rel).read_text('utf8').replace(parent.MANIFEST,MANIFEST).replace(parent.RECEIPT,RECEIPT).replace(parent.SELF,SELF)
        receipt=json.loads((S/parent.RECEIPT).read_text('utf8'))
        helper=helper.replace(receipt['status'],'INSTALLED_LAUNCH_READONLY').replace(prior['status'],'LAUNCH_READONLY_PREFLIGHT_PASS');compile(helper,SELF,'exec')
        ledger=S/'docs/工程经验与修改边界.txt'
        note='''\r\nFO3-LAUNCH-LOCK-001（2026-11-07）：确认 native launcher 对 client-start 申请发布锁，撞上 wonderkid 安装时直接报 Errno 17。用户要求有发布锁也可启动游戏。正式 launcher/fo3_control.py 改为 client-start 只检查游戏未重复运行、正式服务就绪并启动已安装 fifalauncher，不申请/删除发布锁，不重装语言或强化资源、不停服、不读取正在变化的发布门禁。已有服务就绪的 server-start 直接返回；真正启停服务仍锁保护并显示中文冲突原因。安装/独立check/新服务启动的完整版本及player_import检查保留，play独立player_import行保留。本次仅Python启动控制/账本/新子层元数据，无客户端资源或state/shop写入，无服务重启、无游戏GUI操作。回归 D:/fifaol3/launcher-lock-free/test_control.py 验证有锁/无锁启动、离线拒绝、重复游戏拒绝、服务启停冲突保留锁及启动失败；模拟Popen不代表实机启动或比赛通过。\r\n'''
        payload=[('launcher/fo3_control.py',new_control),(SELF,helper.encode('utf8')),('docs/工程经验与修改边界.txt',ledger.read_bytes()+note.encode('utf8')),('play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))]
        entries=[]
        for rel,data in payload:
            target=S/rel;before=sha(target) if target.exists() else None;after=hashlib.sha256(data).hexdigest();key=('server',rel.casefold())
            if key in table:assert table[key]['sha256']==before,('Baseline differs',rel)
            else:assert before is None,('Unregistered existing file',rel)
            table[key]=dict(root='server',relative=rel,sha256=after)
            entries.append(dict(root='server',relative=rel,target=target,source=data,before=before,after=after))
        composition['guards']=list(table.values());composition['files_verified']=False
        composition.setdefault('ancestry',[]).append(dict(layer='LAUNCH-READONLY',native_status='PENDING'))
        policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'})
        if not any(x['root']==policy['root'] and x['relative']==policy['relative'] for x in composition.setdefault('receipt_policies',[])):composition['receipt_policies'].append(policy)
        revision='launch-readonly-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,parent_preflight=parent_rel)
        mb=body(manifest);rb=body(dict(status='INSTALLED_LAUNCH_READONLY',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
        for rel,data in ((MANIFEST,mb),(RECEIPT,rb)):
            assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=data,before=None,after=hashlib.sha256(data).hexdigest()))
        entries.sort(key=lambda e:e['relative']=='play-local.bat');backup=S/'backups'/revision
        tx.commit(entries,backup,lambda:load(S/SELF,'installed_gate').preflight(S,C))
        result=dict(status='INSTALLED_LAUNCH_READONLY',backup=str(backup),preflight=load(S/SELF,'final_gate').preflight(S,C),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_available=True,function_signatures=dict(preflight='server=None, client=None',compose_manifest='server=None, client=None'),files={str(p):sha(p) for p in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat',S/'launcher/fo3_control.py')},state_shop_written=False,services_action='No service stop/start/restart',native_verified=False,match_verified=False,GUI_status='No game launch or GUI operation',observed_at=datetime.datetime.now().astimezone().isoformat(),handoff=str(R/'installed-handback.json'))
        (R/'installed-handback.json').write_bytes(body(result))
        tx.atomic(body(result),R.parent/'root-current-top.json');print(json.dumps(result,ensure_ascii=True))
    finally:
        for p,fd,token in reversed(held):
            os.close(fd)
            if p.exists() and p.read_bytes()==token:p.unlink()
if __name__=='__main__':main()
