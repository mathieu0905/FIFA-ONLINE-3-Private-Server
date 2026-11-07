"""Exact child of the installed console/bulk layer; read-only validation."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
MANIFEST='patches/player-value-release-manifest.json'
RECEIPT='patches/player-value-release-installed.json'
SELF='patches/player_value_preflight.py'
PARENT='patches/console_backpressure_preflight.py'
ALLOWED={('server',n) for n in ('admin.py','admin_grant_guard.py','admin/index.html','http_config.py',
          'market_simulation.py','play-local.bat','patches/label.big',SELF)}|{('client','data/ui/components/label.big')}
PARENT_FILES={PARENT,'patches/console-backpressure-release-manifest.json','patches/console-backpressure-release-installed.json'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise RuntimeError('Duplicate release key: '+k)
            out[k]=v
        return out
    return json.loads(Path(p).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
def parent(server,m):
    if set(m['parent_files'])!=PARENT_FILES:raise RuntimeError('Wrong parent identity set')
    for n,digest in m['parent_files'].items():
        if sha(server/n)!=digest:raise RuntimeError('Parent changed: '+n)
    spec=importlib.util.spec_from_file_location('player_value_parent',server/PARENT)
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);return p
def _compose(server,client,m=None,installed=True):
    server=Path(server).resolve();client=Path(client).resolve();m=m or read(server/MANIFEST)
    if m.get('phase')!='PLAYER_VALUE_DIV1000_EP_ADMIN_COMPACT' or m.get('state_shop_replaced') is not False:
        raise RuntimeError('Wrong player valuation release scope')
    p=parent(server,m);c,v=p._compose(server,client,p.read(server/p.MANIFEST))
    guards=v.table(c['guards']);rows=v.table(m['files'])
    if set(rows)!=ALLOWED:raise RuntimeError('Player valuation whitelist changed')
    v.replace(guards,m['files'],{('server',SELF):None},ALLOWED)
    if installed:
        r=read(server/RECEIPT)
        if r.get('status')!='INSTALLED_PLAYER_VALUE_DIV1000' or r.get('release_id')!=m['release_id'] or r.get('manifest_sha256')!=sha(server/MANIFEST):
            raise RuntimeError('Player valuation receipt mismatch')
        for n in (MANIFEST,RECEIPT):guards[('server',n)]=dict(root='server',relative=n,sha256=sha(server/n))
    c['guards']=list(guards.values());c['ancestry'].append(dict(layer='player-value-div1000',
        balance_scaled=False,shop_prices_changed=False,admin_ep_limit=10**18,native_status='SEE_SEPARATE_NATIVE_REPORT'))
    return c,v
def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST)
    return _compose(server,client or m['client_root'],m)[0]
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST)
    c,v=_compose(server,client or m['client_root'],m)
    result=v.verify_manifest(c,server,client or m['client_root']);result['status']='READ_ONLY_PLAYER_VALUE_DIV1000_PASS'
    return result
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
