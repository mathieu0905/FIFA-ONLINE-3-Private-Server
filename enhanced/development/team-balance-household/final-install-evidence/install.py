"""Direct production history install, with current guards, exact own-file CAS and game protection."""
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
SELF='patches/club_household_refresh_20261107_preflight.py'
MANIFEST='patches/club-household-refresh-20261107-installed.json'
RECEIPT='patches/club-household-refresh-20261107-receipt.json'
EVIDENCE='patches/club-household-refresh-20261107-evidence.json.gz'
DOC='docs/工程经验与修改边界.txt'
BUILD=R/'build'
if '--extended' in sys.argv:
    SELF='patches/club_household_refresh_20261107_v2_preflight.py'
    MANIFEST='patches/club-household-refresh-20261107-v2-installed.json'
    RECEIPT='patches/club-household-refresh-20261107-v2-receipt.json'
    EVIDENCE='patches/club-household-refresh-20261107-v2-evidence.json.gz'
    BUILD=R/'build-extended'


def encoded(obj):return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def digest(body):return hashlib.sha256(body).hexdigest()
def run(args,**kwargs):
    result=subprocess.run([str(x) for x in args],cwd=S,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=HIDDEN,env=environment(),**kwargs)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout.strip()
def environment():
    env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',PYTHONIOENCODING='utf-8')
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
            body=encoded(dict(pid=os.getpid(),task='club-household-refresh',created=datetime.datetime.now().astimezone().isoformat()))
            fd=os.open(path,os.O_EXCL|os.O_CREAT|os.O_WRONLY|getattr(os,'O_BINARY',0))
            owned.append((path,fd,body));os.write(fd,body);os.fsync(fd)
        yield
    finally:
        for path,fd,body in reversed(owned):
            os.close(fd)
            if path.exists() and path.read_bytes()==body:path.unlink()


def atomic(source,target):
    target=Path(target);tmp=target.with_name(target.name+'.household-'+uuid.uuid4().hex)
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


