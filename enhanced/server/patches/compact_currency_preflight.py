"""Currency display child; no price, shop, wallet or XP behavior changes."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
MANIFEST='patches/compact-currency-release-manifest.json'
RECEIPT='patches/compact-currency-release-installed.json'
SELF='patches/compact_currency_preflight.py'
PARENT='patches/fc_retirement_preflight.py'
ALLOWED={('server','play-local.bat'),('server',SELF),('client','data/ui/libs/module.big'),
         ('client','data/ui/localization/fontconfig.dat')}
PARENT_FILES={PARENT,'patches/fc-retirement-release-manifest.json','patches/fc-retirement-release-installed.json'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise RuntimeError('Duplicate currency release key')
            out[k]=v
        return out
    return json.loads(Path(p).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
def parent(server,m):
    if set(m['parent_files'])!=PARENT_FILES:raise RuntimeError('Wrong valuation parent identity')
    for n,h in m['parent_files'].items():
        if sha(server/n)!=h:raise RuntimeError('Valuation parent changed: '+n)
    spec=importlib.util.spec_from_file_location('currency_parent',server/PARENT)
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);return p

def compose_retirement(server,client,p):
    # This installed parent exposes only physical preflight, not pure compose.
    # Project its exact reviewed source's rules without editing old metadata.
    if sha(server/PARENT)!='936b6fc76769b79d3c5244a823308a8cca18fed20d564f4b1a9c60c91621ccab':raise RuntimeError('Unreviewed retirement composer')
    m=p.read(server/p.MANIFEST)
    for n,h in m['parent_files'].items():
        if sha(server/n)!=h:raise RuntimeError('Retirement ancestor changed: '+n)
    spec=importlib.util.spec_from_file_location('frozen_value_ancestor',server/'patches/player_value_preflight.py')
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    c,v=previous._compose(server,client);g=v.table(c['guards'])
    if set(v.table(m['files']))!=p.ALLOWED:raise RuntimeError('Retirement target policy changed')
    v.replace(g,m['files'],{('server',p.SELF):None},p.ALLOWED)
    r=p.read(server/p.RECEIPT)
    if r.get('status')!='INSTALLED_FC13_RETIREMENT' or r.get('manifest_sha256')!=sha(server/p.MANIFEST):raise RuntimeError('Retirement receipt mismatch')
    for n in (p.MANIFEST,p.RECEIPT):g[('server',n.casefold())]=dict(root='server',relative=n,sha256=sha(server/n))
    registry=p.read(server/'gamedata/custom_rosters.json')
    if 13028130 in {r['fo3_spid'] for r in registry['cards']} or len(next(s for s in registry['seasons'] if s['id']==13)['cards'])!=257:raise RuntimeError('Retirement registry contract changed')
    c['guards']=list(g.values());return c,v
def _compose(server,client,m=None,installed=True):
    server=Path(server).resolve();client=Path(client).resolve();m=m or read(server/MANIFEST)
    if m.get('phase')!='CURRENCY_COMPACT_MODULE_FONT' or m.get('state_shop_replaced') is not False:raise RuntimeError('Wrong currency scope')
    p=parent(server,m);c,v=compose_retirement(server,client,p)
    g=v.table(c['guards']);rows=v.table(m['files'])
    if set(rows)!=ALLOWED:raise RuntimeError('Currency display whitelist changed')
    external={('server',SELF):None,('client','data/ui/localization/fontconfig.dat'):m['fontconfig_parent_sha256']}
    v.replace(g,m['files'],external,ALLOWED)
    if installed:
        r=read(server/RECEIPT)
        if r.get('status')!='INSTALLED_CURRENCY_COMPACT' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('release_id')!=m['release_id']:raise RuntimeError('Currency receipt mismatch')
        for n in (MANIFEST,RECEIPT):g[('server',n)]=dict(root='server',relative=n,sha256=sha(server/n))
    c['guards']=list(g.values());c['ancestry'].append(dict(layer='compact-currency-chinese-font',native_status='SEE_SEPARATE_NATIVE_REPORT',prices_changed=False))
    return c,v
def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST)
    return _compose(server,client or m['client_root'],m)[0]
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent);m=read(server/MANIFEST)
    c,v=_compose(server,client or m['client_root'],m)
    out=v.verify_manifest(c,server,client or m['client_root']);out['status']='READ_ONLY_COMPACT_CURRENCY_PASS';return out
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
