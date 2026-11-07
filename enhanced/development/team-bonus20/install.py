"""Fresh-parent, protected-stop transaction for the authorized team-color extension."""
from pathlib import Path
from contextlib import contextmanager
import datetime, hashlib, importlib.util, json, os, re, ssl, subprocess, sys, time, urllib.request
from prepare import transform
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
S=Path(r'D:\FO3ID\server'); C=Path(r'D:\FO3ID\32795')
PY=S/'.venv/Scripts/python.exe'
HIDDEN=subprocess.CREATE_NO_WINDOW
DOC='docs/工程经验与修改边界.txt'
DOC_ENTRY='''

FO3-TEAM-BONUS20-001（2026-11-07，team-bonus20-moments-v1）
新增强化+11..+20套，11名首发全部达到门槛时全属性+8..+17，只取最佳强化套，原低阶规则不变。
84赛季传奇时刻首发去重计数：3..5人额外+2，6..8人额外+3，9..10人额外+4，11人额外+5，仅作用于传奇时刻球员。
错误模式：作为普通special套会与原最佳俱乐部/国家/赛季套互斥，不符合额外叠加。本层复用当前正式Module已有feature分类、选择、应用、清理路径，服务摘要按base/grade/feature独立取最佳，无客户端BIG变更。
离线50项包括全部人数边界、强化1..20与混合首发、替补/重复身份排除、原套装不变、原生协议与正式DB只读身份归属；不写真实测试卡/余额或state/shop。
用户已结束游戏并明确授权本次安装。沿用最新父层全部guards/receipt policies、共同双锁、正式保护停服、新快照/备份/CAS、play最后切换；只改HTTP五个球队加成函数及相关常量。
正式运行时验证与服务恢复见D:/fifaol3/team-bonus20/installed-handback.json。离线/接口通过不代表原生游戏、半场、换人或比赛通过，后者仍PENDING；本轮无GUI操作。
'''

def encoded(x): return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def digest(b): return hashlib.sha256(b).hexdigest()
def sha(p): return digest(Path(p).read_bytes())
def load(p,name):
    sp=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
def run(args,**kw):
    p=subprocess.run([str(a) for a in args],cwd=S,creationflags=HIDDEN,capture_output=True,text=True,encoding='utf8',errors='replace',**kw)
    if p.returncode: raise RuntimeError('Command failed: '+str(args)+'\n'+p.stdout+p.stderr)
    return p.stdout
def closed():
    p=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],creationflags=HIDDEN)
    if p.returncode: raise RuntimeError('更新已延后，当前游戏继续运行')
@contextmanager
def locks():
    owned=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            path=S/name; fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_BINARY',0))
            token=encoded(dict(pid=os.getpid(),task='team-bonus20',at=datetime.datetime.now().astimezone().isoformat()))
            owned.append((path,fd,token)); os.write(fd,token); os.fsync(fd)
        yield
    finally:
        for path,fd,token in reversed(owned):
            os.close(fd)
            if path.exists() and path.read_bytes()==token: path.unlink()
def cas(path,before,after):
    actual=lambda:path.read_bytes() if path.exists() else None
    if actual()!=before: raise RuntimeError('Concurrent change retained: '+str(path))
    if after is None: path.unlink(); return
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.team-bonus-'+str(os.getpid())+'.tmp')
    try:
        with tmp.open('xb') as f: f.write(after); f.flush(); os.fsync(f.fileno())
        if actual()!=before: raise RuntimeError('Concurrent change before replace: '+str(path))
        os.replace(tmp,path)
    finally:
        if tmp.exists(): tmp.unlink()
