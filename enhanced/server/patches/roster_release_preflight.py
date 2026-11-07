"""Validate an explicit additive roster release without rewriting shop history."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def validate(server,client,parent_sha):
 server=Path(server).resolve();client=Path(client).resolve();roots={'server':server,'client':client}
 receipt=read(server/'patches/roster-release-installed.json');manifest=server/'patches/roster-release-manifest.json'
 if receipt.get('status')!='INSTALLED' or receipt.get('manifest_sha256')!=sha(manifest):raise RuntimeError('Roster receipt mismatch')
 m=read(manifest)
 if m.get('parent_shop_manifest_sha256')!=parent_sha:raise RuntimeError('Roster/shop ancestry mismatch')
 old=read(server/'patches/shop-release-manifest.json')
 guards={(e['root'],e['relative'].replace('\\','/').casefold()):e['sha256'] for e in old['files']+old['unchanged']}
 replacements={};seen=set()
 for e in m['files']:
  root=roots[e['root']];rel=Path(e['relative'])
  if rel.is_absolute() or '..' in rel.parts:raise RuntimeError('Roster path escape')
  target=(root/rel).resolve();pair=(e['root'],str(rel).replace('\\','/').casefold())
  if target==root or not target.is_relative_to(root) or pair in seen:raise RuntimeError('Duplicate/escaped roster target')
  seen.add(pair)
  if not target.is_file() or sha(target)!=e['sha256']:raise RuntimeError('Roster installed file differs: '+str(rel))
  if pair in guards:
   if e['parent_sha256']!=guards[pair]:raise RuntimeError('Roster parent guard differs: '+str(rel))
   replacements[pair]=e['sha256']
 if m.get('added_spids')!=[13252371] or m.get('state_shop_replaced') is not False:raise RuntimeError('Unexpected roster release scope')
 return replacements

def preflight(server=None,client=None):
 import shop_release_preflight as shop
 server=Path(server or Path(__file__).resolve().parent.parent).resolve()
 oldpath=server/'patches/shop-release-manifest.json';old=read(oldpath)
 client=Path(client or old['client_root']).resolve();receipt=read(server/'patches/shop-release-installed.json')
 if receipt.get('status')!='INSTALLED' or receipt.get('manifest_sha256')!=sha(oldpath) or receipt.get('release_id')!=old['release_id']:raise RuntimeError('Original shop receipt mismatch')
 proof=receipt.get('native_proof',{})
 if proof.get('status')!='PASS' or proof.get('release_manifest_sha256')!=sha(oldpath):raise RuntimeError('Original shop native proof mismatch')
 roster_receipt=read(server/'patches/roster-release-installed.json')
 if sha(server/'patches/roster_release_preflight.py')!=roster_receipt.get('preflight_sha256'):raise RuntimeError('Roster preflight hash mismatch')
 replacements=validate(server,client,sha(oldpath))
 composed=dict(old)
 for group in ['files','unchanged']:
  composed[group]=[dict(e,sha256=replacements.get((e['root'],e['relative'].replace('\\','/').casefold()),e['sha256'])) for e in old[group]]
 result=shop.verify_files(composed,server,client)
 return dict(result,status='READ_ONLY_COMPOSED_ROSTER_SHOP_PREFLIGHT_PASS',shop_history_unchanged=True,state_shop_touched=False)

if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True))
