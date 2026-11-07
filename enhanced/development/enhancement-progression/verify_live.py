from pathlib import Path
import json,ssl,urllib.request,hashlib
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
read=lambda:json.loads((S/'gamedata/state.json').read_text(encoding='utf-8-sig'))
business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path,admin=False):
 with op.open(('http://127.0.0.1:8088' if admin else 'https://127.0.0.1')+path,timeout=12) as r:return json.load(r)
before=read();shop=sha(S/'gamedata/shop.json');rates=sha(S/'gamedata/enhancement_rates.json')
rules=get('/info/enhancement/progression/rules');settings=get('/api/enhancement',True)
expected=[100,95,90,85,80,75,70,65,60,55,50,45,35,28,20,14,9,6,4]
assert list(settings['rates'].values())==expected and settings['rates']==settings['defaults']
assert rules['active_probabilities']==settings['rates'] and rules['failure_grades']['5']==5 and rules['failure_grades']['10']==10 and rules['failure_grades']['13']==12
assert rules['normal_fee_percent']==2 and rules['protection_percent']==40
protect=get('/info/enhancement/protection/rules');assert protect['fraction_percent']==40 and protect['ordinary_fee_replaced']
market=get('/api/market_status',True);assert market['npc_exchange']['initialized'] and market['npc_exchange']['agents']==32
players=get('/api/players',True)['players'];assert players
st=read();slot=next(c['slot'] for c in st['coaches'] if c['_id']==st['defaultcoachid']);cards=st['teams'][str(slot)]['players'];iid=lambda p:str(p.get('_id') or p['spid'])
previews=[]
for a in sorted(cards,key=lambda p:p.get('grade',0),reverse=True):
 g=a.get('grade',0)
 if not 5<=g<=19 or a.get('lock') or a.get('locked'):continue
 materials=[b for b in cards if b is not a and b['spid']==a['spid'] and b.get('grade',0)==1 and not b.get('lock') and not b.get('locked')]
 if not materials:continue
 b=materials[0];q=get('/player/'+iid(a)+'/enhance2.5/'+iid(b)+'/preview/0/-1/-1')
 if not q.get('result'):continue
 price=next(p['price'] for p in players if str(p['id'])==iid(a));fee=max(1000,(price*2+99)//100)
 assert q['enhancepay']==fee and q['probability']==settings['rates'][str(g)]
 previews.append(dict(current_grade=g,next_grade=g+1,probability=q['probability'],ordinary_fee=fee,current_displayed_value=price,read_only=True))
 if len(previews)>=3:break
assert business(before)==business(read()),'Live assets changed: keep latest progress, do not restore old snapshot'
assert sha(S/'gamedata/shop.json')==shop and sha(S/'gamedata/enhancement_rates.json')==rates
result=dict(status='FORMAL_ACTIVE_PROTOCOL_PASS',rates=settings['rates'],rules=rules,actual_owned_pair_previews=previews,npc_exchange_active=True,
 manager_assets_unchanged=True,shop_unchanged=True,custom_rates_file_unchanged=True,real_paid_upgrade_executed=False,native_pass=False)
(W/'live-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='rules'},ensure_ascii=True,indent=2))
