"""Execute the actual frozen pool adapters without importing the live server."""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import ast,hashlib,json,sqlite3
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');B=R/'build-v2/database'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8'))
def signature(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def functions(path,scope,names,env):
 tree=ast.parse(path.read_text('utf-8'));parent=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==scope)
 found=[n for n in parent.body if isinstance(n,ast.FunctionDef) and n.name in names]
 assert {n.name for n in found}==set(names)
 for f in found:f.decorator_list=[]
 exec(compile(ast.Module(body=found,type_ignores=[]),str(path),'exec'),env)
 return [env[n] for n in names]
def forbidden(*args):raise AssertionError('A released pack reached a live database-dependent fallback')
cad=read(S/'gamedata/pack_cadence.json');cat=read(S/'gamedata/pack_catalogue.json');prod=read(S/'gamedata/product_packs.json')
for config in (cad,cat,prod):assert config['hash']==signature({k:v for k,v in config.items() if k!='hash'})
c=SimpleNamespace(legacy={int(k):v for k,v in cad['legacy'].items()},items={int(k):v for k,v in cad['items'].items()},previous_pool=forbidden,previous_grades=forbidden)
pool,grades=functions(S/'pack_cadence.py','install',('pack_pool','pack_grades'),dict(cadence=c,Counter=Counter))
ids=set(c.legacy)|set(c.items);before={i:(pool(i),grades(i)) for i in ids}
entries={int(k):v for k,v in cat['items'].items()}
pool,grades=functions(S/'pack_catalogue.py','install',('pool','grades'),dict(entries=entries,previous_pool=pool,previous_grades=grades))
ids|=set(entries);before={i:(pool(i),grades(i)) for i in ids}
risks={int(k):v for k,v in {**prod['risk_packs'],**prod.get('strength_packs',{})}.items()}
pool,grades=functions(S/'product_packs.py','install',('pool','grades'),dict(risks=risks,previous_pool=pool,previous_grades=grades))
ids|=set(risks);before={i:(pool(i),grades(i)) for i in ids}
spec=read(B/'spec.json');newids={19000000+r['base_playerid'] for r in spec['cards']}
db=sqlite3.connect(B/'fifadb.sqlite');db.execute('attach database ? as original',(str(S/'gamedata/fifadb.sqlite'),))
for i,(p,g) in before.items():
 assert p and sum(w for _,w in p)>0 and sum(w for _,w in g)>0
 assert not {s for s,_ in p}&newids,('New cards leaked into sold pool',i)
 for s,w in p:
  assert db.execute('select 1 from original.players where spid=?',(s,)).fetchone(),s
assert not db.execute('select * from original.players except select * from main.players limit 1').fetchone()
assert before=={i:(pool(i),grades(i)) for i in ids}
market={r[0] for r in db.execute('select p.spid from players p join permid m on m.spid=p.spid where p.spid>=1000000 and m.transferable=1 and p.playerid in (select playerid from namesind)')}
assert newids<=market
report=dict(status='FROZEN_CONTRACT_PASS',legacy_packs=len(cad['legacy']),cadence_packs=len(cad['items']),catalogue_packs=len(entries),product_packs=len(risks),unique_issued_items=len(ids),all_weights_and_grades_exact=True,new_cards_in_old_pools=0,new_cards_market_eligible=len(newids),source_hashes={n:sha(S/'gamedata'/n) for n in ('pack_cadence.json','pack_catalogue.json','product_packs.json')},adapter_sources={n:sha(S/n) for n in ('pack_cadence.py','pack_catalogue.py','product_packs.py')},native_verified=False,production_written=False)
(R/'contracts-result.json').write_text(json.dumps(report,indent=2),'utf-8');print(json.dumps(report,indent=2))
