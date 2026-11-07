"""Execute installed production pack adapters without listeners or asset writes."""
from pathlib import Path
import os,sys,json,math
from prepare import R,S,C,write
sys.dont_write_bytecode=True
def audit(event,args):
 if event=='open':
  path,mode,flags=args
  if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
   if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Regression cannot write official files')
 if event in ('socket.bind','socket.connect'):raise PermissionError('Regression cannot open listeners or contact services')
sys.addaudithook(audit)
os.environ.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(S));sys.argv=['http_config.py']
import http_config as h
new=json.loads((S/'gamedata/manutd_legends_products.json').read_text('utf8'));wanted=set(next(iter(new['strength_packs'].values()))['tiers'][0]['pool'])
for i,d in new['strength_packs'].items():
 pool=dict(h.pack_pool(int(i)));assert set(pool)==wanted and all(abs(w-1/41)<1e-12 for w in pool.values())
 assert h.pack_grades(int(i))==[(1,100)]
 assert h.product_price(int(i),1)==new['value_prices'][i]['price']
 assert all(88<=h.card_ovr(s)+h.GRADE_BOOST[1]<=92 for s in pool)
assert all(h.on_market(s) for s in wanted)
checked=0
for filename in ('product_packs.json','product_chain_elite.json','shop_value_products.json','chain_rebalance_products.json'):
 cfg=json.loads((S/'gamedata'/filename).read_text('utf8'))
 for i,d in {**cfg.get('risk_packs',{}),**cfg.get('strength_packs',{})}.items():
  assert h.product_packs['strength_packs'].get(i,h.product_packs['risk_packs'].get(i))==d
  expected={};total=sum(t['weight'] for t in d['tiers'])
  for t in d['tiers']:
   for s in t['pool']:expected[s]=expected.get(s,0)+t['weight']/total/len(t['pool'])
  assert dict(h.pack_pool(int(i)))==expected
  assert h.pack_grades(int(i))==list(enumerate(d['grades'],1))
  checked+=1
write(R/'pack-verification.json',dict(status='PASS',new_pools=2,new_cards_each=41,probability_each='1/41',fixed_grade=1,old_product_packs_exact=checked,all_cards_tradeable=True,all_ratings_88_92=True,production_written=False,listener_started=False,native_verified=False))
print('Production adapters PASS; old frozen product packs:',checked)