def plan():
    assert_idle()
    baseline=json.loads((BUILD/'baseline.json').read_text('utf8'))
    for path,expected in baseline.items():
        if prepare.sha(path)!=expected:raise RuntimeError('Build baseline changed; rebuild against current formal inputs: '+path)
    build=json.loads((BUILD/'build-result.json').read_text('utf8'))
    tests=json.loads((R/'tests.json').read_text('utf8'))
    if build['status']!='BUILT_FOR_DIRECT_INSTALL' or tests['status']!='PASS' or tests['database_sha256']!=build['database_sha256']:
        raise RuntimeError('Missing reviewed build/tests')
    for filename,key in [('fifadb.sqlite','database_sha256'),('data_0.big','big_sha256')]:
        if prepare.sha(BUILD/filename)!=build[key]:raise RuntimeError('Build drift')
    certificate=json.loads((BUILD/'player-import-validation.json').read_text('utf8'))
    if certificate['status']!='PLAYER_IMPORT_FULL_PASS' or certificate['input_hashes']['database']!=build['database_sha256'] or certificate['input_hashes']['archive0']!=build['big_sha256']:
        raise RuntimeError('Full validation certificate does not bind build')
    play=(S/'play-local.bat').read_bytes()
    matches=re.findall(rb'patches\\(\w+_preflight\.py)',play)
    if len(matches)!=1:raise RuntimeError('Ambiguous current launcher')
    parent_rel='patches/'+matches[0].decode()
    parent=prepare.load(S/parent_rel,'household_fresh_parent')
    prior=parent.preflight(S,C)
    composition=parent.compose_manifest(S,C)
    verifier=prepare.load(S/'patches/startup_market_preflight.py','household_composition_verifier')
    verifier.verify_manifest(composition,S,C)
    guards={(x['root'],x['relative'].replace('\\','/').casefold()):dict(x) for x in composition['guards']}
    old_receipt=json.loads((S/parent.RECEIPT).read_text('utf-8-sig'))
    helper=(S/parent_rel).read_text('utf8')
    for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),
                    (old_receipt['status'],'INSTALLED_CLUB_HOUSEHOLD_REFRESH'),(prior['status'],'CLUB_HOUSEHOLD_REFRESH_PREFLIGHT_PASS')]:
        if old not in helper:raise RuntimeError('Fresh parent helper contract changed: '+old)
        helper=helper.replace(old,new)
    compile(helper,SELF,'exec')
    revision='club-household-refresh-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    coverage=json.loads((BUILD/'coverage-report.json').read_text('utf8'))
    marker='FO3-HOUSEHOLD-20261107-VERIFIED'+('-EXTENDED' if '--extended' in sys.argv else '')
    doc=(S/DOC).read_bytes()
    if (marker+'\r\n') in doc.decode('utf-8-sig'):raise RuntimeError('History refresh already logged')
    entry=('\r\n\r\n'+marker+'\r\n'
        f'正式增量：仅playerhistory；复用本批最新{coverage["rows_before"]}行旧履历，校验{coverage["source_careers"]}份Nexon职业履历原文与解析，已刷新{coverage["refreshed_ordinary_legend_careers"]}名普通传奇官方履历。球队缺失名称仅在至少3名不同球员的唯一加入年/租借记录一致时恢复映射，另核实莫斯科迪纳摩等明确历史队名；补查ICON和怀旧传奇，包括博辛瓦、博德梅尔、西西尼奥、阿比达尔、迪亚比、埃梅尼克、伊巴尔博。25名手工匹配身份按姓名/生日/国籍核实；旧Chen Yang对应1974年杨晨、Li JunYu对应1977年李金羽，未改姓名或生日。Piyapong生日年份来源分歧保留本服1963，单独标注。\r\n'
        f'本批{coverage["changed_players"]}人变更，新增{coverage["new_player_club_eligibilities"]}组俱乐部资格，履历共{coverage["rows_after"]}行。前批33名无履历普通传奇中19名已补，扩展ICON/怀旧传奇另补7人；14名东南亚名宿仍只登记已查生涯及未核实球队映射，不猜国家队/同名俱乐部ID。保留全部旧户口；执教/青训不冒充职业效力；重复效力及租借独立保留。FC27官方可取得当前球队/球员ID，非完整履历，未凭观察日期编造加盟年份、未导入属性。\r\n'
        '双端UI SQLite一致、全部非history表不变、BIG有序重建且270个非目标成员原压缩payload不变、正式player_import完整校验。按442/433/4231及自然位置、同一球员只选一卡，对普通赛季+本队普通传奇重新计算；传奇时刻/中国明日之星不混入普通队套池，属性/模型/概率/强化及现行套装数值未改。\r\n'
        '保护：共同双锁、fresh当前父层全部guards和receipt policies、备份/CAS；游戏运行则延后，不强退、不GUI；本次停服实时state/shop快照只核对不恢复。接口和结构通过不等于比赛通过，实机/比赛=PENDING。证据D:/fifaol3/team-balance-household/；正式证据'+EVIDENCE+'。\r\n')
    evidence=gzip.compress(encoded(dict(coverage=coverage,changes=json.loads((BUILD/'player-changes.json').read_text('utf8')),
        tests=tests,balance=json.loads((R/'balance-summary.json').read_text('utf8')),
        tooling={name:prepare.sha(R/name) for name in ('prepare.py','manual.py','refresh.py','audit.py','balance.py','test.py','install.py')})),mtime=0)
    payloads=[('server','gamedata/fifadb.sqlite',BUILD/'fifadb.sqlite'),('client','data/data_0.big',BUILD/'data_0.big'),
        ('server','gamedata/player-import-validation.json',BUILD/'player-import-validation.json'),
        ('server',DOC,doc+entry.encode('utf8')),('server',EVIDENCE,evidence),('server',SELF,helper.encode('utf8')),
        ('server','play-local.bat',play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode()))]
    for root,rel,source in payloads:
        target=(S if root=='server' else C)/rel;key=(root,rel.casefold())
        if key in guards and current_hash(target)!=guards[key]['sha256']:raise RuntimeError('Fresh parent target differs: '+rel)
        if root=='server' and rel in (SELF,EVIDENCE) and target.exists():raise RuntimeError('Immutable release path already exists')
        guards[key]=dict(root=root,relative=rel,sha256=prepare.sha(source) if isinstance(source,Path) else digest(source))
    policies=list(composition.get('receipt_policies',[]))
    if not any(x['root']=='server' and x['relative']==parent.RECEIPT for x in policies):
        policies.append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in old_receipt.items() if k!='native_status'}))
    composition.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False)
    composition.setdefault('ancestry',[]).append(dict(layer='club-household-refresh',revision=revision,native_status='PENDING'))
    manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,
        guards=composition['guards'],composition=composition,parent_preflight=parent_rel,parent_preflight_sha256=prepare.sha(S/parent_rel),
        changed_players=coverage['changed_players'],new_player_club_eligibilities=coverage['new_player_club_eligibilities'],
        history_rows=coverage['rows_after'],evidence=EVIDENCE,native_status='PENDING')
    manifest_bytes=encoded(manifest)
    payloads.extend([('server',MANIFEST,manifest_bytes),('server',RECEIPT,encoded(dict(status='INSTALLED_CLUB_HOUSEHOLD_REFRESH',
        revision=revision,manifest_sha256=digest(manifest_bytes),state_shop_replaced=False,native_status='PENDING')))])
    entries=[]
    for root,rel,source in payloads:
        target=(S if root=='server' else C)/rel
        if rel in (MANIFEST,RECEIPT) and target.exists():raise RuntimeError('Immutable metadata already exists')
        entries.append(dict(root=root,relative=rel,target=target,source=source,before=current_hash(target),
            after=prepare.sha(source) if isinstance(source,Path) else digest(source)))
    entries.sort(key=lambda x:x['relative']=='play-local.bat')
    return dict(revision=revision,parent=parent_rel,parent_hash=prepare.sha(S/parent_rel),entries=entries,prior=prior)


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
        validation=run([PY,'-B',S/'tools/player_import/check.py','--full'])
        for name,body in snapshot.items():
            if (S/'gamedata'/name).read_bytes()!=body:raise RuntimeError('Live assets changed while stopped; never restore them')
        journal['status']='INSTALLED';prepare.write(backup/'transaction.json',journal)
        return dict(backup=str(backup),preflight=proof,full_player_import=json.loads(validation),assets_identical_while_stopped=True)
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
        if stopped:
            result['launcher_pid'],result['readiness']=restart()
        result['services_restarted']=stopped
    # The watcher intentionally waits while a publication lock exists. Release
    # both locks before waiting for its immutable business package to activate.
    finish(plan_data,result,snapshot,old_hot,before_colors,top,top_before)


