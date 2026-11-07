"""Exact additive 8088 player editor layer over the installed market worker."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
MANIFEST='patches/player-editor-release-manifest.json'
RECEIPT='patches/player-editor-release-installed.json'
SELF='patches/player_editor_preflight.py'
PARENT='patches/market_background_preflight.py'
PACKAGE=('__init__.py','player_database.py','publish_database.py','database_preflight.py','ordered_big.py','run_publish.py','index.html')
ALLOWED={('server',n) for n in ('admin.py','admin/index.html','play-local.bat',SELF)+tuple('player_editor/'+n for n in PACKAGE)}
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def _compose(server,client):
    server=Path(server).resolve();m=read(server/MANIFEST)
    required={PARENT,'patches/market-background-release-manifest.json','patches/market-background-release-installed.json'}
    if m.get('phase')!='NATIVE_8088_PLAYER_EDITOR' or m.get('state_shop_replaced') is not False or set(m['parent_files'])!=required:raise RuntimeError('Wrong player editor release scope')
    for n,h in m['parent_files'].items():
        if sha(server/n)!=h:raise RuntimeError('Player editor parent changed: '+n)
    spec=importlib.util.spec_from_file_location('player_editor_parent',server/PARENT);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    c,v=p._compose(server,client);g=v.table(c['guards'])
    external={k:None for k in ALLOWED if k not in g}
    v.replace(g,m['files'],external,ALLOWED)
    r=read(server/RECEIPT)
    if r.get('status')!='INSTALLED_8088_PLAYER_EDITOR' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('release_id')!=m['release_id']:raise RuntimeError('Player editor receipt mismatch')
    for n in (MANIFEST,RECEIPT):g[('server',n)]=dict(root='server',relative=n,sha256=sha(server/n))
    c['guards']=list(g.values());c['ancestry'].append(dict(layer='native-8088-player-editor',state_shop_replaced=False))
    return c,v
def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST)
    return _compose(server,client or m['client_root'])[0]
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST)
    c,v=_compose(server,client or m['client_root']);out=v.verify_manifest(c,server,client or m['client_root']);out['status']='NATIVE_8088_PLAYER_EDITOR_PASS';return out
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
