"""Strict read-only shop -> roster -> startup -> optional catalogue composition."""
from pathlib import Path,PurePosixPath
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
MANIFEST='patches/startup-market-release-manifest.json';RECEIPT='patches/startup-market-release-installed.json'
PACK_MANIFEST='patches/pack-catalogue-release-manifest.json';PACK_RECEIPT='patches/pack-catalogue-release-installed.json'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise RuntimeError('Duplicate JSON metadata key')
            result[k]=v
        return result
    return json.loads(Path(p).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
def canonical(row):
    if row.get('root') not in ('server','client'):raise RuntimeError('Unknown resource root')
    text=row['relative'].replace('\\','/');rel=PurePosixPath(text)
    if rel.is_absolute() or not rel.parts or any(p in ('.','..') or ':' in p or p.endswith((' ','.')) for p in rel.parts):raise RuntimeError('Non-canonical relative resource path')
    return row['root'],rel.as_posix().casefold()
def path(roots,row):
    key=canonical(row);root=roots[key[0]];p=(root/row['relative'].replace('\\','/')).resolve()
    if p==root or not p.is_relative_to(root):raise RuntimeError('Resource path escape')
    return p
def table(rows):
    result={}
    for row in rows:
        key=canonical(row)
        if key in result:raise RuntimeError('Duplicate canonical resource target: '+str(key))
        result[key]=dict(row)
    return result
def receipt_identity(receipt,expected):
    if {k:v for k,v in receipt.items() if k!='native_status'}!=expected:raise RuntimeError('Stable installation receipt fields changed')
    if 'native_status' in receipt and not isinstance(receipt['native_status'],str):raise RuntimeError('Invalid informational native_status')
def replace(guards,rows,allow_external=None,allowed_targets=None):
    rows=table(rows);allow_external=allow_external or {}
    if allowed_targets is not None and set(rows)!=set(allowed_targets):raise RuntimeError('Unexpected delta target set')
    for key,e in rows.items():
        expected=guards[key]['sha256'] if key in guards else allow_external.get(key,'UNREGISTERED')
        if expected=='UNREGISTERED' or e.get('parent_sha256','MISSING')!=expected:raise RuntimeError('Delta parent SHA mismatch: '+str(key))
        guards[key]=dict(e)
def _compose(server,client,m,installed=True,include_pack=True):
    roots={'server':Path(server).resolve(),'client':Path(client).resolve()};guards={};ancestry=[];receipt_policies=[]
    parentrows=table([dict(root='server',relative=n,sha256=h) for n,h in m['parent_files'].items()])
    expected_parents={('server',n) for n in ('patches/shop-release-manifest.json','patches/shop-release-installed.json','patches/roster-release-manifest.json','patches/shop_release_preflight.py','patches/roster_release_preflight.py')}
    if set(parentrows)!=expected_parents:raise RuntimeError('Unexpected parent metadata/source set')
    for e in parentrows.values():
        if sha(path(roots,e))!=e['sha256']:raise RuntimeError('Frozen parent metadata/source changed: '+e['relative'])
    shop=read(roots['server']/'patches/shop-release-manifest.json');sr=read(roots['server']/'patches/shop-release-installed.json')
    if sr.get('status')!='INSTALLED' or sr.get('manifest_sha256')!=m['parent_files']['patches/shop-release-manifest.json'] or sr.get('release_id')!=shop['release_id']:raise RuntimeError('Shop receipt identity mismatch')
    proof=sr.get('native_proof',{});proofsha=hashlib.sha256(json.dumps(proof,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')).hexdigest()
    if proof.get('status')!='PASS' or proof.get('release_manifest_sha256')!=sr['manifest_sha256'] or proofsha!=m['shop_native_proof_sha256']:raise RuntimeError('Original shop native proof changed')
    guards=table(shop['files']+shop['unchanged'])
    roster=read(roots['server']/'patches/roster-release-manifest.json');rr=read(roots['server']/'patches/roster-release-installed.json')
    receipt_identity(rr,m['roster_receipt_installation_fields']);receipt_policies.append(dict(root='server',relative='patches/roster-release-installed.json',installation_fields=m['roster_receipt_installation_fields']))
    if rr.get('status')!='INSTALLED' or rr.get('manifest_sha256')!=m['parent_files']['patches/roster-release-manifest.json'] or rr.get('release_id')!=roster['release_id'] or roster.get('parent_shop_manifest_sha256')!=sr['manifest_sha256'] or roster.get('state_shop_replaced') is not False:raise RuntimeError('Roster ancestry mismatch')
    roster_rows=table(roster['files'])
    external={k:e['parent_sha256'] for k,e in table(m['roster_external_parents']).items()}
    replace(guards,roster['files'],external)
    rp=('server','patches/roster_release_preflight.py')
    if rp not in roster_rows or roster_rows[rp]['sha256']!=rr.get('preflight_sha256'):raise RuntimeError('Roster preflight identity mismatch')
    ancestry.extend([dict(layer='shop',manifest_sha256=sr['manifest_sha256'],native_status=proof['status']),dict(layer='roster',manifest_sha256=rr['manifest_sha256'],native_status=rr.get('native_status'),native_status_informational_only=True)])
    startup_rows=table(m['files']);allowed={('server','market_simulation.py'),('server','play-local.bat'),('server','patches/startup_market_preflight.py')}
    replace(guards,m['files'],{('server','patches/startup_market_preflight.py'):None},allowed)
    for key,e in parentrows.items():
        if key in guards and guards[key]['sha256']!=e['sha256']:raise RuntimeError('Parent source guard conflicts with composed layer')
        guards[key]=e
    if installed:
        receipt=read(roots['server']/RECEIPT)
        if receipt.get('status')!='INSTALLED_STARTUP_COMPATIBILITY' or receipt.get('release_id')!=m['release_id'] or receipt.get('manifest_sha256')!=sha(roots['server']/MANIFEST):raise RuntimeError('Startup delta receipt mismatch')
        if sha(roots['server']/'patches/startup_market_preflight.py')!=startup_rows[('server','patches/startup_market_preflight.py')]['sha256']:raise RuntimeError('Startup preflight source changed')
        for n in (MANIFEST,RECEIPT):guards[('server',n.casefold())]=dict(root='server',relative=n,sha256=sha(roots['server']/n))
    ancestry.append(dict(layer='startup',release_id=m['release_id'],market_behavior_certified=False))
    if include_pack:
        pm=roots['server']/PACK_MANIFEST;pr=roots['server']/PACK_RECEIPT
        if pm.exists()!=pr.exists():raise RuntimeError('Incomplete pack release metadata')
        if pm.exists():
            p=read(pm);r=read(pr);policy=m['pack_policy'];rows=table(p['files']);allow=table(policy['files'])
            if sha(pm)!=policy['manifest_sha256']:raise RuntimeError('Registered pack manifest changed; explicit rebase required')
            receipt_identity(r,policy['receipt_installation_fields']);receipt_policies.append(dict(root='server',relative=PACK_RECEIPT,installation_fields=policy['receipt_installation_fields']))
            if r.get('status')!='INSTALLED' or r.get('manifest_sha256')!=sha(pm) or r.get('release_id')!=p.get('release_id') or p.get('release_id')!=policy['release_id'] or p.get('parent_shop_manifest_sha256')!=sr['manifest_sha256'] or p.get('parent_roster_manifest_sha256')!=rr['manifest_sha256'] or p.get('state_shop_replaced') is not False:raise RuntimeError('Pack receipt/ancestry mismatch')
            if set(rows)!=set(allow):raise RuntimeError('Pack six-target whitelist mismatch')
            for key,e in rows.items():
                if e['sha256']!=allow[key]['sha256'] or e.get('parent_sha256')!=allow[key]['parent_sha256']:raise RuntimeError('Pack source/parent whitelist changed: '+str(key))
            replace(guards,p['files'],{k:e['parent_sha256'] for k,e in allow.items() if k not in guards},set(allow))
            helper=('server','patches/pack_catalogue_preflight.py')
            if sha(path(roots,rows[helper]))!=allow[helper]['sha256']:raise RuntimeError('Untrusted pack helper source')
            spec=importlib.util.spec_from_file_location('trusted_pack_catalogue_preflight',path(roots,rows[helper]));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
            actual=mod.validate(roots['server'],roots['client'])
            if actual!={k:e['sha256'] for k,e in rows.items()}:raise RuntimeError('Pack helper result differs from explicit approved manifest')
            guards[('server',PACK_MANIFEST.casefold())]=dict(root='server',relative=PACK_MANIFEST,sha256=sha(pm))
            ancestry.append(dict(layer='pack',manifest_sha256=sha(pm),native_status=r.get('native_status'),native_status_informational_only=True))
    return dict(schema=1,guards=list(guards.values()),receipt_policies=receipt_policies,ancestry=ancestry,files_verified=False,server=str(roots['server']),client=str(roots['client']))
def compose_manifest(server=None,client=None):
    server=Path(server or HERE.parent).resolve();m=read(server/MANIFEST);return _compose(server,client or m['client_root'],m)
def verify_manifest(composed,server=None,client=None):
    roots={'server':Path(server or composed['server']).resolve(),'client':Path(client or composed['client']).resolve()}
    for e in table(composed['guards']).values():
        p=path(roots,e)
        if not p.is_file() or sha(p)!=e['sha256']:raise RuntimeError('Composed installed file differs: '+e['root']+'/'+e['relative'])
    for policy in composed.get('receipt_policies',[]):receipt_identity(read(path(roots,policy)),policy['installation_fields'])
    return dict(status='READ_ONLY_SHOP_ROSTER_STARTUP_PREFLIGHT_PASS',files=len(composed['guards']),files_verified=True,ancestry=composed['ancestry'],state_shop_touched=False)
def preflight(server=None,client=None,additional_replacements=None):
    if additional_replacements is not None:raise RuntimeError('Unregistered additional replacements are forbidden; use a separately sealed explicit child manifest')
    return verify_manifest(compose_manifest(server,client))
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
