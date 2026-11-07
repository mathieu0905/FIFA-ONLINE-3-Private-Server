from pathlib import Path
import urllib.request,json,time,hashlib
out=Path('D:/fifaol3/market-background');server=Path('D:/FO3ID/server')
def status():
 with urllib.request.urlopen('http://127.0.0.1:8088/api/market_status',timeout=20) as r:return json.load(r)
a=status();assert a['background']['running'] and a['background']['errors']==0,a.get('background')
print('FIRST',json.dumps(a['background']),flush=True)
# No market requests during this interval; the persistent worker must progress itself.
time.sleep(18)
b=status();assert b['background']['ticks']>a['background']['ticks'] and b['background']['errors']==0,b.get('background')
before=json.loads((out/'state-before.json').read_text('utf8'));after=json.loads((server/'gamedata/state.json').read_text('utf8'))
assert before['teams']==after['teams'],'Team changed during restart'
assert before['coaches']==after['coaches'],'Coach assets changed during restart'
shop_before=json.loads((out/'shop-before.json').read_text('utf-8-sig'))['Hash'].lower()
assert hashlib.sha256((server/'gamedata/shop.json').read_bytes()).hexdigest()==shop_before
result=dict(running=True,first=a['background'],second=b['background'],teams_coaches_shop_unchanged=True,real_offers=len(after.get('offers',[])),offer_statuses=[o.get('status') for o in after.get('offers',[])])
(out/'live-result.json').write_text(json.dumps(result,indent=2),'utf8');print(json.dumps(result),flush=True)
