"""Official client-resource transaction; never stops services or changes assets."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(S));import hot_update_release as release
SELF='patches/enhancement_pair_remember_preflight.py';MANIFEST='patches/enhancement-pair-remember-installed.json';RECEIPT='patches/enhancement-pair-remember-receipt.json'
DOC='docs/工程经验与修改边界.txt';NAMES=('TeamManagementPlayerEnhancementTabPage','TeamManagementPlayerEnhancingPopupScreen')
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
    assert tests['status']=='PASS' and read(W/'stacks.json')['status']=='PASS' and read(W/'install-tests.json')['status']=='PASS'
    for name in NAMES:
        assert sha(W/(name+'.big'))==tests['output_sha256'][name]==build[name]['sha256']
        assert sha(C/'data/ui'/(name+'.big'))==sha(S/'patches'/(name+'.big'))==tests['source_sha256'][name]==build[name]['source_sha256'],'Rebase resource on current official version'
    return build
def plan():
    build=check_outputs();play=(S/'play-local.bat').read_bytes();names=re.findall(rb'patches[\\/][A-Za-z0-9_]+_preflight\.py',play);assert len(names)==1
    assert b'tools\\player_import\\check.py' in play
    parent_path=names[0].decode().replace('\\','/');assert parent_path!=SELF
    parent=release.load(S/parent_path,'remember_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C))
    table={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']};assert len(table)==len(comp['guards'])
    helper=(S/parent_path).read_text('utf8')
    for old,new in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_ENHANCEMENT_PAIR_REMEMBER'),(prior['status'],'ENHANCEMENT_PAIR_REMEMBER_PREFLIGHT_PASS')):helper=helper.replace(old,new)
    compile(helper,SELF,'exec');revision='enhancement-pair-remember-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    note='\n\nFO3-ENHANCEMENT-PAIR-REMEMBER（2026-11-07，原生GUI待验收）\n用户要求保护失败回来后，主卡和副卡也保留选中。基于前一层已安装的保护/券/ES记忆和取消额外收费弹窗，增量给原生确认数据附原控制器回调；仅结果成功返回且success=false、protection.material_kept=true，在原生结果页完成detach后调用一次。取消、错误、普通失败及成功都不恢复。回调在原玩家面板按_id找到当前库存的双方最新对象，核对spid/grade、native availableEnhancePlayer/isPlayerLocked，并拒绝已离开/隐藏页面、缺卡、等级变化或已有人工新选择；不按SPID替换另一实例。调用原生selectTarget及invalidatePlayerList恢复主副顺序、列表勾选和新报价，保留上一层保护/券/ES选项，不自动PUT、不重用旧报价或token。\n两BIG只改三个既有方法并新增一个闭包回调；其余方法及全部旧指令/跳转、traits/signatures、非ABC标签和其它archive成员保持。回放覆盖五次失败恢复、11种过期/缺卡/锁卡/换卡/隐藏页面条件、取消/错误/成功跳过、重复detach仅一次；四方法栈/作用域流通过。静态/回放不等于原生类型验证、GUI或比赛通过。\n游戏运行时正式写入前延期；游戏关闭时共同双锁、备份/CAS、最新父层全部guards/receipt policies及player_import独立检查保留。仅更新双端两UI BIG、doc/新层/play，不重启服务，不写state/shop/测试资产。证据D:/fifaol3/enhancement-pair-remember。\n'.encode('utf8')
    payload=[]
    for name in NAMES:
        data=(W/(name+'.big')).read_bytes();payload.extend([('client','data/ui/'+name+'.big',data),('server','patches/'+name+'.big',data)])
    payload.extend([('server',SELF,helper.encode('utf8')),('server',DOC,(S/DOC).read_bytes()+note),('server','play-local.bat',play.replace(names[0],SELF.replace('/','\\').encode()))])
    entries=[]
    for root,relative,data in payload:
        target=(S if root=='server' else C)/relative;before=sha(target) if target.exists() else None;after=hashlib.sha256(data).hexdigest();key=(root,relative.casefold())
        if key in table:assert table[key]['sha256']==before,('Guarded target changed',relative)
        else:assert before is None,('Unregistered target',relative)
        table[key]=dict(root=root,relative=relative,sha256=after);entries.append(dict(root=root,relative=relative,target=target,before=before,after=after,data=data))
    comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='enhancement-pair-remember',native_status='PENDING'))
    policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
    if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
    mb=body(dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_path))
    rb=body(dict(status='INSTALLED_ENHANCEMENT_PAIR_REMEMBER',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
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
    with release.locks(S,'enhancement-pair-remember'):
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
            client_files={str(C/'data/ui'/(n+'.big')):sha(C/'data/ui'/(n+'.big')) for n in NAMES},protected=protected,
            service_actions=False,services_restarted=False,state_shop_written=False,business_assets_preserved=True,native_verified=False,match_verified=False,
            client_replay=str(W/'client-tests.json'),stack_checks=str(W/'stacks.json'))
        write(W/'installed-handback.json',result)
        descriptor=read(W.parent/'root-current-top.json');descriptor.update(result,observed_at=datetime.datetime.now().astimezone().isoformat(),handoff=str(W/'installed-handback.json'))
        write(W.parent/'root-current-top.json',descriptor)
    return result
if __name__=='__main__':print(json.dumps(main(),ensure_ascii=True))