def finish(plan_data,result,snapshot,old_hot,before_colors,top,top_before):
        deadline=time.monotonic()+25
        hot=get('http://127.0.0.1:8088/api/hot_update_status')
        while (hot.get('revision')!=old_hot['revision'] or not hot.get('watcher_running')) and time.monotonic()<deadline:
            time.sleep(.25)
            hot=get('http://127.0.0.1:8088/api/hot_update_status')
        colors=get('https://127.0.0.1/static/info/teamcolor')
        if hot['revision']!=old_hot['revision'] or hot['routes']!=old_hot['routes'] or not hot['watcher_running'] or hot['error'] is not None:
            raise RuntimeError('Business hot package status differs; preserve files/assets and inspect')
        if colors['teamColors']!=before_colors['teamColors']:raise RuntimeError('Existing color definitions changed unexpectedly')
        actual=prepare.load(S/SELF,'household_final_gate').preflight(S,C)
        state_now=json.loads((S/'gamedata/state.json').read_bytes());state_before=json.loads(snapshot['state.json'])
        business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
        same_business=business(state_now)==business(state_before)
        result.update(status='INSTALLED_AND_RUNTIME_ACTIVE_NATIVE_PENDING',revision=plan_data['revision'],
            top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),
            composition_api='compose_manifest(server=None,client=None)',preflight=actual,
            files={str(S/rel):prepare.sha(S/rel) for rel in (SELF,MANIFEST,RECEIPT,'play-local.bat','gamedata/fifadb.sqlite','gamedata/player-import-validation.json')},
            client_files={str(C/'data/data_0.big'):prepare.sha(C/'data/data_0.big')},
            hot_update_status=hot,services_restored=listening()==[443,8088,28002],services_restarted=result.get('services_restarted',False),
            state_shop_written=False,shop_equal=(S/'gamedata/shop.json').read_bytes()==snapshot['shop.json'],
            state_business_equal=same_business,later_business_progress_preserved=not same_business,
            club_bonus_values_changed=False,moments_unchanged=True,GUI_used=False,native_verified=False,match_verified=False,
            handoff=str(R/'installed-handback.json'),observed_at=datetime.datetime.now().astimezone().isoformat())
        prepare.write(R/'installed-handback.json',result)
        if top.read_bytes()==top_before:atomic(encoded(result),top)
        else:
            result['later_top_descriptor_preserved']=True;prepare.write(R/'installed-handback.json',result)
        prepare.write(R/'install-status.json',dict(status=result['status'],formal_writer=False,handback=str(R/'installed-handback.json')))
        result['locks_released']=True;prepare.write(R/'installed-handback.json',result)
        print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
