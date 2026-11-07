from pathlib import Path
import urllib.request,ssl,json,collections
R=Path(__file__).resolve().parent;op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(url):
 with op.open(url,timeout=20) as r:return json.load(r)
data=json.loads((R/'pricing.json').read_text('utf8'));plan=json.loads((R/'volume-after.json').read_text('utf8'))
status=get('http://127.0.0.1:8088/api/hot_update_status');assert status['revision']=='pack_base_prices_20261107_01' and status['watcher_running'] and status['error'] is None
rows=get('https://127.0.0.1/shop/list');ordinary=[];chains=[];manutd={}
for row in rows:
 if not row.get('visible',True):continue
 parts=[row]+(row['chained'] if isinstance(row.get('chained'),list) else [])
 for part in parts:
  if part.get('currentstep')=='complete':continue
  d=part['product']['staticdata'];key=str(d['itemid'])
  if key in data['prices']:
   assert all(b['price']==b['bunch']*data['prices'][key] for b in d['bunches']),(key,d['bunches'])
   if not isinstance(row.get('chained'),list):ordinary.append(int(key))
   if key in ('98448081','98448082','98448010'):manutd[key]=d['bunches']
 if isinstance(row.get('chained'),list):
  root=str(row['shopid']);response=get('https://127.0.0.1/shop/chain/round/quote?root='+root)
  if response.get('result'):
   q=response['quote'];assert q['total']==row['round_buy_total']==sum(plan[root]['prices'][str(i)] for i in q['steps'])
   expected=collections.Counter()
   for i in q['steps']:
    for c,n in plan[root]['packages'][str(i)]['contents']:expected[c]+=n
   assert collections.Counter(dict(q['rewards']))==expected
   chains.append(dict(root=root,total=q['total'],remaining_packs=sum(expected.values()),round=q['round']+1))
assert manutd['98448082'][0]['price']==manutd['98448010'][0]['price']==9901
assert manutd['98448082'][1]['price']==99010 and manutd['98448081'][0]['price']==1191
assert '/hot/market/supply/activate' in status['routes'] and '/item/{item_id}/use' in status['routes']
result=dict(status='LIVE_REPRICING_PASS',hot_status=status,ordinary_priced_rows=len(ordinary),chains=chains,manutd_prices=manutd,real_purchase_performed=False,native_verified=False)
(R/'live-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result))
