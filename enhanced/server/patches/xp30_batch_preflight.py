# Main-version complete XP30/batch plus AI-filter resource delta; historical layers remain unchanged.
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
MANIFEST='patches/xp30-batch-release-manifest.json'
RECEIPT='patches/xp30-batch-release-installed.json'
SELF='patches/xp30_batch_preflight.py'
PARENT='patches/startup_market_preflight.py'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def parent(server,m):
    expected={'patches/startup_market_preflight.py','patches/startup-market-release-manifest.json','patches/startup-market-release-installed.json'}
    if set(m['parent_startup_files'])!=expected:raise RuntimeError('Unexpected A parent identity set')
    for n,h in m['parent_startup_files'].items():
        if sha(server/n)!=h:raise RuntimeError('Main XP30 startup parent changed: '+n)
    if sha(server/PARENT)!='49eafb6eaa5ec954bfc65c4460aec2a3f14e9bb93dbbf6547cedfded44393d8a':raise RuntimeError('Unexpected startup composer source')
    spec=importlib.util.spec_from_file_location('frozen_main_a_parent',server/PARENT);p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    return p

def compose_ancestors(p,server,client):
    cfg=p.read(server/'patches/startup-market-release-manifest.json')
    c=p._compose(server,client,cfg,installed=True,include_pack=False);guards=p.table(c['guards'])
    policy=cfg['pack_policy'];pm=server/p.PACK_MANIFEST;pr=server/p.PACK_RECEIPT;pack=p.read(pm);receipt=p.read(pr)
    if p.sha(pm)!=policy['manifest_sha256']:raise RuntimeError('Frozen pack manifest changed')
    p.receipt_identity(receipt,policy['receipt_installation_fields'])
    if receipt.get('status')!='INSTALLED' or receipt.get('manifest_sha256')!=p.sha(pm) or receipt.get('release_id')!=pack.get('release_id') or pack.get('release_id')!=policy['release_id'] or pack.get('state_shop_replaced') is not False:raise RuntimeError('Pack release identity mismatch')
    if pack.get('parent_shop_manifest_sha256')!=cfg['parent_files']['patches/shop-release-manifest.json'] or pack.get('parent_roster_manifest_sha256')!=cfg['parent_files']['patches/roster-release-manifest.json']:raise RuntimeError('Pack ancestry changed')
    rows=p.table(pack['files']);approved=p.table(policy['files'])
    allowed={('server','http_config.py'),('server','shop_season_names.py'),('server','pack_catalogue.py'),('server','gamedata/pack_catalogue.json'),('server','patches/pack_catalogue_preflight.py'),('client','data/ui/teammanagementdraftpackscreen.big')}
    if set(rows)!=allowed or set(approved)!=allowed:raise RuntimeError('Pack exact six-target scope changed')
    backup=Path(receipt['backup']).resolve()
    if not backup.is_relative_to(server/'backups'):raise RuntimeError('Pack parent backup escapes server')
    for k,e in rows.items():
        if e['sha256']!=approved[k]['sha256'] or e.get('parent_sha256')!=approved[k].get('parent_sha256'):raise RuntimeError('Pack frozen source/parent changed')
        if e['parent_sha256'] is not None:
            before=p.path({'server':backup/'server','client':backup/'client'},e)
            if p.sha(before)!=e['parent_sha256']:raise RuntimeError('Pack parent backup changed')
    helper=('server','patches/pack_catalogue_preflight.py')
    if p.sha(p.path({'server':server,'client':client},rows[helper]))!=approved[helper]['sha256']:raise RuntimeError('Frozen pack helper source changed')
    p.replace(guards,pack['files'],{k:e['parent_sha256'] for k,e in approved.items() if k not in guards},allowed)
    guards[('server',p.PACK_MANIFEST)]=dict(root='server',relative=p.PACK_MANIFEST,sha256=p.sha(pm))
    c['receipt_policies'].append(dict(root='server',relative=p.PACK_RECEIPT,installation_fields=policy['receipt_installation_fields']))
    c['ancestry'].append(dict(layer='pack',manifest_sha256=p.sha(pm),native_status=receipt.get('native_status'),native_status_informational_only=True,metadata_projection_only=True))
    c['guards']=list(guards.values())
    return c