def plan():
    play=(S/'play-local.bat').read_bytes()
    found=re.findall(rb'(?m)^\.venv\\Scripts\\python\.exe (patches\\\w+_preflight\.py)\r?$',play)
    if len(found)!=1: raise RuntimeError('Ambiguous latest parent gate')
    parent_rel=found[0].decode().replace('\\','/')
    parent=load(S/parent_rel,'team_bonus_parent')
    prior=parent.preflight(S,C); composition=parent.compose_manifest(S,C)
    validator=load(S/'patches/startup_market_preflight.py','team_bonus_validator')
    validator.verify_manifest(composition,S,C)
    guards=validator.table(composition['guards'])
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    revision='team-bonus20-'+stamp
    gate='patches/team_bonus20_'+stamp+'_preflight.py'
    manifest='patches/'+revision+'-installed.json'; receipt='patches/'+revision+'-receipt.json'
    old_receipt=json.loads((S/parent.RECEIPT).read_text('utf-8-sig'))
    helper=(S/parent_rel).read_text('utf8')
    for old,new in ((parent.MANIFEST,manifest),(parent.RECEIPT,receipt),(parent.SELF,gate),
                    (old_receipt['status'],'INSTALLED_TEAM_BONUS20'),(prior['status'],'TEAM_BONUS20_PREFLIGHT_PASS')):
        if old not in helper: raise RuntimeError('Fresh parent helper changed: '+old)
        helper=helper.replace(old,new)
    compile(helper,gate,'exec')
    http=(S/'http_config.py').read_bytes()
    proposed=transform(http.decode('utf8')).encode('utf8')
    tests=json.loads((R/'tests.json').read_text('utf8'))
    if tests['status']!='PASS' or tests['case_count']!=50 or tests['baseline_sha256']!=digest(http) or tests['proposed_sha256']!=digest(proposed) or tests['transformer_sha256']!=sha(R/'prepare.py'):
        raise RuntimeError('Fresh reviewed source/tests mismatch')
    doc=(S/DOC).read_bytes()
    if b'FO3-TEAM-BONUS20-001' in doc: raise RuntimeError('Already installed ledger entry')
    payloads={'http_config.py':proposed,DOC:doc+DOC_ENTRY.encode('utf8'),gate:helper.encode('utf8'),
              'play-local.bat':play.replace(found[0],gate.replace('/','\\').encode())}
    # Parent receipt remains immutable, including its installation fields.
    policies=list(composition.get('receipt_policies',[]))
    policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in old_receipt.items() if k!='native_status'})
    if not any(p.get('root')=='server' and p.get('relative')==parent.RECEIPT for p in policies): policies.append(policy)
    for rel,body in payloads.items():
        key=('server',rel.casefold())
        if key in guards and sha(S/rel)!=guards[key]['sha256']: raise RuntimeError('Fresh guard mismatch '+rel)
        if rel==gate and (S/rel).exists(): raise RuntimeError('Immutable gate exists')
        guards[key]=dict(root='server',relative=rel,sha256=digest(body))
    composition.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False)
    composition.setdefault('ancestry',[]).append(dict(layer='team-bonus20-moments-v1',revision=revision,native_status='PENDING'))
    m=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],composition=composition,
           parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel))
    payloads[manifest]=encoded(m)
    payloads[receipt]=encoded(dict(status='INSTALLED_TEAM_BONUS20',revision=revision,manifest_sha256=digest(payloads[manifest]),state_shop_replaced=False,native_status='PENDING'))
    before={rel:(S/rel).read_bytes() if (S/rel).exists() else None for rel in payloads}
    return dict(payloads=payloads,before=before,parent=parent_rel,parent_hash=sha(S/parent_rel),revision=revision,gate=gate,manifest=manifest,receipt=receipt,prior=prior)
def stop():
    closed()
    run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1'])
    for _ in range(25):
        p=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-NetTCPConnection -State Listen -LocalPort 443,8088,28002 -ErrorAction SilentlyContinue){exit 9}'],creationflags=HIDDEN)
        if p.returncode==0: return
        time.sleep(.2)
    raise RuntimeError('Protected stop incomplete; no formal writes or duplicate starts allowed')
