"""Read-only guard for withdrawn legacy chain storefront entries."""
from pathlib import Path
import hashlib,json
MANIFEST="patches/legacy-chain-installed.json"
RECEIPT="patches/legacy-chain-receipt.json"
SELF="patches/legacy_chain_preflight.py"
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/'patches/legacy-chain-installed.json').read_text('utf-8'))
    receipt=json.loads((server/RECEIPT).read_text('utf-8'))
    if receipt.get('status')!='INSTALLED_LEGACY_CHAIN_HIDE' or receipt.get('manifest_sha256')!=sha(server/MANIFEST) or receipt.get('revision')!=m['revision']:raise RuntimeError('Database receipt mismatch')
    if m.get('schema')!=1 or m.get('state_shop_replaced') is not False:raise RuntimeError('Wrong database scope')
    roots=dict(server=server,client=Path(client or m['client']).resolve());seen=set()
    for r in m['guards']:
        root=roots[r['root']];target=(root/r['relative']).resolve();key=(r['root'],r['relative'].replace('\\','/').casefold())
        if not target.is_relative_to(root) or target==root or key in seen:raise RuntimeError('Invalid database guard')
        seen.add(key)
        if not target.is_file() or sha(target)!=r['sha256']:raise RuntimeError('Installed file differs: '+r['root']+'/'+r['relative'])
    required={('server','http_config.py'),('server','legacy_chain_hide.py'),('server','play-local.bat'),('server',SELF)}
    if not required<=seen:raise RuntimeError('Incomplete database guards')
    for policy in m.get('composition',{}).get('receipt_policies',[]):
        root=roots[policy['root']];path=(root/policy['relative']).resolve()
        if not path.is_relative_to(root):raise RuntimeError('Receipt path escape')
        receipt=json.loads(path.read_text('utf-8-sig'))
        if {k:v for k,v in receipt.items() if k!='native_status'}!=policy['installation_fields']:raise RuntimeError('Parent installation receipt changed')
    return dict(status='LEGACY_CHAIN_HIDE_PREFLIGHT_PASS',files=len(seen),revision=m['revision'],native_status='PENDING',state_shop_touched=False)
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))

def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/'patches/legacy-chain-installed.json').read_text('utf-8'))
    c=dict(m.get('composition') or {})
    guards=list(m['guards'])
    for name in (MANIFEST,RECEIPT):guards.append(dict(root='server',relative=name,sha256=sha(server/name)))
    c.update(server=str(server),client=str(Path(client or m['client']).resolve()),guards=guards)
    c.setdefault('ancestry',[])
    c.setdefault('receipt_policies',[])
    return c