def _compose(server,client,m,installed=True):
    server=Path(server).resolve();client=Path(client).resolve()
    if installed:
        receipt=read(server/RECEIPT)
        if receipt.get('status')!='INSTALLED_MAIN_XP30_BATCH' or receipt.get('manifest_sha256')!=sha(server/MANIFEST) or receipt.get('release_id')!=m['release_id'] or receipt.get('backend_changed') is not True or receipt.get('exp_ui_changed') is not True:raise RuntimeError('XP installed receipt scope mismatch before parent import')
    p=parent(server,m)
    if m.get('phase')!='MAIN_XP30_BATCH' or m.get('exp_ui_changed') is not True or m.get('backend_changed') is not True:raise RuntimeError('Unexpected main A scope')
    composed=compose_ancestors(p,server,client);guards=p.table(composed['guards'])
    allowed={('client','data/ui/libs/module.big'),('client','data/ui/teammanagementexpcapsulescreen.big'),('server','http_config.py'),('server','experience_levels.py'),('server','play-local.bat'),('server',SELF)}
    if m['module_before']!='8e43a56e49ffce13a1de30d8c40a075e7df7ef12a7d4015d2f6c4c087579b05d' or m['module_after']!='56e03cfb7c55bada0704c7f6ed8a91e41a838602f02f77c14248c0f77944923e':raise RuntimeError('Wrong main A Module pair')
    rows=p.table(m['files'])
    fixed={('server','http_config.py'):'36b07f5198fcdbcaaab37c1833ab583a46cb31f82890516eebb2d3004f313b64',('server','experience_levels.py'):'8873024c9fbbbf8190bc1c080e4f2d958f8dd52064500295d4306f6eacbb5f1d',('client','data/ui/teammanagementexpcapsulescreen.big'):'1f39daf0895e1ac9de84f49873b9b91f12580093eda09be9c8143ab7516430c5'}
    if any(rows.get(k,{}).get('sha256')!=h for k,h in fixed.items()):raise RuntimeError('Wrong final XP payload identity')
    if rows.get(('client','data/ui/libs/module.big'),{}).get('parent_sha256')!=m['module_before'] or rows[('client','data/ui/libs/module.big')]['sha256']!=m['module_after']:raise RuntimeError('Wrong Module ancestry')
    p.replace(guards,m['files'],{('server',SELF):None,('server','experience_levels.py'):m['backend_before']},allowed)
    for e in m['invariants']:
        k=p.canonical(e)
        if k not in guards or guards[k]['sha256']!=e['sha256']:raise RuntimeError('Main XP30 immutable prerequisite differs')
    if installed:
        r=read(server/RECEIPT)
        if r.get('status')!='INSTALLED_MAIN_XP30_BATCH' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('release_id')!=m['release_id']:raise RuntimeError('Main XP30 receipt mismatch')
        for n in (MANIFEST,RECEIPT):guards[('server',n)]=dict(root='server',relative=n,sha256=sha(server/n))
        composed['ancestry'].append(dict(layer='main-XP30-batch',native_status=r.get('native_status'),native_status_informational_only=True,server_cap_changed=True,exp_ui_changed=True))
    composed['guards']=list(guards.values());composed['files_verified']=False
    return composed,p
def compose_manifest(server=None,client=None):
    server=Path(server or HERE.parent).resolve();m=read(server/MANIFEST)
    return _compose(server,client or m['client_root'],m)[0]
def preflight(server=None,client=None):
    server=Path(server or HERE.parent).resolve();m=read(server/MANIFEST);c,p=_compose(server,client or m['client_root'],m)
    result=p.verify_manifest(c,server,client or m['client_root'])
    result['status']='READ_ONLY_MAIN_XP30_BATCH_PREFLIGHT_PASS'
    return result
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))