def start():
    closed()
    env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',PYTHONIOENCODING='utf-8')
    with (R/'service.stdout.log').open('ab') as out,(R/'service.stderr.log').open('ab') as err:
        p=subprocess.Popen([str(PY),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=HIDDEN)
    ready=run([PY,'-B',S/'wait_services.py','--timeout','30'],env=env)
    return p.pid,ready.strip()
def get(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    with opener.open(url,timeout=20) as response: return json.load(response)
def hot_status(): return get('http://127.0.0.1:8088/api/hot_update_status')
def apply(p,snapshot):
    closed()
    if sha(S/p['parent'])!=p['parent_hash']: raise RuntimeError('Parent changed before commit')
    backup=S/'backups'/p['revision']; backup.mkdir(parents=True)
    for rel,body in p['before'].items():
        if body is not None:
            target=backup/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(body)
    for name,body in snapshot.items(): (backup/('snapshot-'+name)).write_bytes(body)
    committed=[]
    try:
        for rel in [x for x in p['payloads'] if x!='play-local.bat']+['play-local.bat']:
            closed(); cas(S/rel,p['before'][rel],p['payloads'][rel]); committed.append(rel)
        check=load(S/p['gate'],'team_bonus_installed_gate').preflight(S,C)
        run([PY,'-B',R/'test.py','--installed'])
        player=run([PY,'-B',S/'tools/player_import/check.py'])
        for name,body in snapshot.items():
            if (S/'gamedata'/name).read_bytes()!=body: raise RuntimeError('Stopped live asset file changed; will not restore assets')
    except BaseException:
        conflicts=[]
        for rel in reversed(committed):
            try: cas(S/rel,p['payloads'][rel],p['before'][rel])
            except RuntimeError: conflicts.append(rel)
        if conflicts: raise RuntimeError('Later legitimate changes retained: '+repr(conflicts))
        raise
    return dict(status='INSTALLED',revision=p['revision'],backup=str(backup),preflight=check,player_import=player.strip(),
                top_preflight=str(S/p['gate']),top_manifest=str(S/p['manifest']),top_receipt=str(S/p['receipt']),
                composition_api='compose_manifest(server=None,client=None)',state_shop_written=False,native_verified=False)
def finish(p,result,snapshot,old_hot):
    hot=hot_status(); deadline=time.monotonic()+20
    while (hot.get('revision')!=old_hot['revision'] or not hot.get('watcher_running')) and time.monotonic()<deadline:
        time.sleep(.2); hot=hot_status()
    assert hot['revision']==old_hot['revision'] and hot['routes']==old_hot['routes'] and hot['error'] is None and hot['watcher_running']
    data=get('https://127.0.0.1/static/info/teamcolor'); colors={c['teamcolorid']:c for c in data['teamColors']}
    for g in range(11,21):
        c=colors[10100+g]; assert c['grade']==g and c['type']=='grade'
        assert c['boostgroups']==[dict(count_min=11,count_max=11,boosts=[dict(type='ovr',amount=g-3)])]
    c=colors[60084]; assert c['type']=='feature' and c['teamid']=='60084'
    assert [(x['count_min'],x['count_max'],x['boosts'][0]['amount']) for x in c['boostgroups']]==[(3,5,2),(6,8,3),(9,10,4),(11,11,5)]
    assert '60084' in data['teamColorSpecials']
    with locks():
        if p['payloads']['play-local.bat']!=(S/'play-local.bat').read_bytes(): raise RuntimeError('Newer legal top retained; do not overwrite handback')
        check=load(S/p['gate'],'team_bonus_final_gate').preflight(S,C)
        before=json.loads(snapshot['state.json']); after=json.loads((S/'gamedata/state.json').read_bytes())
        business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
        assert business(before)==business(after), 'New business progress retained; never restore state'
        assert (S/'gamedata/shop.json').read_bytes()==snapshot['shop.json']
        files={str(S/rel):sha(S/rel) for rel in (p['gate'],p['manifest'],p['receipt'],'play-local.bat','http_config.py')}
        result.update(status='INSTALLED_AND_RUNTIME_ACTIVE',runtime_active=True,services_restored=True,services_restarted=True,
            preflight=check,files=files,hot_update_status=hot,native_game_verified=False,match_verified=False,
            validation=dict(memory_cases=50,installed_source_checked=True,static_teamcolor_endpoint=True,player_import=True,state_business_exact=True,shop_exact=True,game_gui_used=False),
            runtime_rules=dict(grade_tiers={g:g-3 for g in range(11,21)},moments_tiers=[[3,5,2],[6,8,3],[9,10,4],[11,11,5]],owned_moments_members=len(data['teamColorSpecials']['60084'])),
            observed_at=datetime.datetime.now().astimezone().isoformat(),handoff=str(R/'installed-handback.json'))
        (R/'live-teamcolor.json').write_bytes(encoded(data))
        (R/'installed-handback.json').write_bytes(encoded(result))
        top=Path(r'D:\fifaol3\root-current-top.json'); top_before=top.read_bytes(); cas(top,top_before,encoded(result))
    print(json.dumps(result,ensure_ascii=True))
def main():
    closed()
    transaction=json.loads((R/'transaction-tests.json').read_text('utf8'))
    if transaction['status']!='PASS' or transaction['installer_sha256']!=sha(R/'install.py'):
        raise RuntimeError('Installer transaction regression is stale')
    with locks():
        closed(); run([PY,'-B',R/'test.py'])
        p=plan(); (R/'plan.json').write_bytes(encoded({k:v for k,v in p.items() if k not in ('payloads','before')}))
        (R/'baseline-http.py').write_bytes(p['before']['http_config.py'])
        old_hot=hot_status()
        stop() # If refused/incomplete, no write or start follows.
        snapshot={name:(S/'gamedata'/name).read_bytes() for name in ('state.json','shop.json')}
        error=None
        try: result=apply(p,snapshot)
        except BaseException as exc: error=exc
        launcher,ready=start()
        if error: raise error
        result.update(launcher_pid=launcher,readiness=ready)
    finish(p,result,snapshot,old_hot)
if __name__=='__main__': main()
