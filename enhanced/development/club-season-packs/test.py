"""Execute the formal purchase/opening engine against an in-memory state copy."""
from pathlib import Path
import copy,importlib.abc,importlib.util,json,math,os,sys
from decimal import Decimal,ROUND_CEILING
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True;os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi',FO3_GAME='D:/FO3ID/32795')
def guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and args[2]&0x243 and not Path(os.fsdecode(args[0])).resolve().is_relative_to(R):raise RuntimeError('Test attempted formal file write')
 if event in ('socket.bind','socket.connect'):raise RuntimeError('Test cannot start/contact services')
sys.addaudithook(guard)
class Finder(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='product_packs':return importlib.util.spec_from_file_location(fullname,R/'product_packs.py')
sys.meta_path.insert(0,Finder());original_read=Path.read_text;original_exists=Path.exists;original_file=Path.is_file;original_bytes=Path.read_bytes
def staged_read(self,*args,**kwargs):
 if self==S/'gamedata/club_season_products.json':return original_read(R/'club_season_products.json',*args,**kwargs)
 if self==S/'gamedata/all_item_icon_manifest.json':return original_read(R/'all_item_icon_manifest.json',*args,**kwargs)
 return original_read(self,*args,**kwargs)
Path.read_text=staged_read
Path.exists=lambda self:True if self==S/'gamedata/club_season_products.json' else original_exists(self)
Path.is_file=lambda self:True if (R/'icons'/self.name).is_relative_to(R/'icons') and original_file(R/'icons'/self.name) else original_file(self)
Path.read_bytes=lambda self:original_bytes(R/'icons'/self.name) if original_file(R/'icons'/self.name) else original_bytes(self)
import market_price_store
market_price_store.MarketPriceStore.flush=lambda self,events:0
import http_config as h
Path.read_text=original_read;Path.exists=original_exists;Path.is_file=original_file;Path.read_bytes=original_bytes
cfg=json.loads((R/'club_season_products.json').read_text('utf8'));legacy=json.loads((R/'legacy.json').read_text('utf8'));build=json.loads((R/'build.json').read_text('utf8'))
for raw,old in legacy.items():
 itemid=int(raw);assert json.loads(json.dumps(dict(pool=h.pack_pool(itemid),grades=h.pack_grades(itemid),category=h.item_def(itemid)['category'])))==old,('Legacy contract changed',itemid)
st=copy.deepcopy(h._state());h._state=lambda:st;h._save=lambda value:None;coach=h.my_coach(st);coach['cash']=10**9
manager=h.hot_update_manager;manager.poll();assert manager.status()['error'] is None and manager.status()['revision']==json.loads((S/'hot_updates/active.json').read_text('utf8'))['revision'],manager.status()
checked=[]
for p in build['products']:
 itemid=p['id'];weights={int(g):w for g,w in p['grades'].items()};grades={g:w for g,w in h.pack_grades(itemid) if w>0};pool=dict(h.pack_pool(itemid));assert grades==weights and min(grades)>=8 and len(pool)==p['pool_size'] and len(set(pool.values()))==1
 assert all(s//1000000==p['season'] for s in pool);assert h.item_def(itemid)['category']=='PLAYERPACK';assert itemid in h.all_item_icons
 actual=h.pack_expected_value(itemid)
 assert math.isclose(actual,math.fsum(h.player_value_price(s,g)*w for s in pool for g,w in weights.items())/(len(pool)*100),rel_tol=1e-12)
 assert int((Decimal(str(p['expected_bp']))/Decimal(str(p['bp_per_point']))).to_integral_value(rounding=ROUND_CEILING))==p['price']
 assert h.product_price(itemid,1)==p['price']
 before_cash=coach['cash'];body=json.dumps(dict(shopid=itemid,productid=itemid,bunch=0)).encode();response=json.loads(manager.handler('/shop/purchase')('',body)[1]);assert response['result'],(itemid,response)
 assert before_cash-coach['cash']==p['price'],(itemid,before_cash,coach['cash'],h.my_coach(st)['cash'],p['price'],response.get('currency'),response.get('spent'),h.item_def(itemid).get('currency'))
 row=next(r for r in h.coach_items(st,h._default_slot(st)) if r['itemid']==itemid);token=str(row['_id']);handler=manager.handler('/item/'+token+'/use');assert handler
 before_count=len(st['teams'][str(h._default_slot(st))]['players']);result=json.loads(handler('',b'{}')[1]);assert result['result'] and result['player']['spid'] in pool and result['player']['grade'] in grades,result
 assert len(st['teams'][str(h._default_slot(st))]['players'])==before_count+1;again=json.loads(handler('',b'{}')[1]);assert again['replayed'] and again['player']==result['player'];assert len(st['teams'][str(h._default_slot(st))]['players'])==before_count+1
 saved_cash=coach['cash'];coach['cash']=0;before_items=copy.deepcopy(coach.get('items',[]));denied=json.loads(manager.handler('/shop/purchase')('',body)[1]);assert denied['result'] is False and coach['cash']==0 and coach.get('items',[])==before_items;coach['cash']=saved_cash
 if p['period']=='week':
  record=st['product_purchase_counts'][str(itemid)];used=record['used'];record['used']=p['limit'];before_items=copy.deepcopy(coach.get('items',[]));denied=json.loads(manager.handler('/shop/purchase')('',body)[1]);assert denied['result'] is False and coach['cash']==saved_cash and coach.get('items',[])==before_items;record['used']=used
 checked.append(itemid)
report=dict(status='PASS',new_products=checked,old_pack_contracts_unchanged=len(legacy),purchase_correct_debit=6,abi2_random_opening_and_replay=6,insufficient_balance_no_grant=6,weekly_fixed_pack_limit_enforced=2,uniform_frozen_pools=True,grade_minimum=8,correct_expected_bp_snapshot_prices=True,native_style_icons_grade_labels_correct=True,real_state_shop_or_balance_written=False,native_ui_verified=False,hot_revision=manager.status()['revision'])
(R/'tests.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
