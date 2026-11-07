from pathlib import Path
import sys,os,json,copy,collections,ast
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True;os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def guard(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&0x243:raise RuntimeError('Real state write blocked')
sys.addaudithook(guard)
import market_price_store
market_price_store.MarketPriceStore.flush=lambda self,e:0
import http_config as h
from hot_update_runtime import compile_handlers
source=(R/'business.py').read_text('utf8');routes=[dict(path=p,function=f) for p,f in [('/shop/list','shop_list'),('/shop/remained/limited','remained'),('/shop/purchase','purchase'),('/shop/chain/round/quote','round_quote'),('/shop/chain/round/purchase','round_purchase'),('/item/{item_id}/use','open_pack')]]
handlers=compile_handlers(source,'chain-volume',routes,allow_templates=True);ns=handlers['/shop/list'].__globals__
base=copy.deepcopy(h._state());base.pop('market_simulation',None);box={'state':base};saves=[];h._state=lambda:box['state'];h._save=lambda st:saves.append(True);h.coach_me_resources=lambda st,slot:[]
plan=ns['volume_data']();checked=bulk=single=0
# The full native listing and non-chain delegation are exercised separately in
# test_contract.py. Transaction tests retain real native chain rows only.
h.shop_list=lambda st:[h.chained_entry(st,int(root)) for root in plan]
def fresh(root,rn=0,k=0):
 st=copy.deepcopy(base);box['state']=st;c=h.my_coach(st);c['cash']=10**9
 st.setdefault('product_chain_rounds',{})[str(root)]=dict(rounds=rn,stage=k,owner=str(c['_id']),owner_appat=c.get('appat'))
 return st,c
def call(path,req=None,query=''):
 return json.loads(handlers[path](h,query,b'' if req is None else json.dumps(req).encode())[1])
for raw,t in plan.items():
 root=int(raw)
 for rn,steps in enumerate(t['round_steps']):
  prior=0
  for k,i in enumerate(steps):
   d=t['packages'][str(i)];assert sum(n for child,n in d['contents'])==[5,10,20,30,45][k]
   assert d['price']>=prior*1.6;prior=d['price']
   assert all(h.item_def(child)['category']=='PLAYERPACK' for child,n in d['contents']);checked+=1
  st,c=fresh(root,rn);old_other={k:copy.deepcopy(v) for k,v in st['product_chain_rounds'].items() if k!=raw};old_cards=copy.deepcopy(st['teams'])
  q=call('/shop/chain/round/quote',query='root='+raw)['quote'];assert sum(n for i,n in q['rewards'])==110
  amount=q['total'];inv=collections.Counter({x['itemid']:x['remains'] for x in c.get('items',[])})
  out=call('/shop/chain/round/purchase',dict(quote=q));assert out['result'],out
  assert c['cash']==10**9-amount and st['product_chain_rounds'][raw]['rounds']==rn+1
  now=collections.Counter({x['itemid']:x['remains'] for x in c.get('items',[])})
  assert now-inv==collections.Counter(dict(q['rewards'])) and st['teams']==old_cards
  assert old_other=={k:v for k,v in st['product_chain_rounds'].items() if k!=raw}
  count=len(saves);again=call('/shop/chain/round/purchase',dict(quote=q));assert again['replayed'] and len(saves)==count and c['cash']==10**9-amount
  bad=copy.deepcopy(q);bad['total']+=1;assert not call('/shop/chain/round/purchase',dict(quote=bad))['result'];bulk+=1
 # Native per-stage path and out-of-order rejection for all five tiers.
 for k,i in enumerate(t['steps']):
  st,c=fresh(root,0,k);count=len(saves)
  bad=t['steps'][(k+1)%5];assert not call('/shop/purchase',dict(productid=bad,shopid=root,bunch=0))['result'] and len(saves)==count
  before=sum(x['remains'] for x in c.get('items',[]));out=call('/shop/purchase',dict(productid=i,shopid=root,bunch=0));assert out['result'],out
  assert sum(x['remains'] for x in c.get('items',[]))-before==[5,10,20,30,45][k]
  assert c['cash']==10**9-t['prices'][str(i)]
  count=len(saves);assert not call('/shop/purchase',dict(productid=i,shopid=root,bunch=0))['result'] and len(saves)==count;single+=1
 # In-progress rounds only quote the remaining new rewards, never regrant paid tiers.
 st,c=fresh(root,3,2);q=call('/shop/chain/round/quote',query='root='+raw)['quote'];assert sum(n for i,n in q['rewards'])==95
 st,c=fresh(root,10,0);assert not call('/shop/chain/round/quote',query='root='+raw)['result']
 # A fully populated but insufficient wallet must not mutate inventory or progress.
 st,c=fresh(root);q=call('/shop/chain/round/quote',query='root='+raw)['quote'];c['cash']=0;before=copy.deepcopy(st);count=len(saves)
 assert not call('/shop/chain/round/purchase',dict(quote=q))['result'] and st==before and len(saves)==count
# Old committed bulk receipts can still replay without a second grant.
st,c=fresh(71350101);oldq=json.loads(h.ENDPOINTS['/shop/chain/round/quote']('root=71350101',b'')[1])['quote'];qkey=__import__('hashlib').sha256((oldq['nonce']+oldq['signature']).encode()).hexdigest()
st.setdefault('product_chain_bulk_receipts',{})[qkey]=dict(root=71350101,spent=oldq['total'],round_completed=1)
count=len(saves);assert call('/shop/chain/round/purchase',dict(quote=oldq))['replayed'] and len(saves)==count
# A stale uncommitted old quote is rejected because its rewards/prices differ.
st['product_chain_bulk_receipts'].pop(qkey);assert not call('/shop/chain/round/purchase',dict(quote=oldq))['result']
report=dict(status='PASS',stage_definitions=checked,full_round_transactions=bulk,single_stage_transactions=single,round_pack_count=110,counts=[5,10,20,30,45],minimum_price_ratio=1.6,checks=['bulk replay and quote tampering','single-stage order and duplicate rejection','partial round only grants unpaid stages','completed chains closed','insufficient funds no mutation','other roots and cards preserved','old committed receipt replay','old uncommitted quote refresh required'],real_state_written=False,native_verified=False)
(R/'tests.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
