"""Current-launcher validation support, preserving concurrent moments display."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
MANIFEST='patches/player-editor-save-manifest.json'
RECEIPT='patches/player-editor-save-installed.json'
SELF='patches/player_editor_save_preflight.py'
PARENT='patches/market_discovery_preflight.py'
ALLOWED={('server', 'player_editor/publish_database.py'), ('server', 'player_editor/player_database.py'), ('server', 'patches/player_editor_save_preflight.py'), ('server', 'player_editor/database_preflight.py'), ('server', 'player_editor/__init__.py'), ('server', 'play-local.bat'), ('server', 'player_editor/index.html')}
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def _compose(server,client):
    server=Path(server).resolve();m=read(server/MANIFEST)
    if m.get('phase')!='PLAYER_EDITOR_ONE_CLICK_SAVE' or m.get('state_shop_replaced') is not False:raise RuntimeError('Wrong current editor scope')
    required={'patches/market_discovery_preflight.py', 'patches/market-discovery-release-installed.json', 'patches/market-discovery-release-manifest.json'}
    if set(m['parent_files'])!=required:raise RuntimeError('Wrong current editor parent set')
    for n,h in m['parent_files'].items():
        if sha(server/n)!=h:raise RuntimeError('Current editor parent changed: '+n)
    spec=importlib.util.spec_from_file_location('current_editor_parent',server/PARENT);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    c=p.compose_manifest(server,client);vs=importlib.util.spec_from_file_location('direct_save_validator',server/'patches/startup_market_preflight.py');v=importlib.util.module_from_spec(vs);vs.loader.exec_module(v);g=v.table(c['guards']);v.replace(g,m['files'],{('server',SELF):None},ALLOWED)
    r=read(server/RECEIPT)
    if r.get('status')!='INSTALLED_PLAYER_EDITOR_SAVE' or r.get('manifest_sha256')!=sha(server/MANIFEST):raise RuntimeError('Current editor receipt mismatch')
    for n in (MANIFEST,RECEIPT):g[('server',n)]=dict(root='server',relative=n,sha256=sha(server/n))
    c['guards']=list(g.values());return c,v
def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST);return _compose(server,client or m['client_root'])[0]
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST);c,v=_compose(server,client or m['client_root']);out=v.verify_manifest(c,server,client or m['client_root']);out['status']='PLAYER_EDITOR_DIRECT_SAVE_PASS';return out
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True))
