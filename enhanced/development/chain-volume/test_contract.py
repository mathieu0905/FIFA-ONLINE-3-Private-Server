from pathlib import Path
import sys,os,json,copy,ast,hashlib
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True;os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def guard(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&0x243:raise RuntimeError('Real asset write blocked')
sys.addaudithook(guard)
import market_price_store
market_price_store.MarketPriceStore.flush=lambda s,e:0
import http_config as h
from hot_update_runtime import compile_handlers
source=(R/'business.py').read_bytes();routes=[dict(path=p,function=f) for p,f in [('/shop/list','shop_list'),('/shop/purchase','purchase'),('/item/{item_id}/use','open_pack')]]
handlers=compile_handlers(source,'contract',routes,allow_templates=True)
st=copy.deepcopy(h._state());st['product_chain_rounds']={};h._state=lambda:st
rows=json.loads(handlers['/shop/list'](h,'',b'')[1]);roots=[r for r in rows if isinstance(r.get('chained'),list)];assert len(roots)==5
for row in roots:
 parts=[row]+row['chained'];counts=[sum(x['count'] for x in p['product']['staticdata']['items']) for p in parts];assert counts==[5,10,20,30,45],counts
 prices=[p['product']['staticdata']['bunches'][0]['price'] for p in parts];assert row['round_buy_total']==sum(prices)
 assert all(prices[k]>=prices[k-1]*1.6 for k in range(1,5))
 first=parts[0]['product']['staticdata'];assert first['itemicon']==first['items'][0]['staticdata']['itemicon']
 assert all(str(n)+'包' in p['product']['staticdata']['name'] for n,p in zip(counts,parts))
def get_open(data):return ast.dump(next(x for x in ast.parse(data).body if isinstance(x,ast.FunctionDef) and x.name=='open_pack'))
assert get_open(source)==get_open((S/'hot_updates/revisions/draw_first_full_20261107_02/business.py').read_bytes())
namespace=handlers['/shop/list'].__globals__;before={k:v for k,v in vars(h).items()};packages=copy.deepcopy(h.PACKAGES);cfg=copy.deepcopy(h.product_packs)
namespace['volume_engine'](h);assert all(vars(h)[k] is v for k,v in before.items()) and h.PACKAGES==packages and h.product_packs==cfg
calls=[];original=h.ENDPOINTS['/shop/purchase']
h.ENDPOINTS['/shop/purchase']=lambda q,b:(calls.append((q,b)) or h._json(dict(result=True,resources=[dict(uri='/shop/list',body=h.shop_list(st))])))
i=next(r['product']['itemid'] for r in rows if r['shopcategory']=='PLAYERPACK' and r.get('buy',True));body=json.dumps(dict(productid=i)).encode()
out=json.loads(handlers['/shop/purchase'](h,'',body)[1]);assert out['result'] and calls==[('',body)]
assert len([r for r in out['resources'][0]['body'] if isinstance(r.get('chained'),list)])==5
h.ENDPOINTS['/shop/purchase']=original
result=dict(status='PASS',source_sha256=hashlib.sha256(source).hexdigest(),checks=['native shop response shows all five tier names, prices and counts','each full round quote matches all displayed tier prices','first-tier icon matches its actual +8 or themed pack','host globals and catalogue dictionaries unchanged','existing dynamic pack opener unchanged','unrelated purchases delegated exactly once and refreshed'],real_assets_written=False,native_verified=False)
(R/'contract-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
