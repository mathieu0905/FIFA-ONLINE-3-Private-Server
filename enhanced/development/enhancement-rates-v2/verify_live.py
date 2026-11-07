from pathlib import Path
import json,ssl,urllib.request,hashlib
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path,admin=False):
 with op.open(('http://127.0.0.1:8088' if admin else 'https://127.0.0.1')+path,timeout=10) as r:return json.load(r)
read=lambda:json.loads((S/'gamedata/state.json').read_text(encoding='utf-8-sig'))
biz=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
before=read();file_sha=hashlib.sha256((S/'gamedata/enhancement_rates.json').read_bytes()).hexdigest();settings=get('/api/enhancement',True);rules=get('/info/enhancement/progression/rules')
expected={str(g):v for g,v in zip(range(11,20),(20,15,12,10,8,6,5,4,3))}
assert {g:settings['rates'][g] for g in expected}==expected
assert settings['rates']==settings['defaults'] and rules['version']=='progression20-v2' and 'current +12' in rules['high_grade_point_bonus']
players=get('/api/players',True)['players'];st=read();slot=next(c['slot'] for c in st['coaches'] if c['_id']==st['defaultcoachid']);cards=st['teams'][str(slot)]['players'];iid=lambda p:str(p.get('_id') or p['spid']);previews=[]
for a in cards:
 g=a.get('grade',0)
 if g!=12 or a.get('lock') or a.get('locked'):continue
 mates=[b for b in cards if b is not a and b['spid']==a['spid'] and b.get('grade',0)==1 and not b.get('lock') and not b.get('locked')]
 if not mates:continue
 b=mates[0]
 for point,want in ((0,15),(1,16.5)):
  q=get('/player/'+iid(a)+'/enhance2.5/'+iid(b)+'/preview/'+str(point)+'/-1/-1');assert q['result'] and q['probability']==want,q
  price=next(p['price'] for p in players if str(p['id'])==iid(a));assert q['enhancepay']==max(1000,(price*2+99)//100)
  previews.append(dict(current_grade=12,next_grade=13,use_points=bool(point),probability=q['probability'],ordinary_fee=q['enhancepay'],read_only=True))
 break
assert previews,'No matching actual pair available; do not fabricate live test cards'
assert biz(before)==biz(read()) and hashlib.sha256((S/'gamedata/enhancement_rates.json').read_bytes()).hexdigest()==file_sha
r=dict(status='FORMAL_ACTIVE_PROTOCOL_PASS',user_rates=expected,actual_owned_previews=previews,version=rules['version'],assets_unchanged=True,rates_persisted_sha256=file_sha,native_pass=False,paid_upgrade_executed=False)
(W/'live-result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
