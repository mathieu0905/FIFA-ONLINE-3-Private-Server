"""Whole catalogue/grade safety and exact quote-transition regressions."""
from pathlib import Path
from contextlib import closing
import copy,gzip,hashlib,importlib.util,json,math,sqlite3,sys
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path[:0]=[str(P),str(S)]
from fair_value_model import economic_curve
from system_quotes import reissue
sys.path.append('D:/fifaol3/value-redesign-v12')
from effective_boosts import grade_boosts
def main():
 cfg=json.loads((P/'model.json').read_text('utf8'));old=json.loads((S/'gamedata/fair-value-v13-model.json').read_text('utf8'))
 with gzip.open(P/'catalogue.json.gz','rt',encoding='utf8') as f:cat=json.load(f)
 with gzip.open(S/'gamedata/fair-value-v13-catalogue.json.gz','rt',encoding='utf8') as f:previous=json.load(f)
 assert cat['rows']==previous['rows'];assert cfg['curve']==old['curve'];assert cfg['currency_scale']==old['currency_scale'];assert cfg['identity_factors']==old['identity_factors']
 mult=cfg['enhancement_price_curve']['multipliers'];checks=0;peak=0
 for r in cat['rows']:
  for factor in [.85,1.,1.15]:
   base=round(r['economic_value']*factor)+r['strict_floor_ep'];last=0
   for g in range(1,21):
    price=round(base*mult[g]);assert price>last;assert price<(2**53-1)//3;assert round((base+1)*mult[g])>price;last=price;peak=max(peak,price);checks+=1
 # Use actual real-card economics in a detached, synthetic offer world.
 rows={r['spid']:r for r in cat['rows']};sample=rows[12037576];sid=sample['spid'];pid=sample['playerid'];values={sid:(pid,sample['economic_value'],sample['strict_floor_ep'],sample['effective_score'],sample['profile_sha256'])};factors={pid:1.};base=sample['fair_price_ep'];boost=grade_boosts();delta=boost[15]-5;identity=sample['economic_value']/economic_curve(sample['effective_score'],old);oldprice=round(economic_curve(sample['effective_score']+delta,old)*identity)+sample['strict_floor_ep']+33*delta
 state=dict(coaches=[dict(ep=999,bag=[1])],teams={'1':dict(players=[dict(id='owned',exp=4,grade=15)])},offers=[dict(spid=sid,grade=15,price=88,status='selling')],market_simulation=dict(books={'a':dict(epoch=1,expires_at=999999,rows=[dict(spid=sid,grade=15,price=oldprice,count=2,_market_expires=9000),dict(spid=sid,grade=15,price=oldprice,count=0,_market_expires=9000),dict(spid=sid,grade=15,price=None,count=3,_market_expires=9000),dict(spid=sid,grade=15,price=oldprice,count=1,_market_expires=10)])},rare_books={},legacy_supply=[dict(spid=sid,grade=15,price=oldprice//1000,count=1,_market_expires=9000)],npc_exchange=dict(agents=[dict(wallet=123)],assets={'n':dict(spid=sid,grade=15,cost=8,quantity=1,listing=dict(spid=sid,grade=15,price=oldprice,count=1,_market_expires=9000))}),sales=[dict(price=oldprice)]))
 after,receipt,details=reissue(state,old,cfg,values,factors,boost,1000,economic_curve);assert receipt['changed']==3;assert all(after[k]==v for k,v in state.items() if k!='market_simulation');assert after['market_simulation']['sales']==state['market_simulation']['sales'];assert after['market_simulation']['npc_exchange']['agents']==state['market_simulation']['npc_exchange']['agents'];assert after['market_simulation']['npc_exchange']['assets']['n']['cost']==8
 original=state['market_simulation']['books']['a']['rows'];updated=after['market_simulation']['books']['a']['rows'];assert updated[0]['count']==2 and updated[0]['_market_expires']==9000;assert updated[0]['price']==round(base*mult[15]);assert updated[1:]==original[1:];assert after['market_simulation']['legacy_supply'][0]['price']>=round(base*mult[15]*.6)-1
 again,replayed,_=reissue(after,old,cfg,values,factors,boost,1001,economic_curve);assert again==after and replayed['replayed'];assert state['market_simulation']['books']['a']['rows'][0]['price']==oldprice
 # Extract the actual native purchase method to prove a cancelled old ask
 # cannot debit the player: lookup fails before add_ep/add_player.
 import ast,types,threading
 parsed=ast.parse((S/'market_simulation.py').read_text('utf8'));method=next(n for c in parsed.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='purchase');ns={'copy':copy,'integer':int,'now':lambda:1000};exec(compile(ast.Module(body=[method],type_ignores=[]),'actual_native_purchase','exec'),ns)
 calls=[];host=types.SimpleNamespace(STATE_LOCK=threading.RLock(),MAX_PLAYERS=100,_state=lambda:after,coach_me=lambda *a:{'money':{'ep':9999999999999999}},add_ep=lambda *a:calls.append('debit'),add_player=lambda *a:calls.append('grant'),_json=lambda d:d)
 engine=types.SimpleNamespace(h=host,valid_card=lambda *a:True,fail=lambda reason='INVALID_PARAM':dict(result=False,reason=reason),has_active=lambda *a:True,active=lambda *a:({}, {'players':[]},1),prepare=lambda *a:None,rows=lambda *a:[updated[0]])
 result=ns['purchase'](engine,sid,15,oldprice,{},b'');assert result==dict(result=False,reason='NOT_EXIST_OFFER') and not calls
 output=dict(status='PASS',catalogue_cards=len(cat['rows']),base_values_and_curve_shape_unchanged=True,grade_and_factor_checks=checks,peak_grade20_ep=peak,native_reference_ceiling=(2**53-1)//3,checks=['All grades1..20 increase at both market bounds; +1 rows byte-equivalent','No native quote ceiling ties; +1 increases remain strict after every multiplier','System quote withdrawal/reissue preserves count, expiry, consumed rows and hidden unquoted rows','Player offers/assets/wallets/completed sales and NPC original costs are untouched','Old stale unit quotes cannot survive at a thousandth of current value','Quote transition is copy-isolated and idempotent','Actual purchase rejects cancelled old price before any debit/grant'],formal_activated=False)
 (P/'regression.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(output,ensure_ascii=False))
if __name__=='__main__':main()
