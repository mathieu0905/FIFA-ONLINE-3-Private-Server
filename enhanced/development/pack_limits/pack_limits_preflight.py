"""Compose the purchase-limit delta over the installed XP30 release."""
from pathlib import Path
import hashlib, importlib.util, json

SELF='patches/pack_limits_preflight.py'
MANIFEST='patches/pack-limits-release-manifest.json'
RECEIPT='patches/pack-limits-release-installed.json'
ALLOWED={('server','gamedata/pack_cadence.json'),('server','gamedata/pack_catalogue.json'),('server',SELF),('server','play-local.bat')}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def _compose(server,client,m,installed=True):
    server,client=Path(server).resolve(),Path(client).resolve()
    if set(m['parents'])!={'patches/xp30_batch_preflight.py','patches/xp30-batch-release-manifest.json'}:
        raise RuntimeError('Unexpected quota parent set')
    for name,digest in m['parents'].items():
        if sha(server/name)!=digest:raise RuntimeError('Quota ancestor changed: '+name)
    spec=importlib.util.spec_from_file_location('quota_xp_parent',server/'patches/xp30_batch_preflight.py')
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    composed,verifier=parent._compose(server,client,parent.read(server/parent.MANIFEST))
    guards=verifier.table(composed['guards']);rows=verifier.table(m['files'])
    if set(rows)!=ALLOWED:raise RuntimeError('Quota delta target scope differs')
    verifier.replace(guards,m['files'],{('server',SELF):None},ALLOWED)
    if m.get('draw_rules_changed') is not False or m.get('state_replaced') is not False:
        raise RuntimeError('Quota delta cannot change draws or player assets')
    # Independently prove the installed JSONs only change limits and supply text.
    backup=Path(m['backup']).resolve()
    if not backup.is_relative_to(server/'backups'):raise RuntimeError('Invalid quota backup root')
    for filename in ('pack_cadence.json','pack_catalogue.json'):
        oldpath=backup/filename;newpath=server/'gamedata'/filename
        row=rows[('server','gamedata/'+filename)]
        if sha(oldpath)!=row['parent_sha256']:raise RuntimeError('Quota original backup changed')
        old,new=read(oldpath),read(newpath)
        if new['limits']!=m['limits'][filename]:raise RuntimeError('Quota limits differ from published values')
        old.pop('hash');new.pop('hash')
        if filename=='pack_catalogue.json':
            for key,item in new['items'].items():
                item['description']=old['items'][key]['description']
        new['limits']=old['limits']
        if new!=old:raise RuntimeError('Non-quota draw/price/version changes found')
    if installed:
        receipt=read(server/RECEIPT)
        if receipt.get('status')!='INSTALLED' or receipt.get('manifest_sha256')!=sha(server/MANIFEST):
            raise RuntimeError('Quota receipt mismatch')
        for name in (MANIFEST,RECEIPT):guards[('server',name)]=dict(root='server',relative=name,sha256=sha(server/name))
    composed['guards']=list(guards.values())
    composed['ancestry'].append(dict(layer='pack_purchase_limits',release_id=m['release_id'],native_verified=False))
    return composed,verifier

def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=read(server/MANIFEST)
    return _compose(server,client or m['client_root'],m)[0]

def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve();m=read(server/MANIFEST)
    c,p=_compose(server,client or m['client_root'],m)
    out=p.verify_manifest(c,server,client or m['client_root']);out['status']='READ_ONLY_PACK_LIMITS_PREFLIGHT_PASS'
    return out

if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True))
