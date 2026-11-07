from pathlib import Path
import json,hashlib,ssl,urllib.request,sys
W=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
def read_state():return json.loads((S/'gamedata/state.json').read_text(encoding='utf-8-sig'))
def business(st):return {k:v for k,v in st.items() if k!='market_simulation'}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
before=read_state();shop=sha(S/'gamedata/shop.json');rates=sha(S/'gamedata/enhancement_rates.json')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path):
 with opener.open('https://127.0.0.1'+path,timeout=10) as response:return json.load(response)
rules=get('/info/enhancement/protection/rules');assert rules['version']=='protection40-v1' and rules['fraction_percent']==40 and rules['ordinary_fee_replaced'] is True
me=get('/coach/me');rows=[x for x in me.get('items',[]) if x.get('itemid')==1000090];assert len(rows)==1,rows
assert '40%' in rows[0]['staticdata']['name']
with opener.open('http://127.0.0.1:8088/api/enhancement',timeout=10) as response:settings=json.load(response)
assert len(settings['rates'])==19
preview_evidence=None
if not before.get('enhance_restore'):
 coach=next(c for c in before['coaches'] if c['_id']==before['defaultcoachid']);slot=coach['slot'];cards=before['teams'][str(slot)]['players']
 for a in cards:
  if not 5<=a.get('grade',0)<=19 or a.get('locked') or a.get('lock'):continue
  matches=[b for b in cards if b is not a and b['spid']==a['spid'] and b.get('grade',0)==1 and not b.get('lock') and not b.get('locked')]
  if not matches:continue
  b=matches[0];iid=lambda p:str(p.get('_id') or p['spid'])
  q=get('/player/'+iid(a)+'/enhance2.5/'+iid(b)+'/preview/0/1000090/-1')
  if q.get('result'):
   fee=q['protection']['fee'];assert q['enhancepay']==fee==q['protection']['total_ep'] and '40%' in q['protection']['label']
   preview_evidence={'actual_owned_pair_readonly':True,'quoted_fee':fee,'no_action_executed':True};break
result=dict(status='LIVE_READ_ONLY_PASS',rules=rules,client_selection_count=len(rows),default_probabilities_unchanged=sha(S/'gamedata/enhancement_rates.json')==rates,
 manager_assets_unchanged=digest(business(before))==digest(business(read_state())),shop_unchanged=shop==sha(S/'gamedata/shop.json'),preview=preview_evidence,
 native_pass=False,actual_paid_upgrade_executed=False)
assert result['manager_assets_unchanged'] and result['shop_unchanged'] and result['default_probabilities_unchanged']
(W/'live-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True,indent=2))
