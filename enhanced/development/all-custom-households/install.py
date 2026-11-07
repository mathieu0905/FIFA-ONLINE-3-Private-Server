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
SELF='patches/custom_households_verified_20261107_preflight.py'
MANIFEST='patches/custom-households-verified-20261107-installed.json'
RECEIPT='patches/custom-households-verified-20261107-receipt.json'
EVIDENCE='patches/custom-households-verified-20261107-evidence.json.gz'
DOC='docs/工程经验与修改边界.txt'
BUILD=Path(json.loads((R/'install-build-current.json').read_text('utf8'))['build']) if (R/'install-build-current.json').exists() else R/'build-pending'



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
            body=encoded(dict(pid=os.getpid(),task='custom-households-verified',created=datetime.datetime.now().astimezone().isoformat()))
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
    from install_plan import build_plan
    return build_plan(sys.modules[__name__])


def commit(plan,snapshot):
    assert_idle()
    # Some inherited read-only preflights use sqlite3's transaction context,
    # which does not close the connection. Collect their unreachable statement
    # cycles before Windows atomically replaces the UI database.
    import gc
    gc.collect()
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
    if listening():raise RuntimeError("Refusing duplicate service start")
    with (R/'service.stdout.log').open('ab') as out,(R/'service.stderr.log').open('ab') as err:
        p=subprocess.Popen([str(PY),'-B','-u',str(S/'start_all.py')],cwd=S,env=environment(),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=HIDDEN)
    ready=run([PY,'-B',S/'wait_services.py','--timeout','30'])
    return p.pid,ready


def main():
    if not idle():
        prepare.write(R/'install-status.json',dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_files_written=False))
        print('更新已延后，当前游戏继续运行');return
    transaction=json.loads((R/'transaction-tests.json').read_text('utf8'))
    if transaction['status']!='PASS' or transaction['installer_sha256']!=prepare.sha(Path(__file__)) or transaction.get('plan_sha256')!=prepare.sha(R/'install_plan.py'):
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
            coverage=plan_data['coverage'],full_career_review_complete=False,club_bonus_values_changed=False,moments_unchanged=True,GUI_used=False,native_verified=False,match_verified=False,
            handoff=str(R/'installed-handback.json'),observed_at=datetime.datetime.now().astimezone().isoformat())
        prepare.write(R/'installed-handback.json',result)
        if top.read_bytes()==top_before:atomic(encoded(result),top)
        else:
            result['later_top_descriptor_preserved']=True;prepare.write(R/'installed-handback.json',result)
        prepare.write(R/'install-status.json',dict(status=result['status'],formal_writer=False,handback=str(R/'installed-handback.json')))
        result['locks_released']=True;prepare.write(R/'installed-handback.json',result)
        print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
