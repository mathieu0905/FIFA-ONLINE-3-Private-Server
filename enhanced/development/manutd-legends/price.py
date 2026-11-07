"""Use production valuation functions with a read-only prepared database."""
import sys,os,sqlite3,json,math
from pathlib import Path
from prepare import R,S,C,write
sys.dont_write_bytecode=True
def audit(event,args):
 if event=='open':
  path,mode,flags=args
  if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
   if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Pricing cannot write official files')
 if event in ('socket.bind','socket.connect'):raise PermissionError('Pricing cannot start/contact a server')
sys.addaudithook(audit)
out=Path(json.loads((R/'latest-build.json').read_text('utf8'))['path'])
os.environ.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(S));sys.argv=['http_config.py']
import http_config as h
h._db=lambda:sqlite3.connect((out/'fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
h._OVR.clear();h._STATS.clear()
cfg=json.loads((out/'products-unpriced.json').read_text('utf8'));coefficient=h.product_packs['valuation']['points_per_ep']
for i,d in cfg['strength_packs'].items():
 assert int(i) not in h.PACKS and int(i) not in h.ITEMS and int(i) not in h.PACKAGES
 pool=d['tiers'][0]['pool'];ep=[h.player_value_price(s,1) for s in pool]
 expected=max(ep) if d['mode']=='choice' else sum(ep)/len(ep)
 ordinary=max(3,math.ceil(expected*coefficient));chain=min(ordinary-1,max(2,math.ceil(expected*coefficient*.65)));once=min(chain-1,max(1,math.ceil(expected*coefficient*.45)))
 d['price']=ordinary;cfg['value_prices'][i]=dict(expected_ep=expected,standard_points=expected*coefficient,quotes=dict(ordinary=ordinary,chain=chain,once=once),kind='ordinary',price=ordinary)
 assert all(88<=h.card_ovr(s)+h.GRADE_BOOST[1]<=92 for s in pool)
cfg['hash']=h.product_packs_module_signature(cfg) if hasattr(h,'product_packs_module_signature') else __import__('product_packs').signature(cfg)
write(out/'manutd_legends_products.json',cfg)
write(R/'pricing.json',dict(coefficient=coefficient,products=cfg['value_prices'],basis='production player_value_price using prepared DB; ordinary rate, random expected value / choice maximum'))
print(json.dumps(cfg['value_prices']))
