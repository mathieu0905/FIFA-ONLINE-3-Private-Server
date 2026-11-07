from pathlib import Path
import json,urllib.request,ssl,time,hashlib,collections
root=Path('D:/fifaol3/market-supply-v3');records=json.loads((root/'installation.json').read_text('utf8'));server=Path(records[0]['server'])
def request(path):
 start=time.monotonic()
 with urllib.request.urlopen('https://127.0.0.1'+path,context=ssl._create_unverified_context(),timeout=30) as r:data=json.load(r)
 return data,round(time.monotonic()-start,3)
pre_request=json.loads((server/'gamedata/state.json').read_text('utf8'))
top,latency=request('/transfer/top/50')
assert len(top)==50 and {11,12,13,14,15,16,17,18,19,20}<={r['grade'] for r in top}
for grade in (8,10,14,20):
 row=next(r for r in top if r['grade']==grade)
 details,_=request('/transfer/search/'+str(row['spid']))
 assert row in details,(grade,row)
after=json.loads((server/'gamedata/state.json').read_text('utf8'));before=json.loads((Path(records[0]['backup'])/'state.json').read_text('utf8'))
def assets(state):
 state=json.loads(json.dumps(state));state.pop('market_simulation',None)
 for coach in state.get('coaches',[]):coach.pop('_market_owner',None)
 return state
assert assets(after)==assets(pre_request),'GET changed player assets'
oldplayers={str(p.get('_id') or p['spid']):p for p in before['teams']['0']['players']}
newplayers={str(p.get('_id') or p['spid']):p for p in after['teams']['0']['players']}
assert all(newplayers.get(key)==value for key,value in oldplayers.items()),'Existing card changed'
concurrent_additions=len(newplayers)-len(oldplayers)
assert hashlib.sha256((server/'gamedata/shop.json').read_bytes()).hexdigest()==records[0]['assets']['gamedata/shop.json']
report={'protocol_verified':True,'native_verified':False,'latency_seconds':latency,'unique_players':len({r['spid'] for r in top}),'grade_counts':dict(collections.Counter(r['grade'] for r in top)),'get_preserves_player_assets':True,'all_preinstall_cards_unchanged':True,'concurrent_card_additions':concurrent_additions,'shop_unchanged':True,'top':top,'supply_version':after['market_simulation']['supply_version']}
(root/'live-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:v for k,v in report.items() if k!='top'},ensure_ascii=False))

