from pathlib import Path
import json,hashlib,importlib.util
S=Path('D:/FO3ID/server')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(p,name):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')
p=module(S/'patches/moments_display_preflight.py','moments_parent');c,v=p._compose(S,'D:/FO3ID/32795');g=v.table(c['guards'])
child=module(S/'patches/player_editor_current_preflight.py','editor_current')
launcher=S/'play-local.bat';content=launcher.read_bytes();assert b'patches\\moments_display_preflight.py' in content
launcher.write_bytes(content.replace(b'patches\\moments_display_preflight.py',b'patches\\player_editor_current_preflight.py'))
rows=[dict(root=root,relative=rel,parent_sha256=g.get((root,rel.casefold()),{}).get('sha256'),sha256=sha(S/rel)) for root,rel in sorted(child.ALLOWED)]
m=dict(phase='PLAYER_EDITOR_CURRENT_LAUNCHER',state_shop_replaced=False,client_root='D:/FO3ID/32795',files=rows,
       parent_files={n:sha(S/n) for n in (child.PARENT,'patches/moments-display-release-manifest.json','patches/moments-display-release-installed.json')})
write(S/child.MANIFEST,m);write(S/child.RECEIPT,dict(status='INSTALLED_PLAYER_EDITOR_CURRENT',manifest_sha256=sha(S/child.MANIFEST)))
print(child.preflight(S,'D:/FO3ID/32795')['status'])
