"""Direct production club balance install with current guards, CAS and game protection."""
from contextlib import contextmanager
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
import uuid
sys.dont_write_bytecode=True
import prepare

R=prepare.ROOT;S=prepare.SERVER;C=prepare.CLIENT
PY=S/'.venv/Scripts/python.exe'
HIDDEN=subprocess.CREATE_NO_WINDOW
SELF='patches/club_base_balance_20261107_preflight.py'
MANIFEST='patches/club-base-balance-20261107-installed.json'
RECEIPT='patches/club-base-balance-20261107-receipt.json'
EVIDENCE='patches/club-base-balance-20261107-evidence.json.gz'
DOC='docs/工程经验与修改边界.txt' 


def encoded(obj):return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def digest(body):return hashlib.sha256(body).hexdigest()
def run(args,**kwargs):
    result=subprocess.run([str(x) for x in args],cwd=S,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=HIDDEN,env=environment(),**kwargs)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout.strip()
def environment():
    env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    env['PSModulePath']=str(Path(env.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/Modules')+';'+str(Path(env.get('ProgramFiles','C:/Program Files'))/'WindowsPowerShell/Modules')
    return env
def idle():
    result=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],env=environment(),creationflags=HIDDEN)
    return result.returncode==0
def assert_idle():
    if not idle():raise RuntimeError('更新已延后，当前游戏继续运行')


@contextmanager
def locks(server=S):
    owned=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            path=server/name
            body=encoded(dict(pid=os.getpid(),task='club-base-balance',created=datetime.datetime.now().astimezone().isoformat()))
            fd=os.open(path,os.O_EXCL|os.O_CREAT|os.O_WRONLY|getattr(os,'O_BINARY',0))
            owned.append((path,fd,body));os.write(fd,body);os.fsync(fd)
        yield
    finally:
        for path,fd,body in reversed(owned):
            os.close(fd)
            if path.exists() and path.read_bytes()==body:path.unlink()


def atomic(source,target):
    target=Path(target);tmp=target.with_name(target.name+'.club-balance-'+uuid.uuid4().hex)
    try:
        if isinstance(source,Path):shutil.copyfile(source,tmp)
        else:tmp.write_bytes(source)
        os.replace(tmp,target)
    finally:tmp.unlink(missing_ok=True)


def current_hash(path):return prepare.sha(path) if path.exists() else None
def cas(entry):
    if current_hash(entry['target'])!=entry['before']:raise RuntimeError('Concurrent file change: '+str(entry['target']))
    atomic(entry['source'],entry['target'])


def rollback(entries):
    retained=[]
    for entry in reversed(entries):
        target=entry['target']
        if current_hash(target)!=entry['after']:
            retained.append(str(target));continue
        if entry['before'] is None:target.unlink()
        else:atomic(entry['backup'],target)
    return retained


def listening():
    ports=[]
    for port in (443,8088,28002):
        try:
            with socket.create_connection(('127.0.0.1',port),.3):ports.append(port)
        except OSError:pass
    return ports


