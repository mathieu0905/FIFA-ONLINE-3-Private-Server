"""Official client-resource transaction; never stops services or changes assets."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(S));import hot_update_release as release
SELF='patches/lineup_enhance_v5_preflight.py';MANIFEST='patches/lineup-enhance-v5-installed.json';RECEIPT='patches/lineup-enhance-v5-receipt.json'
DOC='docs/工程经验与修改边界.txt';NAMES=('components-Button','components-ScrollingList','TeamManagementScreen')
def client_relative(name):return 'data/ui/'+name.replace('components-','components/')+'.big'
def server_relative(name):return 'patches/'+name.replace('components-','')+'.big'
def client_target(name):return C/client_relative(name)
def server_target(name):return S/server_relative(name)
sha=release.sha;body=release.body;read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
def write(p,value):release.atomic(Path(p),body(value))
def game_active():
    return 'fifazf.exe' in subprocess.check_output(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],text=True,errors='replace').lower()
def idle():
    if game_active():raise RuntimeError('更新已延后，当前游戏继续运行')
def deferred():
    result=dict(status='DEFERRED_GAME_RUNNING',formal_files_written=False,service_actions=False,message='更新已延后，当前游戏继续运行')
    write(W/'deferred.json',result);return result
def check_outputs():
    build=read(W/'client-build.json');tests=read(W/'client-tests.json')
    assert tests['status']=='PASS' and bool(tests['stack_checks']) and read(W/'install-tests.json')['status']=='PASS'
    for name in NAMES:
        assert sha(W/(name+'.big'))==tests['output_sha256'][name]==build[name]['sha256']
        assert sha(client_target(name))==tests['source_sha256'][name]==build[name]['source_sha256'],'Rebase resource on current official version'
        if server_target(name).exists():assert sha(server_target(name))==build[name]['source_sha256']
        else:assert name in ('TeamManagementScreen','components-Button')
    return build
def plan():
    build=check_outputs();play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches[\\/][A-Za-z0-9_]+_preflight\.py',play);assert len(names)==1
    assert b'tools\\player_import\\check.py' in play
    parent_path=names[0].decode().replace('\\','/');assert parent_path!=SELF
    parent=release.load(S/parent_path,'remember_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C))
    table={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']};assert len(table)==len(comp['guards'])
    helper=(S/parent_path).read_text('utf8')
    for old,new in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_LINEUP_ENHANCE_V5'),(prior['status'],'LINEUP_ENHANCE_V5_PREFLIGHT_PASS')):helper=helper.replace(old,new)
    helper=helper.replace(' if not required<=seen:'," required.update({('client','data/ui/components/scrollinglist.big'),('server','patches/scrollinglist.big'),('client','data/ui/teammanagementscreen.big'),('server','patches/teammanagementscreen.big'),('client','data/ui/components/button.big'),('server','patches/button.big')})\n if not required<=seen:")
    compile(helper,SELF,'exec');revision='lineup-enhance-v5-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    note='\n\nFO3-LINEUP-ENHANCE-V5 (2026-11-07)\n用户明确要求升级图标而非交换图标，并要求跳转后选对应主卡。新增独立Fo3LineupUpgradeButton原生SWF符号：复制原PlayerSwapButton的胶囊外框/35帧状态/原方法体，以代码原生DefineShape替换图标中心为双色向上双箭头；原交换图标、所有其它符号及全部DDS像素逐字节保留，不拉伸、不运行时自绘。三个新Shape复用原状态位图的无图标竖条恢复中心渐变，再绘制向上双箭头。\n主卡选择不再依赖屏幕行renderer或默认重复卡过滤。进入原强化页后打开原生显示全部并触发原生按钮事件，等待原生DataProvider中的精确_id/spid/grade；保持原锁策略和原生TimerUtil/DateUtils锁定时间语义，拒绝禁用/变化卡。原生clear selected player清旧对，再用原生post selected players和selected player公共query契约设置(main,null)，等价于原selectTarget的setter和owner消息，不自动选材料/解锁/强化/购买；单张卡也可仅作为主卡展示，真正交易继续原服务端校验。\n离线回放实际原生EnhancePlayerPanel.query18和first/second setter2/4，验证同SPID诱饵不替代、重复/单卡主卡正确、材料null、一次性、锁/失效锁/禁用/数据变化/未加载/离页等情形。增强页BIG完全未改，没有新增启动/库存钩子或别名。根screen所有后向分支都有显式label，精确最终driver通过stock AVMplus真实验证，旧缺label负对照继续#1021。UI符号静态解析及原生方法体一致通过；stock与回放不等于游戏GUI/实机验收。用户仍禁止游戏GUI。\n正式安装仅在游戏关闭、fresh实际top和基线、共同双锁/备份/CAS、完整guards/receipt policies下执行；游戏运行即延期，不要求退出、不强退/停服/重启，不改真实state/shop或其它聊天合法修改。\n'.encode('utf8')
    payload=[]
    for name in NAMES:
        if sha(W/(name+'.big'))==sha(client_target(name)):continue
        data=(W/(name+'.big')).read_bytes();payload.extend([('client',client_relative(name),data),('server',server_relative(name),data)])
    payload.extend([('server',SELF,helper.encode('utf8')),('server',DOC,(S/DOC).read_bytes()+note),('server','play-local.bat',play.replace(names[0],SELF.replace('/','\\').encode()))])
    entries=[]
    for root,relative,data in payload:
        target=(S if root=='server' else C)/relative;before=sha(target) if target.exists() else None;after=hashlib.sha256(data).hexdigest();key=(root,relative.casefold())
        if key in table:assert table[key]['sha256']==before,('Guarded target changed',relative)
        else:
            # The native screen is an existing official resource entering the
            # release guard set for the first time. Bind exactly the inspected,
            # tested source; never treat arbitrary unregistered files as writable.
            assert before is None or (root=='client' and any(relative==client_relative(n) and before==build[n]['source_sha256'] for n in NAMES)),('Unregistered target',relative)
        table[key]=dict(root=root,relative=relative,sha256=after);entries.append(dict(root=root,relative=relative,target=target,before=before,after=after,data=data))
    comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='lineup-enhance-v5',native_status='PENDING'))
    policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
    if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
    mb=body(dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_path))
    rb=body(dict(status='INSTALLED_LINEUP_ENHANCE_V5',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
    for relative,data in ((MANIFEST,mb),(RECEIPT,rb)):
        target=S/relative;assert not target.exists();entries.append(dict(root='server',relative=relative,target=target,before=None,after=hashlib.sha256(data).hexdigest(),data=data))
    entries.sort(key=lambda e:e['relative']=='play-local.bat')
    return dict(entries=entries,revision=revision,parent=parent_path,old_play_sha256=sha(S/'play-local.bat'))

def commit(entries,backup,verify,guard,fail_after=None,hook=None):
    backup.mkdir(parents=True,exist_ok=False);done=[]
    journal=[{k:str(v) if isinstance(v,Path) else v for k,v in e.items() if k!='data'} for e in entries]
    for i,e in enumerate(entries):
        assert (sha(e['target']) if e['target'].exists() else None)==e['before']
        if e['before'] is not None:shutil.copyfile(e['target'],backup/str(i))
    write(backup/'transaction.json',dict(status='PREPARED',files=journal))
    try:
        for i,e in enumerate(entries):
            guard()
            if hook:hook(i,e)
            assert (sha(e['target']) if e['target'].exists() else None)==e['before'],'Concurrent target change'
            release.atomic(e['target'],e['data']);done.append(i)
            if fail_after==i+1:raise OSError('Injected write failure')
        verify();write(backup/'transaction.json',dict(status='INSTALLED',files=journal))
    except BaseException:
        retained=[]
        for i in reversed(done):
            e=entries[i]
            if not e['target'].exists() or sha(e['target'])!=e['after']:retained.append(str(e['target']));continue
            if e['before'] is None:e['target'].unlink()
            else:release.atomic(e['target'],(backup/str(i)).read_bytes())
        write(backup/'transaction.json',dict(status='ROLLED_BACK',files=journal,later_changes_retained=retained));raise

def business(st):return {k:v for k,v in st.items() if k!='market_simulation'}
def main():
    if game_active():return deferred()
    with release.locks(S,'lineup-enhance-v5'):
        if game_active():return deferred()
        coord=read(W.parent/'coordination-current.json');assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer')
        p=plan()
        if game_active():return deferred()
        snapshot=W/'fresh-install-snapshot'/p['revision'];snapshot.mkdir(parents=True)
        for name in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/name,snapshot/name)
        before=business(read(snapshot/'state.json'))
        protected={str(S/'gamedata'/n):sha(S/'gamedata'/n) for n in ('shop.json','enhancement_rates.json','market-supply-config.json','npc-market-seed.json.gz')}
        for relative in ('patches/TeamManagementPlayerEnhancementTabPage.big','hot_updates/active.json','http_config.py','enhancement_protection40.py','enhancement_progression.py'):protected[str(S/relative)]=sha(S/relative)
        backup=S/'backups'/p['revision']
        def verify():
            release.load(S/SELF,'remember_installed').preflight(S,C)
            for path,h in protected.items():assert sha(path)==h,('Protected data changed',path)
            assert business(read(S/'gamedata/state.json'))==before,'Preserve new progress; never restore old state'
        commit(p['entries'],backup,verify,idle)
        result=dict(status='INSTALLED_CLIENT_UI_NATIVE_PENDING',revision=p['revision'],backup=str(backup),
            preflight=release.load(S/SELF,'remember_final').preflight(S,C),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),
            composition_api='compose_manifest(server=None,client=None)',files={str(path):sha(path) for path in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat')},
            client_files={str(client_target(n)):sha(client_target(n)) for n in NAMES},protected=protected,
            service_actions=False,services_restarted=False,state_shop_written=False,business_assets_preserved=True,native_verified=False,match_verified=False,
            client_replay=str(W/'client-tests.json'),stack_checks=str(W/'client-tests.json'))
        write(W/'installed-handback.json',result)
        descriptor=read(W.parent/'root-current-top.json');descriptor.update(result,observed_at=datetime.datetime.now().astimezone().isoformat(),handoff=str(W/'installed-handback.json'))
        write(W.parent/'root-current-top.json',descriptor)
    return result
if __name__=='__main__':print(json.dumps(main(),ensure_ascii=True))
