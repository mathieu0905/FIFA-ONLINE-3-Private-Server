"""Read-only exact guard for the shop value callback revision."""
from pathlib import Path
import hashlib,json
MANIFEST='patches/shop-value-installed.json'
RECEIPT='patches/shop-value-receipt.json'
SELF='patches/shop_value_preflight.py'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/MANIFEST).read_text('utf-8'))
    r=json.loads((server/RECEIPT).read_text('utf-8'))
    if m.get('schema')!=1 or m.get('state_shop_replaced') is not False:raise RuntimeError('Invalid shop value scope')
    if r.get('status')!='INSTALLED_SHOP_VALUE' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('revision')!=m['revision']:raise RuntimeError('Shop value receipt mismatch')
    roots=dict(server=server,client=Path(client or m['client']).resolve());seen=set()
    for g in m['guards']:
        root=roots[g['root']];p=(root/g['relative']).resolve();key=(g['root'],g['relative'].replace('\\','/').casefold())
        if not p.is_relative_to(root) or p==root or key in seen:raise RuntimeError('Invalid shop value guard')
        seen.add(key)
        if not p.is_file() or sha(p)!=g['sha256']:raise RuntimeError('Installed file differs: '+str(key))
    required={('server',x) for x in ('product_packs.py','pack_value.py','gamedata/shop_value_products.json','play-local.bat',SELF.casefold())}
    if not required<=seen:raise RuntimeError('Incomplete shop value guards')
    for policy in m.get('composition',{}).get('receipt_policies',[]):
        root=roots[policy['root']];p=(root/policy['relative']).resolve()
        if not p.is_relative_to(root):raise RuntimeError('Receipt path escape')
        receipt=json.loads(p.read_text('utf-8-sig'))
        if {k:v for k,v in receipt.items() if k!='native_status'}!=policy['installation_fields']:raise RuntimeError('Parent installation receipt changed')
    return dict(status='SHOP_VALUE_PREFLIGHT_PASS',files=len(seen),revision=m['revision'],native_status='PENDING',state_shop_touched=False)
def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/MANIFEST).read_text('utf-8'));c=dict(m.get('composition') or {})
    guards=list(m['guards'])
    for rel in (MANIFEST,RECEIPT):guards.append(dict(root='server',relative=rel,sha256=sha(server/rel)))
    c.update(server=str(server),client=str(Path(client or m['client']).resolve()),guards=guards)
    c.setdefault('ancestry',[]);c.setdefault('receipt_policies',[])
    return c
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True))
