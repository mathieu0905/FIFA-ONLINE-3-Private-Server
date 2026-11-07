"""Single official transaction. No writes/restarts while the game is running."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,re,shutil,socket,subprocess,sys,time,uuid
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(S))
import hot_update_release as release
SELF='patches/enhancement_capped_preflight.py'
MANIFEST='patches/enhancement-capped-installed.json'
RECEIPT='patches/enhancement-capped-receipt.json'
sha=release.sha;body=release.body;load=release.load
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):release.atomic(Path(p),body(v))
def env():
    e=dict(os.environ);e['PSModulePath']=r'C:\Windows\System32\WindowsPowerShell\v1.0\Modules;C:\Program Files\WindowsPowerShell\Modules';return e
def game_running():
    return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9};exit 0'],env=env(),creationflags=subprocess.CREATE_NO_WINDOW).returncode!=0
def assert_idle():
    if game_running():raise RuntimeError('更新已延后，当前游戏继续运行')
def listening():
    ports=[]
    for port in (443,8088,28002):
        try:
            with socket.create_connection(('127.0.0.1',port),.3):ports.append(port)
        except OSError:pass
    return ports
def defer():
    result=dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_files_written=False,services_restarted=False,build=str(R/'build.json'),tests=str(R/'tests.json'))
    write(R/'deferred.json',result);print(json.dumps(result,ensure_ascii=False));return result
def fresh():
    b=read(R/'build.json');t=read(R/'tests.json')
    assert t['status']=='PASS' and t['matrix_cases']==3040
    assert t['tested_outputs']==b['outputs'],'Retest edited development files'
    assert t['host_sha256']==sha(S/'http_config.py'),'Host changed; rerun tests'
    assert t['hot_revision']==read(S/'hot_updates/active.json')['revision'],'Retest current hot package'
    for rel,h in b['outputs'].items():assert sha(R/rel)==h,('Development output changed',rel)
    for rel,h in b['baseline'].items():assert sha(S/rel)==h,('Rebase on latest formal file',rel)
    return b
def plan():
    b=fresh();play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1
    parentrel=matches[0].decode().replace('\\','/');assert parentrel!=SELF
    parent=load(S/parentrel,'capped_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C))
    table={(g['root'],g['relative'].replace('\\','/').casefold()):g for g in comp['guards']};assert len(table)==len(comp['guards'])
    code=(S/parentrel).read_text('utf8')
    for old,new in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_ENHANCEMENT_CAPPED'),(prior['status'],'ENHANCEMENT_CAPPED_PREFLIGHT_PASS')):code=code.replace(old,new)
    compile(code,SELF,'exec')
    revision='enhancement-capped-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    doc='docs/工程经验与修改边界.txt'
    note=('\n\nFO3-ENHANCEMENT-CAPPED（2026-11-07，'+revision+'，原生/比赛PENDING）\n'
        '按主卡当前等级1..19，同级材料成功率及所有叠加最终上限为90/85/75/65/55/45/38/32/28/25/20/15/12/10/8/6/5/4/3%。材料低于主卡1/3、2/3、同级及同级以上分别取上限35/50/75/100%；+0不升级。所有等级ES相对+10%，铜银金道具相对+5/10/15%，比例相加，不突破同级上限；已达上限不消耗ES/加成道具；常驻概率活动关闭。保护仍收主卡尝试前身价40%替代普通费，失败保级、耗材，失败ES奖励和原有恢复权益保留。\n'
        '估值改为最低预期EP生产成本：V(g+1)=V(g)+[V(m)+手续费+(1-p)*(V(g)-V(失败等级))]/p，在所有1..g材料及可用保护/普通策略中取最小值；保护无重做损耗。包含普通2%且至少1000EP手续费及40%保护费，每级上取整。以持久市场当前+1价格为起点，不重新初始化市场数据库。无ES/道具补贴假设；原有5.6e15显示安全上限可能使高等级封顶，不宣称等于无界真实预期成本。原card_price商城/奖励锚不改，不改已有卡包售价/概率、挂单或历史交易。\n'
        '强化函数和市场闭包超出现有ABI2热包范围；游玩中安装器在任何正式写入或停服前延期，不触碰游戏GUI，不reload宿主。仅游戏自然关闭时共同双锁、最新父层完整guards/receipt policies、备份/CAS、新鲜state/shop快照安装；独立player_import检查保留。回退仅自己的文件后版本，不恢复存档。证据D:/fifaol3/enhancement-capped。\n').encode('utf8')
    payload={rel:(R/rel).read_bytes() for rel in b['outputs']}
    payload.update({SELF:code.encode('utf8'),doc:(S/doc).read_bytes()+note,'play-local.bat':play.replace(matches[0],SELF.replace('/','\\').encode())})
    entries=[]
    for rel,data in payload.items():
        target=S/rel;before=sha(target) if target.exists() else None;after=hashlib.sha256(data).hexdigest();key=('server',rel.casefold())
        # This is an existing online mutable configuration, never freeze it by a guard.
        if rel=='gamedata/enhancement_rates.json':assert key not in table,'Mutable rate configuration unexpectedly guarded'
        else:
            if key in table:assert table[key]['sha256']==before,('Guard changed',rel)
            else:assert before is None,('Unregistered target',rel)
            table[key]=dict(root='server',relative=rel,sha256=after)
        entries.append(dict(relative=rel,target=target,data=data,before=before,after=after))
    comp.update(guards=list(table.values()),files_verified=False)
    comp.setdefault('ancestry',[]).append(dict(layer='enhancement-capped',native_status='PENDING'))
    policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
    if not any(p['root']==policy['root'] and p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
    mb=body(dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parentrel))
    rb=body(dict(status='INSTALLED_ENHANCEMENT_CAPPED',revision=revision,manifest_sha256=hashlib.sha256(mb).hexdigest(),state_shop_replaced=False,native_status='PENDING'))
    for rel,data in ((MANIFEST,mb),(RECEIPT,rb)):
        assert not (S/rel).exists();entries.append(dict(relative=rel,target=S/rel,data=data,before=None,after=hashlib.sha256(data).hexdigest()))
    entries.sort(key=lambda e:e['relative']=='play-local.bat')
    return dict(entries=entries,revision=revision,parent=parentrel,parent_hash=sha(S/parentrel),play_hash=sha(S/'play-local.bat'))
def commit(p,protected):
    backup=S/'backups'/p['revision'];backup.mkdir(exist_ok=False);entries=p['entries']
    journal=[{k:str(v) if isinstance(v,Path) else v for k,v in e.items() if k!='data'} for e in entries]
    for i,e in enumerate(entries):
        assert (sha(e['target']) if e['target'].exists() else None)==e['before']
        if e['before'] is not None:shutil.copyfile(e['target'],backup/str(i))
    write(backup/'transaction.json',dict(status='PREPARED',files=journal));done=[]
    try:
        for i,e in enumerate(entries):
            assert_idle()
            assert (sha(e['target']) if e['target'].exists() else None)==e['before'],'Concurrent file edit'
            release.atomic(e['target'],e['data']);done.append(i)
        check=load(S/SELF,'capped_final').preflight(S,C)
        for path,h in protected.items():assert sha(path)==h,('Protected file changed',path)
        write(backup/'transaction.json',dict(status='INSTALLED',files=journal))
        return backup,check
    except BaseException:
        retained=[]
        for i in reversed(done):
            e=entries[i]
            if not e['target'].exists() or sha(e['target'])!=e['after']:retained.append(str(e['target']));continue
            if e['before'] is None:e['target'].unlink()
            else:release.atomic(e['target'],(backup/str(i)).read_bytes())
        write(backup/'transaction.json',dict(status='ROLLED_BACK',later_changes_retained=retained,files=journal));raise
def restart():
    assert_idle();e=env();e.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
    with (S/'captures/enhancement-capped-restart.log').open('ab') as log:
        subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=e,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','30'],cwd=S,env=e,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def main():
    if game_running():return defer()
    with release.locks(S,'enhancement-capped'):
        if game_running():return defer()
        coord=read(R.parent/'coordination-current.json');assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer'),'Coordinate existing installation window first'
        p=plan()
        if game_running():return defer()
        running=bool(listening());stopped=False
        try:
            if running:
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
                deadline=time.monotonic()+15
                while listening():
                    if time.monotonic()>deadline:raise RuntimeError('Old services still listening; abort without formal writes')
                    time.sleep(.2)
            assert_idle();fresh();assert sha(S/p['parent'])==p['parent_hash'] and sha(S/'play-local.bat')==p['play_hash']
            snap=R/'fresh-stop-snapshot'/p['revision'];snap.mkdir(parents=True)
            for name in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/name,snap/name)
            protected={str(path):sha(path) for path in (S/'gamedata').glob('*.json') if path.name!='enhancement_rates.json'}
            protected[str(S/'hot_updates/active.json')]=sha(S/'hot_updates/active.json')
            protected[str(S/'gamedata/npc-market-prices.sqlite')]=sha(S/'gamedata/npc-market-prices.sqlite')
            backup,check=commit(p,protected)
            result=dict(status='INSTALLED_NATIVE_PENDING',revision=p['revision'],backup=str(backup),preflight=check,
                top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',
                files={str(path):sha(path) for path in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat')},
                protected=protected,state_shop_written=False,native_verified=False,match_verified=False,hot_revision=read(S/'hot_updates/active.json')['revision'])
            write(R/'installed-handback.json',result)
        finally:
            if running and stopped and not game_running():restart()
        result['services_restored']=listening()==[443,8088,28002] if running else 'previously_stopped'
        result['services_action']='Restarted only after game was observed closed' if running else 'Previously stopped; not started'
        write(R/'installed-handback.json',result)
        descriptor=read(R.parent/'root-current-top.json');descriptor.update(result,observed_at=datetime.datetime.now().astimezone().isoformat(),handoff=str(R/'installed-handback.json'))
        write(R.parent/'root-current-top.json',descriptor)
        print(json.dumps(result,ensure_ascii=True))
        return result
if __name__=='__main__':main()
