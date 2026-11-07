"""Direct official install: fresh parent composition, shared locks, own-file rollback."""
from pathlib import Path
from contextlib import contextmanager
import datetime,hashlib,json,os,re,shutil,socket,subprocess,sys,time,uuid
sys.dont_write_bytecode=True
import build
R=build.HERE;S=build.SERVER;C=build.CLIENT
SELF='patches/club_history_preflight.py'
MANIFEST='patches/club-history-installed.json'
RECEIPT='patches/club-history-receipt.json'

def encoded(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def digest(b):return hashlib.sha256(b).hexdigest()
def process_env():
    env=dict(os.environ)
    env['PSModulePath']=str(Path(env.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/Modules')+';'+str(Path(env.get('ProgramFiles','C:/Program Files'))/'WindowsPowerShell/Modules')
    return env

@contextmanager
def locks(server):
    owned=[]
    try:
        for name in ['.shop-release.lock','.fo3-publish.lock']:
            p=server/name;fd=os.open(p,os.O_EXCL|os.O_CREAT|os.O_WRONLY|getattr(os,'O_BINARY',0))
            body=encoded(dict(pid=os.getpid(),task='club-history',thread='01a1b13d-0275-7491-bb9d-6d6d8eaa8ed3'))
            owned.append((p,fd,body));os.write(fd,body);os.fsync(fd)
        yield
    finally:
        for p,fd,body in reversed(owned):
            os.close(fd)
            if p.exists() and p.read_bytes()==body:p.unlink()

def game_closed():
    r=subprocess.run(['powershell.exe','-NoProfile','-Command',
       'if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],env=process_env(),creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode:raise RuntimeError('Game active. Do not interrupt the player; installation requires a closed client.')

def plan(server=S,client=C,build_dir=R/'build'):
    server=Path(server).resolve();client=Path(client).resolve();build_dir=Path(build_dir).resolve()
    result=json.loads((build_dir/'build-result.json').read_text('utf8'))
    if result.get('status')!='BUILT_FOR_DIRECT_INSTALL' or result.get('state_shop_written') is not False or result.get('non_target_members_identical')!=270:
        raise RuntimeError('Unverified database resource build')
    if build.sha(build_dir/'fifadb.sqlite')!=result['database_sha256'] or build.sha(build_dir/'data_0.big')!=result['big_sha256']:
        raise RuntimeError('Build output changed')
    baseline=json.loads((build_dir/'baseline.json').read_text('utf8'))
    for rel in ['gamedata/fifadb.sqlite','server_display_zh.json','extract_fifadb.py','tools/re/refpack.py','tools/re/bigdir.py']:
        if build.sha(server/rel)!=baseline[str(S/rel)]:raise RuntimeError('Build baseline changed; rebase history update: '+rel)
    if build.sha(client/'data/data_0.big')!=baseline[str(C/'data/data_0.big')]:raise RuntimeError('Client DB baseline changed; rebase required')
    play=(server/'play-local.bat').read_bytes()
    matches=re.findall(rb'patches\\(\w+_preflight\.py)',play)
    if len(matches)!=1:raise RuntimeError('Ambiguous launch preflight')
    parent_rel='patches/'+matches[0].decode()
    if parent_rel==SELF:raise RuntimeError('Club-history is already installed; do not overwrite its immutable receipt')
    parent=build.load(server/parent_rel,'history_fresh_parent')
    prior=parent.preflight(server,client)
    composition=parent.compose_manifest(server,client)
    validator=build.load(server/'patches/startup_market_preflight.py','history_validator')
    validator.verify_manifest(composition,server,client)
    table=validator.table(composition['guards'])
    helper=(R/'preflight.py').read_bytes();compile(helper,SELF,'exec')
    newplay=play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode())
    payloads=[('server','gamedata/fifadb.sqlite',build_dir/'fifadb.sqlite'),
              ('client','data/data_0.big',build_dir/'data_0.big'),
              ('server',SELF,helper),('server','play-local.bat',newplay)]
    changes=[]
    for root,rel,source in payloads:
        target=(server if root=='server' else client)/rel;key=(root,rel.casefold())
        before=build.sha(target) if target.exists() else None
        if key in table:
            if before!=table[key]['sha256']:raise RuntimeError('Parent target changed: '+rel)
        elif target.exists():raise RuntimeError('Unregistered existing target: '+rel)
        after=build.sha(source) if isinstance(source,Path) else digest(source)
        changes.append(dict(root=root,relative=rel,before=before,after=after))
        table[key]=dict(root=root,relative=rel,sha256=after)
    composition['guards']=list(table.values());composition['files_verified']=False
    composition.setdefault('ancestry',[]).append(dict(layer='official-club-history',native_status='PENDING'))
    revision='club-history-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    manifest=dict(schema=1,revision=revision,client=str(client),state_shop_replaced=False,
       guards=composition['guards'],composition=composition,parent_preflight=parent_rel,
       parent_preflight_sha256=build.sha(server/parent_rel),changes=changes,
       coverage_report_sha256=build.sha(build_dir/'coverage-report.json'),coverage=result['report'])
    manifest_body=encoded(manifest)
    payloads += [('server',MANIFEST,manifest_body),('server',RECEIPT,encoded(dict(
       status='INSTALLED_CLUB_HISTORY',revision=revision,manifest_sha256=digest(manifest_body),state_shop_replaced=False,native_status='PENDING')))]
    for rel in [SELF,MANIFEST,RECEIPT]:
        if (server/rel).exists():raise RuntimeError('Immutable release metadata already exists: '+rel)
    # Save snapshots as bytes only for the small launcher/helper/metadata. The large
    # resource and DB are streamed from their exact build inputs.
    entries=[]
    for root,rel,source in payloads:
        target=(server if root=='server' else client)/rel
        entries.append(dict(root=root,relative=rel,target=target,source=source,
              before=build.sha(target) if target.exists() else None,
              after=build.sha(source) if isinstance(source,Path) else digest(source)))
    entries.sort(key=lambda x:x['relative']=='play-local.bat')
    return dict(server=server,client=client,entries=entries,revision=revision,parent=parent_rel,
        parent_hash=build.sha(server/parent_rel),prior=prior,build_dir=build_dir)

def atomic(source,target):
    temp=target.with_name(target.name+'.club-history-'+uuid.uuid4().hex)
    try:
        if isinstance(source,Path):shutil.copyfile(source,temp)
        else:temp.write_bytes(source)
        os.replace(temp,target)
    finally:temp.unlink(missing_ok=True)

def commit(p,fail_after=None):
    server=p['server'];backup=server/'backups'/p['revision'];backup.mkdir(parents=True,exist_ok=False)
    for i,e in enumerate(p['entries']):
        e['backup']=backup/(str(i)+'-'+e['target'].name)
        if (build.sha(e['target']) if e['target'].exists() else None)!=e['before']:
            raise RuntimeError('Concurrent target change before backup: '+str(e['target']))
        if e['before'] is not None:shutil.copyfile(e['target'],e['backup'])
    journal=dict(revision=p['revision'],status='PREPARED',entries=[{k:str(v) if isinstance(v,Path) else v for k,v in e.items() if k!='source'} for e in p['entries']],completed=[])
    build.write(backup/'transaction.json',journal)
    written=[]
    try:
        if build.sha(server/p['parent'])!=p['parent_hash']:raise RuntimeError('Parent gate changed')
        for i,e in enumerate(p['entries'],1):
            if (build.sha(e['target']) if e['target'].exists() else None)!=e['before']:
                raise RuntimeError('Concurrent target change: '+str(e['target']))
            if isinstance(e['source'],Path) and build.sha(e['source'])!=e['after']:raise RuntimeError('Build input drift')
            e['target'].parent.mkdir(parents=True,exist_ok=True);atomic(e['source'],e['target']);written.append(e)
            journal['completed'].append(e['relative']);build.write(backup/'transaction.json',journal)
            if i==fail_after:raise RuntimeError('INJECTED_COMMIT_FAILURE')
        proof=build.load(server/SELF,'history_installed_gate').preflight(server,p['client'])
        journal['status']='INSTALLED';build.write(backup/'transaction.json',journal)
    except BaseException:
        retained=[]
        for e in reversed(written):
            if not e['target'].exists() or build.sha(e['target'])!=e['after']:
                retained.append(str(e['target']));continue
            if e['before'] is None:e['target'].unlink()
            else:atomic(e['backup'],e['target'])
        journal.update(status='ROLLBACK_PRESERVED_LATER_CHANGES' if retained else 'ROLLED_BACK',retained=retained)
        build.write(backup/'transaction.json',journal)
        raise
    return dict(status='INSTALLED_CLUB_HISTORY',backup=str(backup),revision=p['revision'],preflight=proof,
       top_preflight=str(server/SELF),top_manifest=str(server/MANIFEST),top_receipt=str(server/RECEIPT),
       hashes={**{str(server/rel):build.sha(server/rel) for rel in [SELF,MANIFEST,RECEIPT,'play-local.bat','gamedata/fifadb.sqlite']},
               str(p['client']/'data/data_0.big'):build.sha(p['client']/'data/data_0.big')},
       state_shop_written=False,native_status='PENDING')

def assets_snapshot(backup):
    snap={}
    for name in ['state.json','shop.json']:
        path=S/'gamedata'/name;body=path.read_bytes();(backup/('fresh-'+name)).write_bytes(body)
        snap[name]=dict(sha256=digest(body),bytes=len(body))
    return snap

def services_listening():
    result=[]
    for port in [443,8088,28002]:
        try:
            with socket.create_connection(('127.0.0.1',port),.3):result.append(port)
        except OSError:pass
    return result

def restart():
    env={**process_env(),'FO3_GAME':str(C),'FO3_LANGUAGE':'chi','FO3_MAX_GRADE':'20'}
    with (S/'captures/club-history-restart.log').open('ab') as log:
        subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,
           stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','30'],cwd=S,check=True,creationflags=subprocess.CREATE_NO_WINDOW)

def main():
    with locks(S):
        game_closed();p=plan()
        descriptor=R.parent/'root-current-top.json'
        descriptor_before=descriptor.read_bytes() if descriptor.exists() else None
        atomic(encoded(dict(status='INSTALLING_WITH_SHARED_LOCKS',formal_writer=True,revision=p['revision'],
               parent=p['parent'],build=str(p['build_dir']),state_shop_written=False)),R/'status.json')
        build.write(R/'install-plan.json',dict(revision=p['revision'],parent=p['parent'],parent_hash=p['parent_hash'],
                    prior=p['prior'],changes=[{k:str(v) if isinstance(v,Path) else v for k,v in e.items() if k!='source'} for e in p['entries']]))
        # Recheck the exact current entry and closed-client condition under both locks.
        game_closed();was_running=bool(services_listening());stopped=False;result=None
        try:
            if was_running:
                subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=process_env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                stopped=True
                deadline=time.monotonic()+12
                while services_listening():
                    if time.monotonic()>deadline:raise RuntimeError('Official services did not stop')
                    time.sleep(.2)
            before_dir=R/'fresh-stop-snapshot'/p['revision'];before_dir.mkdir(parents=True)
            assets=assets_snapshot(before_dir)
            result=commit(p)
            result['fresh_stop_assets']=assets
            for name,record in assets.items():
                if build.sha(S/'gamedata'/name)!=record['sha256']:raise RuntimeError('Assets changed while stopped: '+name)
            result['assets_identical_while_stopped']=True
            build.write(R/'installed-handback.json',result)
        finally:
            if was_running and stopped:restart()
        result['services_restored']=services_listening()==[443,8088,28002] if was_running else 'previously_stopped'
        result['composition_api']='compose_manifest(server=None, client=None)'
        build.write(R/'installed-handback.json',result)
        atomic(encoded(dict(status='INSTALLED',formal_writer=False,handback=str(R/'installed-handback.json'),
            top_preflight=result['top_preflight'],revision=result['revision'],services_restored=result['services_restored'],
            hashes=result['hashes'],state_shop_written=False,native_status='PENDING')),R/'status.json')
        if (descriptor.read_bytes() if descriptor.exists() else None)==descriptor_before:
            atomic(encoded(dict(status='OBSERVED_INDEPENDENT_CLUB_HISTORY_INSTALL',observed_at=datetime.datetime.now().astimezone().isoformat(),
               top_preflight=result['top_preflight'],top_manifest=result['top_manifest'],top_receipt=result['top_receipt'],
               files=result['hashes'],function_signatures=dict(sha='p',preflight='server=None, client=None',compose_manifest='server=None, client=None'),
               composition_available=True,physical_preflight_run_by_this_observer=True,
               handoff=str(R/'installed-handback.json'),state_shop_written=False,services_restored=result['services_restored'],
               GUI_status='Database/resource, production-function and service checks PASS; native UI and match not tested. Root goal remains paused.')),descriptor)
        else:
            result['shared_descriptor_retained_due_to_concurrent_change']=True
            build.write(R/'installed-handback.json',result)
        print(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':main()
