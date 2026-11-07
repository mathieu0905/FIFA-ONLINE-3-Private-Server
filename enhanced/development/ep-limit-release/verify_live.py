from pathlib import Path
import json,ssl,urllib.request
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
ctx=ssl._create_unverified_context()
def get(path):return json.load(urllib.request.urlopen('https://127.0.0.1'+path,context=ctx,timeout=15))
before=json.loads((R/'live-before-restart.json').read_text(encoding='utf-8'))
after={p:get(p) for p in ('/coach/me','/shop/list')}
b=before['/coach/me'];a=after['/coach/me']
assert a['money']==b['money'],(a['money'],b['money'])
old={p['_id']:p for p in b['team']['players']};new={p['_id']:p for p in a['team']['players']}
assert old.keys()==new.keys()
for key,x in old.items():
    y=new[key]
    assert y['price']==(max(1,x['price']//1000) if x['price'] else 0),(key,x['price'],y['price'])
    assert {k:v for k,v in x.items() if k!='price'}=={k:v for k,v in y.items() if k!='price'},key
assert after['/shop/list']==before['/shop/list'],'Live shop products changed'
assert (S/'gamedata/state.json').read_bytes()==(R/'state-before-restart.json').read_bytes()
assert (S/'gamedata/shop.json').read_bytes()==(R/'shop-before-restart.json').read_bytes()
summary=json.load(urllib.request.urlopen('http://127.0.0.1:8088/api/summary',timeout=15))
assert summary['coach']['ep_exact']==str(a['money']['ep'])
report=dict(status='LIVE_PROTOCOL_PASS',old_players_preserved=len(old),all_player_values_divided_by_1000=True,
            native_wallet_ep=a['money']['ep'],wallet_unchanged=True,full_live_shop_response_unchanged=True,
            state_shop_bytes_unchanged=True,admin_exact_balance=summary['coach']['ep_exact'],native_render='PENDING')
(R/'live-after-restart.json').write_text(json.dumps(after,ensure_ascii=False),encoding='utf-8')
(R/'live-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
