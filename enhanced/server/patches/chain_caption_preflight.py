"""Composed exact-file guard; live market DB has an immutable seed, mutable prices."""
from pathlib import Path
import hashlib,importlib.util,json
MANIFEST='patches/chain-caption-installed.json'
RECEIPT='patches/chain-caption-receipt.json'
SELF='patches/chain_caption_preflight.py'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def preflight(server=None,client=None):
 server=Path(server or Path(__file__).resolve().parent.parent).resolve();m=json.loads((server/MANIFEST).read_text('utf8'));r=json.loads((server/RECEIPT).read_text('utf8'))
 if m.get('schema')!=1 or m.get('state_shop_replaced') is not False:raise RuntimeError('Invalid market price-store scope')
 if r.get('status')!='INSTALLED_CHAIN_CAPTION' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('revision')!=m['revision']:raise RuntimeError('Market price-store receipt mismatch')
 roots=dict(server=server,client=Path(client or m['client']).resolve());seen=set()
 for g in m['guards']:
  root=roots[g['root']];p=(root/g['relative']).resolve();key=(g['root'],g['relative'].replace('\\','/').casefold())
  if not p.is_relative_to(root) or p==root or key in seen:raise RuntimeError('Invalid market guard')
  seen.add(key)
  if not p.is_file() or sha(p)!=g['sha256']:raise RuntimeError('Installed file differs: '+str(key))
 required={('server',SELF),('server','play-local.bat'),('server','market_price_store.py'),('server','npc_exchange.py'),('server','market_simulation.py'),('server','gamedata/npc-market-seed.json.gz')}
 if not required<=seen:raise RuntimeError('Incomplete market price-store guard')
 if ('server','gamedata/npc-market-prices.sqlite') in seen:raise RuntimeError('Mutable current prices must not be frozen by a file hash')
 for policy in m.get('composition',{}).get('receipt_policies',[]):
  root=roots[policy['root']];p=(root/policy['relative']).resolve()
  if not p.is_relative_to(root) or p==root:raise RuntimeError('Receipt path escape')
  receipt=json.loads(p.read_text('utf-8-sig'))
  if {k:v for k,v in receipt.items() if k!='native_status'}!=policy['installation_fields']:raise RuntimeError('Parent receipt installation fields changed')
 spec=importlib.util.spec_from_file_location('_price_seed_check',server/'market_price_store.py');store=importlib.util.module_from_spec(spec);spec.loader.exec_module(store)
 seed=store.verify_seed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/npc-market-seed.json.gz')
 return dict(status='CHAIN_CAPTION_PREFLIGHT_PASS',files=len(seen),revision=m['revision'],seed=seed,runtime_model_loaded=False,native_status='PENDING',state_shop_touched=False)
def compose_manifest(server=None,client=None):
 server=Path(server or Path(__file__).resolve().parent.parent).resolve();m=json.loads((server/MANIFEST).read_text('utf8'));c=dict(m.get('composition') or {});guards=list(m['guards'])
 for rel in (MANIFEST,RECEIPT):guards.append(dict(root='server',relative=rel,sha256=sha(server/rel)))
 c.update(server=str(server),client=str(Path(client or m['client']).resolve()),guards=guards);c.setdefault('ancestry',[]);c.setdefault('receipt_policies',[])
 return c
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True))
