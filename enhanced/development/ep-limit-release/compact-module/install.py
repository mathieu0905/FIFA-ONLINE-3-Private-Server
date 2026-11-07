from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,os,subprocess,sys,uuid
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
def load():
    spec=importlib.util.spec_from_file_location('ep_child',ROOT/'payload/player_value_preflight.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);return p
p=load()
def sha(path):return p.sha(path) if Path(path).exists() else None
def raw(obj):return json.dumps(obj,ensure_ascii=False,indent=2).encode('utf-8')
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.ep-stage-'+uuid.uuid4().hex)
    try:
        with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:tmp.unlink(missing_ok=True)
def target(roots,root,name):
    q=(roots[root]/name).resolve()
    if not q.is_relative_to(roots[root]):raise RuntimeError('Target escape')
    return q
def preview(server,client):
    m=p.read(ROOT/'manifest.json');c,v=p._compose(server,client,m,False);guards=v.table(c['guards'])
    for e in m['files']:
        key=v.canonical(e);digest=e['parent_sha256']
        if digest is None:
            guards.pop(key,None)
            if target({'server':server,'client':client},e['root'],e['relative']).exists():raise RuntimeError('New target already exists')
        else:guards[key]=dict(root=e['root'],relative=e['relative'],sha256=digest)
        if sha(ROOT/'payload'/e['payload'])!=e['sha256']:raise RuntimeError('Payload changed: '+e['relative'])
    c['guards']=list(guards.values());v.verify_manifest(c,server,client)
    return m
def install(server,client,apply=False,fail_after=None):
    server=Path(server).resolve();client=Path(client).resolve();roots={'server':server,'client':client}
    if (server/p.RECEIPT).exists():
        if sha(server/p.MANIFEST)!=sha(ROOT/'manifest.json'):raise RuntimeError('Different child already installed')
        return dict(status='ALREADY_INSTALLED',preflight=p.preflight(server,client))
    m=preview(server,client)
    if not apply:return dict(status='DRY_RUN_PASS',targets=len(m['files'])+2)
    processes=subprocess.run(['tasklist','/FI','IMAGENAME eq fifazf.exe','/FO','CSV','/NH'],capture_output=True,text=True,check=True)
    if 'fifazf.exe' in processes.stdout.lower():raise RuntimeError('Please exit the game before installing UI resources')
    lock=server/'.shop-release.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    backup=server/'backups'/('player-value-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    entries=[];done=[]
    try:
        m=preview(server,client);backup.mkdir(parents=True)
        receipt=dict(status='INSTALLED_CURRENCY_COMPACT',release_id=m['release_id'],manifest_sha256=sha(ROOT/'manifest.json'),
                     backup=str(backup),state_shop_replaced=False)
        plans=[(e['root'],e['relative'],(ROOT/'payload'/e['payload']).read_bytes()) for e in m['files']]
        plans += [('server',p.MANIFEST,(ROOT/'manifest.json').read_bytes()),('server',p.RECEIPT,raw(receipt))]
        for i,(root,name,data) in enumerate(plans):
            dest=target(roots,root,name);before=sha(dest)
            entry=dict(root=root,relative=name,before=before,after=hashlib.sha256(data).hexdigest(),backup=str(i)+'.bak')
            if before is not None:atomic(backup/entry['backup'],dest.read_bytes())
            entries.append(entry)
        tx=dict(status='BACKED_UP',server=str(server),client=str(client),entries=entries,completed=[])
        atomic(backup/'transaction.json',raw(tx))
        try:
            preview(server,client)
            for i,(root,name,data) in enumerate(plans):
                dest=target(roots,root,name)
                if sha(dest)!=entries[i]['before']:raise RuntimeError('Concurrent edit: '+name)
                atomic(dest,data);done.append(i);tx['completed']=done[:];atomic(backup/'transaction.json',raw(tx))
                if fail_after==i+1:raise RuntimeError('Injected failure')
            result=p.preflight(server,client);tx['status']='INSTALLED';atomic(backup/'transaction.json',raw(tx))
        except Exception:
            for i in reversed(done):
                e=entries[i];dest=target(roots,e['root'],e['relative'])
                if sha(dest)!=e['after']:raise RuntimeError('Concurrent edit preserved during rollback: '+e['relative'])
                if e['before'] is None:dest.unlink(missing_ok=True)
                else:atomic(dest,(backup/e['backup']).read_bytes())
            tx['status']='ROLLED_BACK';atomic(backup/'transaction.json',raw(tx));raise
        return dict(status='INSTALLED',backup=str(backup),preflight=result)
    finally:lock.unlink(missing_ok=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--server',default='D:/FO3ID/server');ap.add_argument('--client',default='D:/FO3ID/32795');ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    print(json.dumps(install(a.server,a.client,a.apply),ensure_ascii=True,indent=2))