def get(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    with opener.open(url,timeout=20) as response:return json.load(response)


def commit(plan,snapshot):
    assert_idle()
    backup=S/'backups'/plan['revision'];backup.mkdir(parents=True,exist_ok=False)
    for name,body in snapshot.items():(backup/('fresh-'+name)).write_bytes(body)
    for i,entry in enumerate(plan['entries']):
        if current_hash(entry['target'])!=entry['before']:raise RuntimeError('Target drift before backup')
        entry['backup']=backup/(str(i)+'-'+entry['target'].name)
        if entry['before'] is not None:shutil.copyfile(entry['target'],entry['backup'])
    journal=dict(status='PREPARED',revision=plan['revision'],entries=[{k:str(v) if isinstance(v,Path) else v for k,v in e.items() if k!='source'} for e in plan['entries']],completed=[])
    prepare.write(backup/'transaction.json',journal)
    written=[]
    try:
        if prepare.sha(S/plan['parent'])!=plan['parent_hash']:raise RuntimeError('Parent changed')
        for entry in plan['entries']:
            assert_idle()
            if isinstance(entry['source'],Path) and prepare.sha(entry['source'])!=entry['after']:raise RuntimeError('Build input drift')
            cas(entry);written.append(entry);journal['completed'].append(entry['relative']);prepare.write(backup/'transaction.json',journal)
        proof=prepare.load(S/SELF,'household_installed_gate').preflight(S,C)
        validation=run([PY,'-B',S/'tools/player_import/check.py'])
        run([PY,'-B',R/'test.py','--installed'])
        for name,body in snapshot.items():
            if (S/'gamedata'/name).read_bytes()!=body:raise RuntimeError('Live assets changed while stopped; never restore them')
        journal['status']='INSTALLED';prepare.write(backup/'transaction.json',journal)
        return dict(backup=str(backup),preflight=proof,player_import=json.loads(validation),assets_identical_while_stopped=True)
    except BaseException:
        retained=rollback(written)
        journal.update(status='ROLLBACK_RETAINED_LATER_CHANGES' if retained else 'ROLLED_BACK',retained=retained)
        prepare.write(backup/'transaction.json',journal)
        raise


def restart():
    assert_idle()
    with (R/'service.stdout.log').open('ab') as out,(R/'service.stderr.log').open('ab') as err:
        p=subprocess.Popen([str(PY),'-B','-u',str(S/'start_all.py')],cwd=S,env=environment(),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=HIDDEN)
    ready=run([PY,'-B',S/'wait_services.py','--timeout','30'])
    return p.pid,ready


def main():
    if not idle():
        prepare.write(R/'install-status.json',dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_files_written=False))
        print('更新已延后，当前游戏继续运行');return
    transaction=json.loads((R/'transaction-tests.json').read_text('utf8'))
    if transaction['status']!='PASS' or transaction['installer_sha256']!=prepare.sha(Path(__file__)):
        raise RuntimeError('Transaction regression missing or stale')
    with locks():
        assert_idle()
        plan_data=plan()
        prepare.write(R/'install-plan.json',{k:v for k,v in plan_data.items() if k!='entries'})
        top=R.parent/'root-current-top.json';top_before=top.read_bytes()
        old_hot=get('http://127.0.0.1:8088/api/hot_update_status')
        before_colors=get('https://127.0.0.1/static/info/teamcolor')
        was_running=bool(listening())
        stopped=False
        if was_running:
            assert_idle()
            run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1'])
            deadline=time.monotonic()+15
            while listening():
                if time.monotonic()>deadline:raise RuntimeError('Protected stop incomplete; no formal writes or duplicate starts performed')
                time.sleep(.2)
            stopped=True
        snapshot={name:(S/'gamedata'/name).read_bytes() for name in ('state.json','shop.json')}
        try:
            result=commit(plan_data,snapshot)
        except BaseException:
            if stopped:restart()
            raise
        if not listening():
            result['launcher_pid'],result['readiness']=restart()
        result['services_restarted']=stopped
    # The watcher intentionally waits while a publication lock exists. Release
    # both locks before waiting for its immutable business package to activate.
    finish(plan_data,result,snapshot,old_hot,before_colors,top,top_before)



