"""Official client-resource transaction; never stops services or changes assets."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(S));import hot_update_release as release
SELF='patches/lineup_enhance_v3_preflight.py';MANIFEST='patches/lineup-enhance-v3-installed.json';RECEIPT='patches/lineup-enhance-v3-receipt.json'
DOC='docs/工程经验与修改边界.txt';NAMES=('components-ScrollingList','TeamManagementPlayerEnhancementTabPage','TeamManagementScreen')
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
        else:assert name=='TeamManagementScreen'
    return build
def plan():
    build=check_outputs();play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches[\\/][A-Za-z0-9_]+_preflight\.py',play);assert len(names)==1
    assert b'tools\\player_import\\check.py' in play
    parent_path=names[0].decode().replace('\\','/');assert parent_path!=SELF
    parent=release.load(S/parent_path,'remember_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C))
    table={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']};assert len(table)==len(comp['guards'])
    helper=(S/parent_path).read_text('utf8')
    for old,new in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_LINEUP_ENHANCE_V3'),(prior['status'],'LINEUP_ENHANCE_V3_PREFLIGHT_PASS')):helper=helper.replace(old,new)
    helper=helper.replace(' if not required<=seen:'," required.update({('client','data/ui/components/scrollinglist.big'),('server','patches/scrollinglist.big'),('client','data/ui/teammanagementscreen.big'),('server','patches/teammanagementscreen.big')})\n if not required<=seen:")
    compile(helper,SELF,'exec');revision='lineup-enhance-v3-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    note='\n\nFO3-LINEUP-ENHANCE-V3 (2026-11-07, runtime not verified)\n用户反馈第二版按钮丑且进入强化页后卡死；截图为空的强化页面，服务日志22:12:08 PE2STATICVALUES、22:12:51 CLIENT_CRASH，不能证明唯一根因。用户明确禁止游戏GUI操作，只允许继续静态排查，本次不启动/操作客户端。\n视觉静态证据已提取正式Button DDS原生像素：搜索/解锁使用64x37胶囊，原第二版PlayerGrowthIncreaseButton是25x25方形加号且还带额外图层，整体拉伸属于错误选型。第三版采用原生空胶囊TransferMarketRollOverButton固定64x37，在内部用代码绘制与原图标近似色的向上箭头，不再读取其它复合控件的动态width/height；搜索/锁/解锁原坐标不变，额外按钮仍按原60px间距放置。\n强化BIG撤下本聊天全部新增ABC方法、traits、常量池及初始化/库存/逐帧钩子；当前输入仅含本聊天对该ABC的改动已经逐字节核对，最小块恢复后整个强化BIG SHA为cd8f7b2d8dd747eb617b6b64b93631602a99ad77bdead962403b690fbbdde314，与加快捷键前的正式稳定资源完全一致。其余正式最新文件和所有后续合法改动保留，不回退存档或旧state/shop。\n导航与一次请求只放在TeamManagementScreen。一次导航后等待原生DataProvider非空、精确_id/spid/grade、原生行renderer就绪且两帧稳定；仅通过原生ListEvent(itemClick)分发给原onClickListItem，不直接调用/注入强化私有方法或改玩家对象。先移除请求与监听，再原生clear selected player和原生点击；材料不自动选择。未就绪最多30秒或600帧，逐帧有界检查，无同步轮询死循环；退出屏幕撤下监听。\n回归执行新增字节码、原生ListEvent构造和原生onClickListItem，覆盖15种加载/空列表/renderer/过期/卡变化失败状态、两帧就绪、一次导航、原生资格拒绝和完整强化资源精确恢复。回放与栈流通过不等于原生类型验证或卡死消除；crash_fixed_proven=false，GUI/native/match验证均未做。安装fresh最新父层和全部guards/receipt policies，双锁、备份/CAS；不启停服务，不写真实资产。\n'.encode('utf8')
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
            assert before is None or (root=='client' and relative=='data/ui/TeamManagementScreen.big' and before==build['TeamManagementScreen']['source_sha256']),('Unregistered target',relative)
        table[key]=dict(root=root,relative=relative,sha256=after);entries.append(dict(root=root,relative=relative,target=target,before=before,after=after,data=data))
    comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='lineup-enhance-v3',native_status='PENDING'))
    policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
    if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
    mb=body(dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_path))
    rb=body(dict(status='INSTALLED_LINEUP_ENHANCE_V3',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
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
    with release.locks(S,'lineup-enhance-v3'):
        if game_active():return deferred()
        coord=read(W.parent/'coordination-current.json');assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer')
        p=plan()
        if game_active():return deferred()
        snapshot=W/'fresh-install-snapshot'/p['revision'];snapshot.mkdir(parents=True)
        for name in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/name,snapshot/name)
        before=business(read(snapshot/'state.json'))
        protected={str(S/'gamedata'/n):sha(S/'gamedata'/n) for n in ('shop.json','enhancement_rates.json','market-supply-config.json','npc-market-seed.json.gz')}
        for relative in ('hot_updates/active.json','http_config.py','enhancement_protection40.py','enhancement_progression.py'):protected[str(S/relative)]=sha(S/relative)
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
