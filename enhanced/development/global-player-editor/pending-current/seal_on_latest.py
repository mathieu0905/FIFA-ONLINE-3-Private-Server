"""Run only in the coordinator's exclusive writer window."""
from pathlib import Path
import hashlib,importlib.util,json,re,shutil,datetime
S=Path('D:/FO3ID/server');ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),'utf-8')
launcher=S/'play-local.bat';old=launcher.read_bytes()
matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',old);assert len(matches)==1
parent_rel=matches[0].decode().replace('\\','/')
parent=load(S/parent_rel,'latest_editor_parent');c=parent.compose_manifest(S,'D:/FO3ID/32795')
v=load(S/'patches/startup_market_preflight.py','latest_editor_validator');g=v.table(c['guards'])
oldpub=S/'backups/player-editor-8088-20261106/publish_database.before-current.py'
target=S/'player_editor/publish_database.py';payload=ROOT/'publish_database.py'
expected=g[('server','player_editor/publish_database.py')]['sha256']
assert sha(oldpub)==expected
assert sha(target) in (expected,sha(payload)), 'Publisher changed outside this task'
# Validate the complete latest version, projecting only our known pending source back to its sealed parent.
before=dict(c);before['guards']=[dict(row,sha256=sha(target)) if v.canonical(row)==('server','player_editor/publish_database.py') else row for row in c['guards']]
v.verify_manifest(before,S,'D:/FO3ID/32795')
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup=S/'backups'/('player-editor-current-'+stamp);backup.mkdir()
shutil.copyfile(launcher,backup/'play-local.bat');shutil.copyfile(oldpub,backup/'publish_database.py')
template=(ROOT/'player_editor_current_preflight.py').read_text('utf-8')
template=template.replace("PARENT='patches/moments_display_preflight.py'",'PARENT='+repr(parent_rel))
template=template.replace("required={PARENT,'patches/moments-display-release-manifest.json','patches/moments-display-release-installed.json'}",'required='+repr({parent_rel,parent.MANIFEST,parent.RECEIPT}))
template=template.replace("c,v=p._compose(server,client);g=v.table(c['guards']);", "c=p.compose_manifest(server,client);vs=importlib.util.spec_from_file_location('current_editor_validator',server/'patches/startup_market_preflight.py');v=importlib.util.module_from_spec(vs);vs.loader.exec_module(v);g=v.table(c['guards']);")
helper=S/'patches/player_editor_current_preflight.py';helper.write_text(template,'utf-8');shutil.copyfile(payload,target)
new=old.replace(matches[0],b'patches\\player_editor_current_preflight.py');launcher.write_bytes(new)
child=load(helper,'current_editor_final')
rows=[dict(root=root,relative=rel,parent_sha256=g.get((root,rel.casefold()),{}).get('sha256'),sha256=sha(S/rel)) for root,rel in sorted(child.ALLOWED)]
m=dict(phase='PLAYER_EDITOR_CURRENT_LAUNCHER',state_shop_replaced=False,client_root='D:/FO3ID/32795',files=rows,parent_files={n:sha(S/n) for n in (parent_rel,parent.MANIFEST,parent.RECEIPT)})
write(S/child.MANIFEST,m);write(S/child.RECEIPT,dict(status='INSTALLED_PLAYER_EDITOR_CURRENT',manifest_sha256=sha(S/child.MANIFEST),backup=str(backup)))
print(json.dumps(child.preflight(S,'D:/FO3ID/32795'),ensure_ascii=True))