def plan():
    assert_idle()
    coordination=json.loads((R.parent/'coordination-current.json').read_text('utf8'))
    if coordination.get('current_unhanded_writers') or coordination.get('next_formal_writer'):
        raise RuntimeError('Coordinate with the current formal writer before proceeding')
    tests=json.loads((R/'tests.json').read_text('utf8'))
    original=(S/'http_config.py').read_bytes()
    proposed=prepare.transform(original.decode('utf8')).encode('utf8')
    if (tests['status']!='PASS' or tests['baseline_sha256']!=digest(original) or
        tests['proposed_sha256']!=digest(proposed) or tests['transformer_sha256']!=prepare.sha(R/'prepare.py') or
        tests['test_sha256']!=prepare.sha(R/'test.py')):
        raise RuntimeError('Fresh server differs from tested source; refresh and rerun regression')
    play=(S/'play-local.bat').read_bytes()
    matches=re.findall(rb'patches\\(\w+_preflight\.py)',play)
    if len(matches)!=1:raise RuntimeError('Ambiguous current launcher')
    parent_rel='patches/'+matches[0].decode()
    parent=prepare.load(S/parent_rel,'club_balance_fresh_parent')
    prior=parent.preflight(S,C)
    composition=parent.compose_manifest(S,C)
    verifier=prepare.load(S/'patches/startup_market_preflight.py','club_balance_verifier')
    verifier.verify_manifest(composition,S,C)
    guards={(g['root'],g['relative'].replace('\\','/').casefold()):dict(g) for g in composition['guards']}
    receipt=json.loads((S/parent.RECEIPT).read_text('utf-8-sig'))
    helper=(S/parent_rel).read_text('utf8')
    for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),
                    (receipt['status'],'INSTALLED_CLUB_BASE_BALANCE'),(prior['status'],'CLUB_BASE_BALANCE_PREFLIGHT_PASS')]:
        if old not in helper:raise RuntimeError('Parent contract changed: '+old)
        helper=helper.replace(old,new)
    compile(helper,SELF,'exec')
    revision='club-base-balance-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    note=('\r\n\r\nFO3-CLUB-BASE-BALANCE-20261107\r\n'
        '队套基础：首发4-5人全属性+1、6-7人+3、8-9人+5、10人+7、11人+8；保留原命名球队专项加成。\r\n'
        '按用户最新要求，取消普通赛季额外奖励整项；各卡种统一按球队人数获得基础加成，不创建普通卡额外feature或新成员集。\r\n'
        '保留传奇时刻原属性/模型/专属加成及强化套；本次只改服务端队套定义/普通奖励资格，不写DB/BIG或真实state/shop。'
        '核心队套不在业务热更新范围；游戏运行则延后，正常停服后备份/CAS增量、继承当前全部guards/receipt policies，保护实时资产。'
        '25UCL仅完成来源/覆盖研究，本次未导入卡或模型；新赛季导入仍须原生身份/资源/等级码和完整player_import校验。'
        '临时数据回归及正式接口验证各自记录，不代表客户端实机/比赛验证。证据D:/fifaol3/club-balance-live/。\r\n')
    evidence=gzip.compress(encoded(dict(tests=tests,tooling={n:prepare.sha(R/n) for n in ('prepare.py','test.py','install.py','test_install.py')},
        native_verified=False,match_verified=False)),mtime=0)
    payloads=[('http_config.py',proposed),(DOC,(S/DOC).read_bytes()+note.encode('utf8')),
        (EVIDENCE,evidence),(SELF,helper.encode('utf8')),
        ('play-local.bat',play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode()))]
    for rel,body in payloads:
        key=('server',rel.casefold());target=S/rel
        if key in guards and current_hash(target)!=guards[key]['sha256']:raise RuntimeError('Fresh target changed: '+rel)
        if rel in (SELF,EVIDENCE) and target.exists():raise RuntimeError('Immutable path exists: '+rel)
        guards[key]=dict(root='server',relative=rel,sha256=digest(body))
    policies=list(composition.get('receipt_policies',[]))
    if not any(p['root']=='server' and p['relative']==parent.RECEIPT for p in policies):
        policies.append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in receipt.items() if k!='native_status'}))
    composition.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False)
    composition.setdefault('ancestry',[]).append(dict(layer='club-base-balance',revision=revision,native_status='PENDING'))
    manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=composition['guards'],
        composition=composition,parent_preflight=parent_rel,parent_preflight_sha256=prepare.sha(S/parent_rel),
        evidence=EVIDENCE,native_status='PENDING')
    manifest_bytes=encoded(manifest)
    payloads.extend([(MANIFEST,manifest_bytes),(RECEIPT,encoded(dict(status='INSTALLED_CLUB_BASE_BALANCE',
        revision=revision,manifest_sha256=digest(manifest_bytes),state_shop_replaced=False,native_status='PENDING')))])
    entries=[]
    for rel,body in payloads:
        if rel in (MANIFEST,RECEIPT) and (S/rel).exists():raise RuntimeError('Immutable metadata exists')
        entries.append(dict(root='server',relative=rel,target=S/rel,source=body,before=current_hash(S/rel),after=digest(body)))
    entries.sort(key=lambda e:e['relative']=='play-local.bat')
    return dict(revision=revision,parent=parent_rel,parent_hash=prepare.sha(S/parent_rel),entries=entries,prior=prior)


