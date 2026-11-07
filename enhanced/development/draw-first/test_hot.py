from pathlib import Path
import sys,os,json,copy,importlib.util,types
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def guard(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&0x243:raise RuntimeError('Protected asset write')
sys.addaudithook(guard)
import market_price_store
market_price_store.MarketPriceStore.flush=lambda self,events:0
import http_config as h
from hot_update_runtime import compile_handlers
routes=[dict(path='/shop/list',function='shop_list'),dict(path='/shop/remained/limited',function='remained'),dict(path='/shop/purchase',function='purchase'),dict(path='/shop/chain/round/purchase',function='round_purchase')]
handlers=compile_handlers((R/'hot_business.py').read_bytes(),str(R/'hot_business.py'),routes)
before=dict(vars(h));st=copy.deepcopy(h._state());host=types.SimpleNamespace(**vars(h));host._state=lambda:st
old=json.loads(h._json(h.shop_list(st))[1]);host.shop_list=lambda s:copy.deepcopy(old);before=dict(vars(h));new=json.loads(handlers['/shop/list'](host,'',b'')[1]);removed={r['shopid'] for r in old}-{r['shopid'] for r in new}
assert len(removed)>=15
assert [r for r in old if isinstance(r.get('chained'),list)]==[r for r in new if isinstance(r.get('chained'),list)]
assert all(any(r==x for x in old if x['shopid']==r['shopid']) for r in new), [(r['shopid'],list(r)) for r in new if not any(r==x for x in old if x['shopid']==r['shopid'])][:3]
saved=[];host._save=lambda s:saved.append(s)
host.ENDPOINTS=dict(h.ENDPOINTS)
def forbidden(q,b):raise AssertionError('Blocked purchase reached original mutation')
host.ENDPOINTS['/shop/purchase']=forbidden
for i in removed:
 for req in (dict(productid=i),dict(shopid=i)):
  result=json.loads(handlers['/shop/purchase'](host,'',json.dumps(req).encode())[1]);assert result['result'] is False
assert not saved
normal=next(r for r in new if r['product']['staticdata']['category']=='PLAYERPACK' and r.get('buy',True))
calls=[]
def original(q,b):
 calls.append((q,b));return h._json(dict(result=True,resources=[dict(uri='/shop/list',body=copy.deepcopy(old)),dict(uri='/bag',body=[{'sentinel':True}])]))
host.ENDPOINTS['/shop/purchase']=original
req=json.dumps(dict(productid=normal['product']['itemid'])).encode();out=json.loads(handlers['/shop/purchase'](host,'',req)[1])
assert calls==[('',req)] and out['result']
assert not removed&{r['shopid'] for r in out['resources'][0]['body']}
assert out['resources'][1]['body']==[{'sentinel':True}]
host.ENDPOINTS['/shop/chain/round/purchase']=original
prior=len(calls);out=json.loads(handlers['/shop/chain/round/purchase'](host,'',b'{}')[1]);assert len(calls)==prior+1 and not removed&{r['shopid'] for r in out['resources'][0]['body']}
assert all(vars(h)[k] is v for k,v in before.items())
report=dict(status='PASS',removed_shopids=sorted(removed),removed_count=len(removed),chains_unchanged=5,checks=['blocked direct purchase and shopid fallback before mutation','retained rows byte-equivalent','all five chains preserved','normal purchase delegated exactly once','purchase resource refresh filtered','other resources preserved','host globals unchanged','no real save'],real_assets_written=False,native_verified=False)
(R/'hot-test-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report))


