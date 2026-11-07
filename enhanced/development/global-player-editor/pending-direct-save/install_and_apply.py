"""Execute only in the coordinator's exclusive direct-save window."""
from pathlib import Path
import ast,datetime,hashlib,importlib.util,json,os,re,shutil,sys,time,uuid
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/FO3ID/player-editor-workspace')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',old);assert len(matches)==1
parent_rel=matches[0].decode().replace('\\','/');parent=load(S/parent_rel,'direct_save_parent')
parent.preflight(S,C);composed=parent.compose_manifest(S,C);verifier=load(S/'patches/startup_market_preflight.py','direct_save_verifier');guards=verifier.table(composed['guards'])
sources=read(ROOT/'source-hashes.json')
for rel,wanted in sources.items():assert sha(S/rel)==wanted,'Source changed: '+rel
targets=set(sources)|{'play-local.bat','patches/player_editor_save_preflight.py'}
template=(ROOT.parent/'pending-current/player_editor_current_preflight.py').read_text('utf-8')
template=template.replace("MANIFEST='patches/player-editor-current-manifest.json'","MANIFEST='patches/player-editor-save-manifest.json'").replace("RECEIPT='patches/player-editor-current-installed.json'","RECEIPT='patches/player-editor-save-installed.json'")
template=template.replace("SELF='patches/player_editor_current_preflight.py'","SELF='patches/player_editor_save_preflight.py'").replace("PARENT='patches/moments_display_preflight.py'",'PARENT='+repr(parent_rel))
template=template.replace("ALLOWED={('server',n) for n in ('player_editor/publish_database.py','play-local.bat',SELF)}",'ALLOWED='+repr({('server',rel) for rel in targets}))
template=template.replace("required={PARENT,'patches/moments-display-release-manifest.json','patches/moments-display-release-installed.json'}",'required='+repr({parent_rel,parent.MANIFEST,parent.RECEIPT}))
template=template.replace('PLAYER_EDITOR_CURRENT_LAUNCHER','PLAYER_EDITOR_ONE_CLICK_SAVE').replace('INSTALLED_PLAYER_EDITOR_CURRENT','INSTALLED_PLAYER_EDITOR_SAVE').replace('PLAYER_EDITOR_8088_CURRENT_PASS','PLAYER_EDITOR_DIRECT_SAVE_PASS')
template=template.replace("c,v=p._compose(server,client);g=v.table(c['guards']);", "c=p.compose_manifest(server,client);vs=importlib.util.spec_from_file_location('direct_save_validator',server/'patches/startup_market_preflight.py');v=importlib.util.module_from_spec(vs);vs.loader.exec_module(v);g=v.table(c['guards']);")
ast.parse(template)
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=S/'backups'/('player-editor-direct-save-'+stamp)
lock=S/'.shop-release.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
try:
    parent.preflight(S,C)
    for rel,wanted in sources.items():assert sha(S/rel)==wanted,'Concurrent source change: '+rel
    assert (S/'play-local.bat').read_bytes()==old
    backup.mkdir();entries=[]
    for rel in targets|{'patches/player-editor-save-manifest.json','patches/player-editor-save-installed.json'}:
        path=S/rel;e=dict(relative=rel,existed=path.exists())
        if e['existed']:
            dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        entries.append(e)
    try:
        for rel in sources:shutil.copyfile(ROOT/Path(rel).name,S/rel)
        (S/'patches/player_editor_save_preflight.py').write_text(template,'utf-8')
        (S/'play-local.bat').write_bytes(old.replace(matches[0],b'patches\\player_editor_save_preflight.py'))
        child=load(S/'patches/player_editor_save_preflight.py','direct_save_child')
        rows=[dict(root='server',relative=rel,parent_sha256=guards.get(('server',rel.casefold()),{}).get('sha256'),sha256=sha(S/rel)) for rel in sorted(targets)]
        m=dict(phase='PLAYER_EDITOR_ONE_CLICK_SAVE',state_shop_replaced=False,client_root=str(C),files=rows,parent_files={n:sha(S/n) for n in (parent_rel,parent.MANIFEST,parent.RECEIPT)})
        write(S/child.MANIFEST,m);write(S/child.RECEIPT,dict(status='INSTALLED_PLAYER_EDITOR_SAVE',manifest_sha256=sha(S/child.MANIFEST),backup=str(backup)))
        result=child.preflight(S,C);write(ROOT/'code-preflight.json',result)
    except Exception:
        for e in reversed(entries):
            target=S/e['relative']
            if e['existed']:shutil.copyfile(backup/e['relative'],target)
            else:target.unlink(missing_ok=True)
        raise
finally:
    os.close(fd);lock.unlink(missing_ok=True)
print('DIRECT_SAVE_CODE_INSTALLED',flush=True)
sys.path.insert(0,str(S));from player_editor.player_database import Database
from player_editor.publish_database import apply
d=Database(S,C,W);draft=d.draft();assert draft['cards'],'No pending user edits'
record=None;job_path=None
for path in sorted((W/'jobs').glob('*.json'),reverse=True):
    j=read(path)
    if j['status'] not in ('built','apply_failed'):continue
    candidate=Path(j['candidate']);m=read(candidate/'manifest.json')
    if sorted(m['changes'],key=lambda r:r['spid'])==sorted(draft['cards'].values(),key=lambda r:r['spid']) and sha(d.db)==m['source_hashes']['database'] and sha(C/'data/data_0.big')==m['source_hashes']['client']:
        record=j;job_path=path;break
if record is None:
    job=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];candidate=W/'builds'/job
    m=d.build(draft,candidate);job_path=W/'jobs'/(job+'.json');record=dict(id=job,cards=len(draft['cards']),revision=draft['revision'],candidate=str(candidate),manifest_sha256=sha(candidate/'manifest.json'))
record['status']='applying';write(job_path,record)
try:
    record.update(apply(record['candidate'],record['manifest_sha256'],manage_services=True))
except Exception as error:
    record.update(status='apply_failed',error=str(error));write(job_path,record);raise
write(job_path,record);write(ROOT/'application-result.json',record)
print(json.dumps(record,ensure_ascii=True),flush=True)