def finish(plan_data,result,snapshot,old_hot,before_colors,top,top_before):
    deadline=time.monotonic()+25
    while True:
        hot=get('http://127.0.0.1:8088/api/hot_update_status')
        if hot.get('revision')==old_hot['revision'] and hot.get('watcher_running'):break
        if time.monotonic()>deadline:raise RuntimeError('Hot business package did not recover')
        time.sleep(.25)
    if hot['routes']!=old_hot['routes'] or hot['error'] is not None:raise RuntimeError('Business status differs; inspect without reverting assets')
    colors=get('https://127.0.0.1/static/info/teamcolor')
    sys.path.insert(0,str(R))
    import test as regression
    ns=regression.functions((S/'http_config.py').read_text('utf8'),S/'gamedata/fifadb.sqlite')
    actual={c['teamcolorid']:c for c in colors['teamColors']}
    assert len(actual)==len(colors['teamColors'])
    for color in before_colors['teamColors']:
        cid=color['teamcolorid'];expected=dict(color)
        if color['type']=='club':
            named=next((b for c,t,b in ns['TC_NAMED_CLUBS'] if c==cid),None)
            expected['boostgroups']=ns['_tc_boost'](ns['TC_CLUB_GROUPS'],named) if named is not None else ns['TC_CLUB_GROUPS']
        assert actual[cid]==expected,('existing color drift',cid)
    assert len(actual)==len(before_colors['teamColors'])
    assert 'TC_ORDINARY_CLUB_BASE' not in (S/'http_config.py').read_text('utf8')
    state=json.loads((S/'gamedata/state.json').read_bytes());previous=json.loads(snapshot['state.json'])
    business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
    result.update(status='INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING',revision=plan_data['revision'],
        top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),
        composition_api='compose_manifest(server=None,client=None)',
        files={str(S/rel):prepare.sha(S/rel) for rel in (SELF,MANIFEST,RECEIPT,'play-local.bat','http_config.py')},
        services_restored=listening()==[443,8088,28002],hot_update_status=hot,ordinary_club_features=0,ordinary_reward_removed=True,
        state_shop_written=False,shop_equal=(S/'gamedata/shop.json').read_bytes()==snapshot['shop.json'],
        state_business_equal=business(state)==business(previous),later_business_progress_preserved=business(state)!=business(previous),
        club_bonus_values_changed=True,moments_individual_attributes_and_exclusive_feature_unchanged=True,
        GUI_used=False,native_verified=False,match_verified=False,locks_released=True,
        handoff=str(R/'installed-handback.json'),observed_at=datetime.datetime.now().astimezone().isoformat())
    with locks():
        latest_play=(S/'play-local.bat').read_bytes()
        latest_matches=re.findall(rb'patches\\(\w+_preflight\.py)',latest_play)
        if len(latest_matches)!=1:raise RuntimeError('Ambiguous latest launcher during handback')
        latest_rel='patches/'+latest_matches[0].decode()
        latest=prepare.load(S/latest_rel,'club_balance_actual_latest_gate')
        proof=latest.preflight(S,C)
        composition=latest.compose_manifest(S,C)
        prepare.load(S/'patches/startup_market_preflight.py','club_balance_final_verifier').verify_manifest(composition,S,C)
        result.update(top_preflight=str(S/latest_rel),top_manifest=str(S/latest.MANIFEST),top_receipt=str(S/latest.RECEIPT),
            preflight=proof,later_top_preserved=latest_rel!=SELF,
            files={str(S/rel):prepare.sha(S/rel) for rel in (latest_rel,latest.MANIFEST,latest.RECEIPT,'play-local.bat','http_config.py')})
        if top.read_bytes()==top_before:atomic(encoded(result),top)
        else:result['later_top_descriptor_preserved']=True
    prepare.write(R/'installed-handback.json',result)
    prepare.write(R/'install-status.json',dict(status=result['status'],formal_writer=False,handback=result['handoff']))
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
