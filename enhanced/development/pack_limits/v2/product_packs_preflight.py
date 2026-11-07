"""Read-only composition of independent pack policy over the reviewed current main release."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
MANIFEST='patches/product-packs-release-manifest.json'
RECEIPT='patches/product-packs-release-installed.json'
SELF='patches/product_packs_preflight.py'
TARGETS={('server',n) for n in ('http_config.py','pack_catalogue.py','product_packs.py','pack_probability.py','admin.py','admin/index.html','gamedata/product_packs.json','play-local.bat',SELF)}|{('client','data/ui/teammanagementdraftpackscreen.big')}

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def read(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise RuntimeError('Duplicate metadata key')
            result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)

def project_parent(parent,server,client,parent_manifest):
    if hasattr(parent,'_compose'):
        import inspect
        parameters=inspect.signature(parent._compose).parameters
        if 'm' in parameters or 'manifest' in parameters:
            return parent._compose(server,client,parent_manifest,**({'installed':True} if 'installed' in parameters else {}))
        return parent._compose(server,client)
    # Exact reviewed metadata projection of the frozen retirement-only parent.
    # It is identical to that parent's preflight through guard construction;
    # physical verification is deferred until the final composed child.
    if Path(parent.__file__).name!='fc_retirement_preflight.py':raise RuntimeError('Parent needs reviewed pure projection')
    m=parent_manifest
    for name,digest in m['parent_files'].items():
        if sha(server/name)!=digest:raise RuntimeError('FC retirement parent changed: '+name)
    spec=importlib.util.spec_from_file_location('fc_projection_parent',server/'patches/player_value_preflight.py')
    ep=importlib.util.module_from_spec(spec);spec.loader.exec_module(ep)
    c,v=ep._compose(server,client);guards=v.table(c['guards'])
    if set(v.table(m['files']))!=parent.ALLOWED:raise RuntimeError('Wrong retirement scope')
    v.replace(guards,m['files'],{('server',parent.SELF):None},parent.ALLOWED)
    receipt=read(server/parent.RECEIPT)
    if receipt['status']!='INSTALLED_FC13_RETIREMENT' or receipt['manifest_sha256']!=sha(server/parent.MANIFEST):raise RuntimeError('Retirement receipt mismatch')
    for name in (parent.MANIFEST,parent.RECEIPT):guards[('server',name.casefold())]=dict(root='server',relative=name,sha256=sha(server/name))
    registry=read(server/'gamedata/custom_rosters.json')
    if 13028130 in {r['fo3_spid'] for r in registry['cards']} or len(next(s for s in registry['seasons'] if s['id']==13)['cards'])!=257:raise RuntimeError('FC retirement roster invariant failed')
    c['guards']=list(guards.values())
    return c,v

def _compose(server,client,m=None,installed=True):
    server=Path(server).resolve();client=Path(client).resolve();m=m or read(server/MANIFEST)
    if m.get('phase')!='INDEPENDENT_PRODUCT_PACKS' or m.get('state_shop_replaced') is not False:
        raise RuntimeError('Unexpected product policy release scope')
    for name,digest in m['parent_identity'].items():
        if sha(server/name)!=digest:raise RuntimeError('Protected parent changed: '+name)
    parent_path=server/m['parent_preflight']
    if not parent_path.resolve().is_relative_to(server/'patches'):raise RuntimeError('Invalid parent path')
    spec=importlib.util.spec_from_file_location('product_parent',parent_path)
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    # Parent composers are pure; only this final child verifies physical payloads.
    parent_manifest=read(server/m['parent_manifest'])
    c,v=project_parent(parent,server,client,parent_manifest)
    guards=v.table(c['guards']);rows=v.table(m['files'])
    if set(rows)!=TARGETS:raise RuntimeError('Unexpected product policy target set')
    external={key:row['parent_sha256'] for key,row in rows.items() if key not in guards}
    v.replace(guards,m['files'],external,TARGETS)
    if installed:
        receipt=read(server/RECEIPT)
        if receipt!=dict(status='INSTALLED_INDEPENDENT_PRODUCT_PACKS',release_id=m['release_id'],manifest_sha256=sha(server/MANIFEST),state_shop_replaced=False):
            raise RuntimeError('Product policy receipt identity mismatch')
        for name in (MANIFEST,RECEIPT):guards[('server',name)]=dict(root='server',relative=name,sha256=sha(server/name))
        c['ancestry'].append(dict(layer='independent-product-packs',native_status_informational_only=True))
    c['guards']=list(guards.values());c['files_verified']=False
    return c,v

def compose_manifest(server=None,client=None):
    server=Path(server or HERE.parent).resolve();m=read(server/MANIFEST)
    return _compose(server,client or m['client_root'],m)[0]

def preflight(server=None,client=None):
    server=Path(server or HERE.parent).resolve();m=read(server/MANIFEST);client=Path(client or m['client_root'])
    c,v=_compose(server,client,m);result=v.verify_manifest(c,server,client)
    result['status']='READ_ONLY_INDEPENDENT_PRODUCT_PACKS_PASS'
    return result

if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
