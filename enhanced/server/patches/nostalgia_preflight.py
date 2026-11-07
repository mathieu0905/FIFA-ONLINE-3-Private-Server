"""Exact composed-file gate for the independent season19 roster and native UI."""
from pathlib import Path
import hashlib,json,sqlite3
MANIFEST='patches/nostalgia-installed.json'
RECEIPT='patches/nostalgia-receipt.json'
SELF='patches/nostalgia_preflight.py'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def preflight(server=None,client=None):
 server=Path(server or Path(__file__).resolve().parent.parent).resolve();m=json.loads((server/MANIFEST).read_text('utf-8'));r=json.loads((server/RECEIPT).read_text('utf-8'))
 if r.get('status')!='INSTALLED_NOSTALGIA' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('revision')!=m.get('revision'):raise RuntimeError('Nostalgia installation receipt mismatch')
 if m.get('schema')!=1 or m.get('season')!=19 or m.get('card_count')!=88 or m.get('state_shop_replaced') is not False:raise RuntimeError('Unexpected nostalgia release scope')
 roots={'server':server,'client':Path(client or m['client']).resolve()};seen=set()
 for row in m['guards']:
  root=roots[row['root']];path=(root/row['relative']).resolve();key=(row['root'],row['relative'].replace('\\','/').casefold())
  if not path.is_relative_to(root) or path==root or key in seen:raise RuntimeError('Invalid or duplicate nostalgia guard')
  seen.add(key)
  if not path.is_file() or sha(path)!=row['sha256']:raise RuntimeError('Composed installed file differs: '+row['root']+'/'+row['relative'])
 required={('server',n.casefold()) for n in (SELF,'gamedata/fifadb.sqlite','gamedata/custom_rosters.json','responses/static_roster.json','patches/language_chi.big','patches/Label.big','patches/PlayerInfoNew.big','play-local.bat')}
 required|={('client',n.casefold()) for n in ('data/data_0.big','data/ui/libs/Module.big','data/ui/components/Label.big','data/ui/components/PlayerInfoNew.big')}
 if not required<=seen:raise RuntimeError('Missing nostalgia resource guards')
 for policy in m.get('composition',{}).get('receipt_policies',[]):
  root=roots[policy['root']];path=(root/policy['relative']).resolve()
  if not path.is_relative_to(root):raise RuntimeError('Receipt path escape')
  actual=json.loads(path.read_text('utf-8-sig'))
  if {k:v for k,v in actual.items() if k!='native_status'}!=policy['installation_fields']:raise RuntimeError('Parent installation receipt changed')
 registry=json.loads((server/'gamedata/custom_rosters.json').read_text('utf-8'));season=next(x for x in registry['seasons'] if x['id']==19)
 if season['label']!='怀旧神兽' or len(set(season['cards']))!=88:raise RuntimeError('Season registry mismatch')
 with sqlite3.connect((server/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  actual={r[0] for r in db.execute('select spid from players where spid/1000000=19')}
  if actual!=set(season['cards']):raise RuntimeError('Season19 database/registry mismatch')
 return dict(status='NOSTALGIA_PREFLIGHT_PASS',files=len(seen),revision=m['revision'],season=19,cards=88,native_status='PENDING',state_shop_touched=False)
def compose_manifest(server=None,client=None):
 server=Path(server or Path(__file__).resolve().parent.parent).resolve();m=json.loads((server/MANIFEST).read_text('utf-8'));c=dict(m.get('composition') or {});guards=list(m['guards'])
 for name in (MANIFEST,RECEIPT):guards.append(dict(root='server',relative=name,sha256=sha(server/name)))
 c.update(server=str(server),client=str(Path(client or m['client']).resolve()),guards=guards);c.setdefault('ancestry',[]);c.setdefault('receipt_policies',[]);return c
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True,indent=2))
