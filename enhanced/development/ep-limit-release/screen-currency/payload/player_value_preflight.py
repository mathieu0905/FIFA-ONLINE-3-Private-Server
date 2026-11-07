"""Exact display-only child over the installed background-market layer."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
MANIFEST='patches/currency-screen-release-manifest.json'
RECEIPT='patches/currency-screen-release-installed.json'
SELF='patches/currency_screen_preflight.py'
PARENT='patches/moments_display_preflight.py'
PARENT_FILES={PARENT,'patches/moments-display-release-manifest.json','patches/moments-display-release-installed.json'}
ALLOWED={('server','play-local.bat'),('server',SELF)}|{('client','data/ui/'+n) for n in ('menuscreen.big','startupcoachcreationscreen.big','startuptest.big')}
EXTERNAL={('server',SELF):None,
 ('client','data/ui/menuscreen.big'):'b7a0e0630009a2ce005869b38116416b94b01303f76235cd8ceb540f1975bf11',
 ('client','data/ui/startupcoachcreationscreen.big'):'1eaf7549bea3a980fab921c705373f8fe8f2a58a6fb67050dc713426b1c71f4f',
 ('client','data/ui/startuptest.big'):'dd255cabbb689d725d79e405884863df22e9e0ca385b7c2b3be77c8e5fcf4a43'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise RuntimeError('Duplicate currency screen key')
            out[k]=v
        return out
    return json.loads(Path(p).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
def parent(server,m):
    if set(m['parent_files'])!=PARENT_FILES:raise RuntimeError('Wrong market parent identity set')
    for n,h in m['parent_files'].items():
        if sha(server/n)!=h:raise RuntimeError('Market parent changed: '+n)
    spec=importlib.util.spec_from_file_location('currency_screen_parent',server/PARENT)
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);return p
def _compose(server,client,m=None,installed=True):
    server=Path(server).resolve();client=Path(client).resolve();m=m or read(server/MANIFEST)
    if m.get('phase')!='CURRENCY_SCREEN_COMMA_PATHS' or m.get('state_shop_replaced') is not False:raise RuntimeError('Wrong display scope')
    p=parent(server,m);c,v=p._compose(server,client);g=v.table(c['guards'])
    if set(v.table(m['files']))!=ALLOWED:raise RuntimeError('Screen currency whitelist changed')
    v.replace(g,m['files'],EXTERNAL,ALLOWED)
    if installed:
        r=read(server/RECEIPT)
        if r.get('status')!='INSTALLED_CURRENCY_SCREEN' or r.get('release_id')!=m['release_id'] or r.get('manifest_sha256')!=sha(server/MANIFEST):raise RuntimeError('Currency screen receipt mismatch')
        for n in (MANIFEST,RECEIPT):g[('server',n)]=dict(root='server',relative=n,sha256=sha(server/n))
    c['guards']=list(g.values());c['ancestry'].append(dict(layer='currency-screen-comma-paths',prices_changed=False,native_status='SEE_SEPARATE_NATIVE_REPORT'))
    return c,v
def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST)
    return _compose(server,client or m['client_root'],m)[0]
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST)
    c,v=_compose(server,client or m['client_root'],m)
    result=v.verify_manifest(c,server,client or m['client_root']);result['status']='READ_ONLY_CURRENCY_SCREEN_PASS';return result
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
