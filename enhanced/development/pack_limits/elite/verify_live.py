"""Verify elite chains on the real read-only APIs, without purchases or grants."""
from pathlib import Path
import hashlib,json,ssl,urllib.request
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(url):
    with opener.open(url,timeout=40) as response:return json.load(response)
def protected():
    value=json.loads((S/'gamedata/state.json').read_text(encoding='utf8'))
    return dict(coaches=value['coaches'],teams=value['teams'],defaultcoachid=value.get('defaultcoachid'))
before=protected();addon=json.loads((S/'gamedata/product_chain_elite.json').read_text(encoding='utf8'))
rows=get('https://127.0.0.1/shop/list');byid={row['shopid']:row for row in rows}
checks=[]
for root,track in addon['chains'].items():
    row=byid[int(root)];parts=[row]+row['chained'];assert len(parts)==5
    assert '10轮' in row['chainedproductname']
    for part,itemid in zip(parts,track['steps']):
        definition=track['packages'][str(itemid)];native=part['product']['staticdata']
        if len(native.get('items',[]))==1 and native['items'][0]['itemid']==itemid:
            native=native['items'][0]['staticdata']
        assert part['product']['itemid']==itemid
        assert native['name']==definition['name']
        assert native['bunches'][0]['price']==track['prices'][str(itemid)]
        assert [[item['itemid'],item['count']] for item in native['items']]==definition['contents']
        assert all(str(count) in native['description'] for _,count in definition['contents'])
    checks.append(track['name']+': five live stages, exact point prices, reward counts and ten rounds')
assert not set(addon['chain_only_items']).intersection(byid)
checks.append('Exclusive +11 packs remain chain-only')
admin=get('http://127.0.0.1:8088/api/shop')
packs={p['itemid']:p for p in admin['products'] if p['kind']=='packs'}
assert packs[97610910]['def']['min_grade']==packs[97610910]['def']['grade']==11
assert packs[97610910]['def']['grade_probabilities']==[100]
assert packs[97610910]['def']['probability_locked']
assert packs[97700511]['def']['min_grade']==packs[97700511]['def']['grade']==11
checks.append('Live admin exposes both new exclusive packs at guaranteed +11 with frozen odds')
assert not {97300011,97300012,97400020,97400100}.intersection(byid)
checks.append('Both old junk-risk packs and their old bundles are absent from live sale')
for itemid in (97310011,97310012):
    row=byid[itemid]['product']['staticdata'];definition=addon['risk_packs'][str(itemid)]
    assert row['name']==definition['name'] and row['bunches'][0]['price']==definition['price']
    assert definition['description'] in row['description'] and '100' in row['description']
    d=packs[itemid]['def']
    assert d['min_grade']==6 and d['grade']==11 and d['grade_probabilities']==[30,28,25,10,6,1]
    assert d['probability_locked'] and not packs[itemid]['hidden']
checks.append('Live new packs show exact names, prices, Chinese season descriptions, independent quotas and +6..11 odds')
shock=addon['risk_packs']['97310011']
assert sum(len(t['pool']) for t in shock['tiers'])==115
assert all(s//1000000 in {27,30,31,33,48,93} for t in shock['tiers'] for s in t['pool'])
checks.append('Published gamble pool contains only 115 classic legends, with no ordinary-season filler')
for itemid in (97410020,97410100):
    assert itemid in byid
    row=byid[itemid]['product']['staticdata']
    if len(row['items'])==1 and row['items'][0]['itemid']==itemid:row=row['items'][0]['staticdata']
    assert [[x['itemid'],x['count']] for x in row['items']]==addon['bundles'][str(itemid)]['contents']
checks.append('Both replacement bundles contain the new quality editions')
moments=byid[97310084]['product']['staticdata']
assert moments['name']==addon['risk_packs']['97310084']['name'] and moments['bunches'][0]['price']==600000
assert '每经理每周限购1包' in moments['description']
assert packs[97310084]['def']['min_grade']==packs[97310084]['def']['grade']==1
checks.append('Moments is live at fixed +1, 600000 points, one per manager per week')
base=json.loads((S/'gamedata/product_packs.json').read_text(encoding='utf8'))
for text,d in base['strength_packs'].items():
    i=int(text);assert i in byid
    grades=[g for g,w in enumerate(d['grades'],1) if w]
    assert packs[i]['def']['min_grade']==min(grades) and packs[i]['def']['grade']==max(grades)
    assert packs[i]['def']['grade_probabilities']==d['grades'][min(grades)-1:max(grades)]
    assert byid[i]['product']['staticdata']['name']==d['name']
checks.append('All 54 earlier upgraded season/choice packs remain live with their exact +6..11 or fixed +8 grades')
assert all(int(itemid) in byid for itemid in (71220101,71220201))
checks.append('Previously installed ten-round chains remain available')
assert hashlib.sha256((S/'gamedata/product_packs.json').read_bytes()).hexdigest()==json.loads((R/'baseline.json').read_text())['gamedata/product_packs.json']
checks.append('Previously issued base config preserved byte for byte')
assert before==protected()
checks.append('Read-only inspection preserved cards, manager, wallet, inventory and squads')
report=dict(status='LIVE_PROTOCOL_PASS',checks=checks,count=len(checks),purchases=0,grants=0,native_render='PENDING')
(R/'live-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status=report['status'],checks=len(checks)),ensure_ascii=True))
