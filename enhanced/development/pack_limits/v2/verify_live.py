"""Read-only verification of the installed store. No purchases, grants or asset writes."""
from pathlib import Path
import hashlib,json,ssl,urllib.request
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(path):
    with opener.open('https://127.0.0.1'+path,timeout=45) as response:return json.load(response)
def admin(name,data):
    request=urllib.request.Request('http://127.0.0.1:8088/api/'+name,data=json.dumps(data).encode(),headers={'X-FO3-Admin':'1','Content-Type':'application/json','X-FO3-Lang':'zh'})
    with opener.open(request,timeout=20) as response:return json.load(response)
def protected():
    state=json.loads((S/'gamedata/state.json').read_text(encoding='utf8'))
    return dict(defaultcoachid=state.get('defaultcoachid'),coaches=state['coaches'],teams=state['teams'])
before=protected();checks=[]
def check(name,value):
    assert value,name
    checks.append(name)
cfg=json.loads((S/'gamedata/product_packs.json').read_text(encoding='utf8'))
rows=get('/shop/list');byid={row['product']['itemid']:row for row in rows}
check('All 54 new high-strength season and choice SKUs appear in live native store',all(int(i) in byid for i in cfg['strength_packs']))
check('Old 54 +1 SKUs no longer sold',not set(cfg['retired_sale_items']).intersection(byid))
check('Both risk packs and all three multi-pack bundles appear',all(int(i) in byid for key in ('risk_packs','bundles') for i in cfg[key]))
for key in ('strength_packs','risk_packs'):
    for itemid,definition in cfg[key].items():
        row=byid[int(itemid)];native=row['product']['staticdata']
        assert native['name']==definition['name']
        if definition.get('mode')=='choice':assert '+8' in native['name']
        else:assert '+6' in native['name'] and '+11' in native['name']
        assert '独立' in native['description']
        assert native['bunches'][0]['price']==definition['price']
        assert row['limitcountperaccount']==cfg['limits'][itemid]['count']
        assert 0 <= row['remainedperaccount'] <= cfg['limits'][itemid]['count']
check('Live names, enhancement ranges and independent quota descriptions match frozen definitions',True)
for itemid,definition in cfg['bundles'].items():
    row=byid[int(itemid)]
    assert row['product']['staticdata']['bunches'][0]['price']==definition['price']
    assert row['limitcountperaccount']==cfg['limits'][itemid]['count']
check('Live new pack and bundle prices and per-product caps match frozen rules',True)
for root,track in cfg['chains'].items():
    assert '10轮' in byid[int(root)]['chainedproductname']
check('Both chain pages expose ten rounds',True)
default=admin('pack_probability_preview',dict(min_grade=6,grade=11,probability_mode='formula'))
check('Live probability formula returns 30/28/25/10/6/1',default['grade_probabilities']==[30,28,25,10,6,1])
manual=admin('pack_probability_preview',dict(min_grade=6,grade=11,probability_mode='manual',grade_probabilities=[25,25,25,15,8,2]))
check('Live probability editor accepts valid manual odds',manual['grade_probabilities']==[25,25,25,15,8,2])
bad=admin('pack_probability_preview',dict(min_grade=6,grade=11,probability_mode='manual',grade_probabilities=[25,25,25,15,8,3]))
check('Live probability editor rejects total other than 100%',bool(bad.get('error')))
check('Read-only verification preserved manager, all cards, balance and squads',before==protected())
report=dict(status='LIVE_PROTOCOL_PASS',checks=checks,products=len(rows),purchases=0,grants=0,native_render='PENDING')
(R/'live-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status=report['status'],checks=len(checks),products=len(rows)),ensure_ascii=True))
