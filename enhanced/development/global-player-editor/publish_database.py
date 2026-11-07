"""Stopped-service, backed-up transaction for a reviewed global database."""
from pathlib import Path
import argparse,os,shutil,socket,subprocess,sys,time,uuid
sys.dont_write_bytecode=True
from player_database import HERE,module,read,sha,write

def game_closed():
    r=subprocess.run(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],capture_output=True,text=True,errors='replace',check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if 'fifazf.exe' in r.stdout.lower():raise RuntimeError('请先退出 FIFA Online 3，再应用全局数据库')
def listening(port):
    try:
        with socket.create_connection(('127.0.0.1',port),.3):return True
    except OSError:return False
def baseline(server,client):
    installed=server/'patches/player-database-installed.json'
    if installed.exists():
        m=read(installed);helper=server/'patches/player_database_preflight.py'
        wanted=next(r['sha256'] for r in m['guards'] if r['root']=='server' and r['relative']=='patches/player_database_preflight.py')
        if sha(helper)!=wanted:raise RuntimeError('数据库启动检查器已变化')
        module(helper,'installed_database_gate').preflight(server,client);return m['guards']
    gate=module(server/'patches/console_backpressure_preflight.py','original_database_gate')
    gate.preflight(server,client);return gate.compose_manifest(server,client)['guards']
def atomic(source,target):
    target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.playerdb-'+uuid.uuid4().hex)
    try:shutil.copyfile(source,temporary);os.replace(temporary,target)
    finally:temporary.unlink(missing_ok=True)
def transaction(pairs,backup,verify,fail_after=None):
    backup.mkdir(parents=True,exist_ok=False);entries=[]
    for i,(source,target) in enumerate(pairs):
        e=dict(target=str(target),backup=str(i)+'.before',existed=target.exists(),after=sha(source))
        if target.exists():e['before']=sha(target);shutil.copyfile(target,backup/e['backup'])
        entries.append(e)
    journal=dict(status='prepared',entries=entries,completed=[]);write(backup/'transaction.json',journal)
    try:
        for i,(source,target) in enumerate(pairs):
            atomic(source,target);journal['completed'].append(i);write(backup/'transaction.json',journal)
            if fail_after==i+1:raise RuntimeError('Injected transaction failure')
        verify();journal['status']='installed_runtime_pending';write(backup/'transaction.json',journal)
    except Exception:
        for e in reversed(entries):
            target=Path(e['target'])
            if e['existed']:atomic(backup/e['backup'],target)
            else:target.unlink(missing_ok=True)
        journal['status']='rolled_back';write(backup/'transaction.json',journal);raise
def apply(candidate,expected_sha,manage_services=False):
    # Serialize publishers even when two manager processes use different workspaces.
    candidate=Path(candidate).resolve();m=read(candidate/'manifest.json')
    from hashlib import sha256
    lock_dir=HERE/'locks';lock_dir.mkdir(exist_ok=True)
    lock=lock_dir/(sha256(str(Path(m['server']).resolve()).casefold().encode()).hexdigest()+'.lock')
    try:
        descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('已有数据库发布任务；若上次异常退出，请检查发布备份后清理锁文件：'+str(lock))
    try:
        os.write(descriptor,str(os.getpid()).encode());os.close(descriptor)
        return _apply(candidate,expected_sha,manage_services)
    finally:
        lock.unlink(missing_ok=True)

def _apply(candidate,expected_sha,manage_services=False):
    candidate=Path(candidate).resolve()
    if sha(candidate/'manifest.json')!=expected_sha:raise RuntimeError('候选清单校验值不匹配')
    m=read(candidate/'manifest.json')
    if m.get('status')!='BUILT_RUNTIME_PENDING' or m.get('non_target_members_identical')!=270 or m.get('state_shop_replaced') is not False:raise RuntimeError('不是已验证的双端数据库候选')
    if set(m['output_hashes'])!={'fifadb.sqlite','data_0.big'}:raise RuntimeError('非法候选输出范围')
    for name,wanted in m['output_hashes'].items():
        if sha(candidate/name)!=wanted:raise RuntimeError('候选文件已变化：'+name)
    server,client=Path(m['server']).resolve(),Path(m['client']).resolve()
    def check_sources():
        if sha(server/'gamedata/fifadb.sqlite')!=m['source_hashes']['database'] or sha(client/'data/data_0.big')!=m['source_hashes']['client']:raise RuntimeError('正式数据库已变化，请重新生成')
    check_sources();guards=baseline(server,client);game_closed();was_running=listening(443)
    if was_running and not manage_services:raise RuntimeError('请先停止游戏服务，或使用 --manage-services')
    if was_running:subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(server/'stop-server.ps1')],check=True,capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(50):
            if not listening(443) and not listening(8088):break
            time.sleep(.1)
        else:raise RuntimeError('游戏服务未停止，拒绝替换数据库')
        game_closed();check_sources();baseline(server,client)
        protected={n:sha(server/'gamedata'/n) for n in ('state.json','shop.json')}
        revision=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];stage=candidate/('publish-'+revision);stage.mkdir()
        launcher=server/'play-local.bat';content=launcher.read_bytes();old,new=b'patches\\console_backpressure_preflight.py',b'patches\\player_database_preflight.py'
        if old in content:content=content.replace(old,new)
        elif new not in content:raise RuntimeError('未知启动脚本版本，拒绝修改')
        (stage/'play-local.bat').write_bytes(content);helper=HERE/'database_preflight.py'
        pairs=[(candidate/'fifadb.sqlite',server/'gamedata/fifadb.sqlite'),(candidate/'data_0.big',client/'data/data_0.big'),(stage/'play-local.bat',launcher),(helper,server/'patches/player_database_preflight.py')]
        table={(r['root'],r['relative'].replace('\\','/').casefold()):r for r in guards}
        for source,target in pairs:
            root='server' if target.is_relative_to(server) else 'client';relative=target.relative_to(server if root=='server' else client).as_posix()
            table[(root,relative.casefold())]=dict(root=root,relative=relative,sha256=sha(source))
        installed=dict(schema=1,revision=revision,client=str(client),guards=list(table.values()),state_shop_replaced=False,native_status='PENDING',candidate_manifest_sha256=expected_sha)
        write(stage/'player-database-installed.json',installed);pairs += [(stage/'player-database-installed.json',server/'patches/player-database-installed.json')]
        def verify():
            for n,wanted in protected.items():
                if sha(server/'gamedata'/n)!=wanted:raise RuntimeError('停服期间玩家资产变化')
            module(helper,'new_database_gate').preflight(server,client)
        backup=server/'backups/player-database'/revision;transaction(pairs,backup,verify)
        return dict(status='installed',backup=str(backup),revision=revision,native_status='PENDING')
    finally:
        if was_running and manage_services:
            env={**os.environ,'FO3_GAME':str(client),'FO3_LANGUAGE':'chi','FO3_MAX_GRADE':'20'};logs=server/'captures';logs.mkdir(exist_ok=True)
            with (logs/'player-database-restart.log').open('ab') as log:subprocess.Popen([str(server/'.venv/Scripts/python.exe'),'-B','-u',str(server/'start_all.py')],cwd=server,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('candidate');p.add_argument('--sha',required=True);p.add_argument('--manage-services',action='store_true');args=p.parse_args()
    print(apply(args.candidate,args.sha,args.manage_services))
