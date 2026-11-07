from pathlib import Path
import sys,types,copy,json,threading
from unittest.mock import patch
P=Path(__file__).resolve().parent;sys.path[:0]=[str(P),'D:/FO3ID/server']
from market_simulation import Market
m=Market.__new__(Market);store=[dict(coaches=[dict(money=dict(ep=10000))],teams={'0':dict(players=[])},market_simulation=dict(seed='fixture',supply_started_at=0,rare_books={},legacy_supply=[]))]
h=types.SimpleNamespace(MAX_GRADE=20,MAX_PLAYERS=100,STATE_LOCK=threading.RLock(),_json=lambda v:v,_state=lambda:copy.deepcopy(store[0]),_save=lambda st:store.__setitem__(0,copy.deepcopy(st)),coach_me=lambda st,slot:st['coaches'][0],coach_me_resources=lambda *a:[])
def add(team,spid,grade):
 player=dict(spid=spid,grade=grade,id='fixture-only');team['players'].append(player);return player
h.add_player=add;h.add_ep=lambda st,amount:st['coaches'][0]['money'].__setitem__('ep',st['coaches'][0]['money']['ep']+amount);m.h=h
m.has_active=lambda st:True;m.valid_card=lambda *a:True;m.prepare=lambda *a:None;m.settle=lambda *a:None;m.active=lambda st:(st['coaches'][0],st['teams']['0'],0);m.quality_pools=lambda:{'elite':(93001075,)};m.supply_plan=lambda:[dict(key='elite_15',quality='elite',grades=(15,),period=300,slots=5,chance=1,pool_size=1,expected_per_day=1440)];m.quote=lambda *a:100;m.unit=lambda seed:.01;m.book=lambda *a:dict(rows=[]);m.exchange=types.SimpleNamespace(listings=lambda *a:[],human_purchase=lambda *a:None)
rows=m.rare_stock(store[0],241);next(r for r in rows if r['_market_release']==240)['price']=777;m.rare_stock(store[0],301)
with patch('market_simulation.now',return_value=601):result=m.purchase(93001075,15,777,{},b'')
assert result['result'] is True and len(store[0]['teams']['0']['players'])==1 and store[0]['coaches'][0]['money']['ep']==9223
with patch('market_simulation.now',return_value=601):second=m.purchase(93001075,15,777,{},b'')
assert second['result'] is False and len(store[0]['teams']['0']['players'])==1 and store[0]['coaches'][0]['money']['ep']==9223
(P/'purchase-regression.json').write_text(json.dumps(dict(status='PASS',checks=2,carried_offer_purchased_after_multiple_rollovers=True,consumed_offer_repurchase_rejected=True,real_state_written=False),indent=2),'utf8');print('PASS 2: actual purchase handler with temporary state')
