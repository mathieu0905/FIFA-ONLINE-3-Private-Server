"""Exact-file guard for the additive official club-career update."""
from pathlib import Path
import hashlib,json
MANIFEST='patches/player-import-installed.json'
RECEIPT='patches/player-import-receipt.json'
SELF='patches/player_import_preflight.py'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def preflight(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/MANIFEST).read_text('utf8'))
    r=json.loads((server/RECEIPT).read_text('utf8'))
    if m.get('schema')!=1 or m.get('state_shop_replaced') is not False:raise RuntimeError('Invalid player-import scope')
    if r.get('status')!='INSTALLED_PLAYER_IMPORT' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('revision')!=m['revision']:raise RuntimeError('Player-Import receipt mismatch')
    roots=dict(server=server,client=Path(client or m['client']).resolve());seen=set()
    for g in m['guards']:
        if g.get('root') not in roots:raise RuntimeError('Unknown guard root')
        root=roots[g['root']];p=(root/g['relative']).resolve();key=(g['root'],g['relative'].replace('\\','/').casefold())
        if not p.is_relative_to(root) or p==root or key in seen:raise RuntimeError('Invalid player-import guard')
        seen.add(key)
        if not p.is_file() or sha(p)!=g['sha256']:raise RuntimeError('Installed file differs: '+str(key))
    required={('server','gamedata/fifadb.sqlite'),('client','data/data_0.big'),('server','play-local.bat'),('server',SELF),('client','data/ui/libs/module.big'),('client','data/data_4.big'),('client','data/data_6.big'),('server','tools/player_import/check.py'),('server','gamedata/player-imports.json'),('server','gamedata/player-import-validation.json')}
    if not required<=seen:raise RuntimeError('Incomplete player-import guards')
    for policy in m.get('composition',{}).get('receipt_policies',[]):
        if policy.get('root') not in roots:raise RuntimeError('Unknown receipt root')
        root=roots[policy['root']];p=(root/policy['relative']).resolve()
        if not p.is_relative_to(root) or p==root:raise RuntimeError('Receipt path escape')
        receipt=json.loads(p.read_text('utf-8-sig'))
        if {k:v for k,v in receipt.items() if k!='native_status'}!=policy['installation_fields']:raise RuntimeError('Parent installation receipt changed')
    return dict(status='PLAYER_IMPORT_PREFLIGHT_PASS',files=len(seen),revision=m['revision'],native_status='PENDING',state_shop_touched=False)

def compose_manifest(server=None,client=None):
    server=Path(server or Path(__file__).resolve().parent.parent).resolve()
    m=json.loads((server/MANIFEST).read_text('utf8'));c=dict(m.get('composition') or {})
    guards=list(m['guards'])
    for rel in (MANIFEST,RECEIPT):guards.append(dict(root='server',relative=rel,sha256=sha(server/rel)))
    c.update(server=str(server),client=str(Path(client or m['client']).resolve()),guards=guards)
    c.setdefault('ancestry',[]);c.setdefault('receipt_policies',[])
    return c

if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True))
