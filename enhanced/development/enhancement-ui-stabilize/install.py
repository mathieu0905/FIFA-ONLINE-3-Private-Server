"""Official client-resource transaction; never stops services or changes assets."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(S));import hot_update_release as release
SELF='patches/enhancement_ui_stabilize_preflight.py';MANIFEST='patches/enhancement-ui-stabilize-installed.json';RECEIPT='patches/enhancement-ui-stabilize-receipt.json'
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
    for old,new in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_ENHANCEMENT_UI_STABILIZE'),(prior['status'],'ENHANCEMENT_UI_STABILIZE_PREFLIGHT_PASS')):helper=helper.replace(old,new)
    compile(helper,SELF,'exec');revision='enhancement-ui-stabilize-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    note='\n\nFO3-ENHANCEMENT-UI-STABILIZE（2026-11-07，原生入页仍待验收）\n16:55:40 PE2STATICVALUES后无preview；用户截图证明上一轮入口修正仍失败，不能称已修复。撤下当前聊天新增的选项记忆/双卡自动重选实现，Tab完整回到15:41成功强化的520499d9 UI；Popup回到f6c65102基础，仅保留method33的原生确认后免额外保护费弹窗。没有新增类成员/词法闭包；保留原独立保护、数值概率及字体修正。概率/身价/40%双卡保护后端均不回退。选项记忆和双卡自动重选暂不可用；今后须完成原生加载验证才重新交付，不以自制VM通过代替。\n所有非ABC资源及其它BIG成员与当前版本逐字节一致，原生确认回放验证有签名非阻塞报价仅发一次PUT，仍携带新鲜token；异常报价不绕过收费确认。根因未确证，当前只是撤销回归范围内改动，不能宣称实机已恢复。安装沿用最新父层全guards/receipt policies、双锁、备份/CAS；真实state/shop不写入/不恢复、不停服/不操作GUI，游戏运行则延期。证据D:/fifaol3/enhancement-ui-stabilize。\n'.encode('utf8')
    payload=[]
    for name in NAMES:
        if sha(W/(name+'.big'))==sha(C/'data/ui'/(name+'.big')):continue
        data=(W/(name+'.big')).read_bytes();payload.extend([('client','data/ui/'+name+'.big',data),('server','patches/'+name+'.big',data)])
    payload.extend([('server',SELF,helper.encode('utf8')),('server',DOC,(S/DOC).read_bytes()+note),('server','play-local.bat',play.replace(names[0],SELF.replace('/','\\').encode()))])
    entries=[]
    for root,relative,data in payload:
        target=(S if root=='server' else C)/relative;before=sha(target) if target.exists() else None;after=hashlib.sha256(data).hexdigest();key=(root,relative.casefold())
        if key in table:assert table[key]['sha256']==before,('Guarded target changed',relative)
        else:assert before is None,('Unregistered target',relative)
        table[key]=dict(root=root,relative=relative,sha256=after);entries.append(dict(root=root,relative=relative,target=target,before=before,after=after,data=data))
    comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='enhancement-ui-stabilize',native_status='PENDING'))
    policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
    if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
    mb=body(dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_path))
    rb=body(dict(status='INSTALLED_ENHANCEMENT_UI_STABILIZE',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
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
    with release.locks(S,'enhancement-ui-stabilize'):
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
