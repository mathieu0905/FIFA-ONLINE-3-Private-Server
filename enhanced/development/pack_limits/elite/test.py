from pathlib import Path
import copy,hashlib,json,os,sys
from unittest.mock import patch
R=Path(__file__).resolve().parent;P=R/'sandbox/server'
sys.dont_write_bytecode=True
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
def audit(event,args):
    if event=='open':
        name,mode,flags=args
        if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(name)).resolve().is_relative_to(R):raise PermissionError('Outside elite fixture write')
sys.addaudithook(audit)
import http_config as h
checks=[]
def check(name,value):
    assert value,name
    checks.append(name);print(name,flush=True)
def call(itemid,root=None):
    body=dict(productid=itemid,bunch=0)
    if root:body['shopid']=root
    return json.loads(h.ENDPOINTS['/shop/purchase']('',json.dumps(body).encode())[1])
def decoded(result):return json.loads(result[1])
base=json.loads((P/'gamedata/product_packs.json').read_text(encoding='utf8'))
addon=json.loads((P/'gamedata/product_chain_elite.json').read_text(encoding='utf8'))
seed=h._state();h.my_coach(seed)['cash']=100000000;h._save(seed)
before_old=copy.deepcopy(seed.get('product_chain_rounds',{}))
check('Original issued configuration file remains byte-identical',hashlib.sha256((P/'gamedata/product_packs.json').read_bytes()).hexdigest()==json.loads((R/'baseline.json').read_text())['gamedata/product_packs.json'])
for itemid in addon['chain_only_items']:
    check('Exclusive cannot be bought as a standalone pack '+str(itemid),not call(itemid)['result'])
totals={}
for root,track in addon['chains'].items():
    root=int(root);h._save(copy.deepcopy(seed));cash=h.my_coach(h._state())['cash'];expected={}
    prior_other=h.pack_cadence.remaining(h._state(),97300011)
    check('Skip-ahead rejected '+str(root),not call(track['steps'][1],root)['result'])
    for itemid in track['steps']:
        definition=track['packages'][str(itemid)]
        for child,count in definition['contents']:expected[child]=expected.get(child,0)+count
        assert call(itemid,root)['result']
    state=h._state();coach=h.my_coach(state)
    assert cash-coach['cash']==sum(track['prices'][str(i)] for i in track['steps'])
    old={}
    for item in h.my_coach(seed).get('items',[]):old[item['itemid']]=old.get(item['itemid'],0)+item['remains']
    now={}
    for item in coach.get('items',[]):now[item['itemid']]=now.get(item['itemid'],0)+item['remains']
    assert all(now.get(child,0)-old.get(child,0)==count for child,count in expected.items())
    check('All five stages charge exact prices and grant all packs '+str(root),True)
    check('Per-product allowances are not consumed by chain rewards '+str(root),h.pack_cadence.remaining(state,97300011)==prior_other)
    check('Completed stage replay cannot charge twice '+str(root),not call(track['steps'][-1],root)['result'])
    state=h._state();record=state['product_chain_rounds'][str(root)];record.update(rounds=9,stage=4);h._save(state)
    assert call(track['round_steps'][-1][-1],root)['result']
    check('Tenth round completes and eleventh is refused '+str(root),not h.chained_entry(h._state(),root)['buy'] and not call(track['round_steps'][-1][-1],root)['result'])
    assert all(h._state().get('product_chain_rounds',{}).get(key)==value for key,value in before_old.items())
    totals[str(root)]=sum(expected.values())
check('Classic chains grant 68/873 packs; nostalgia round grants 50+2 exactly',totals=={'71230101':68,'71230201':873,'71231901':52})
h._save(copy.deepcopy(seed))
state=h._state();coach=h.my_coach(state);h.inventory_add(coach,97610910,1);h._save(state)
choice=addon['strength_packs']['97610910'];target=choice['tiers'][0]['pool'][0]
fn=next(fn for pattern,fn in h.ROUTES if pattern.pattern==r'/packchoice/(\d+)/search')
rows=decoded(fn('97610910','',b''))
check('New TOP10 native selection displays ten +11 candidates',len(rows)==10 and {r['grade'] for r in rows}=={11})
token=next(item['_id'] for item in h.coach_items(h._state(),h._default_slot(h._state())) if item['itemid']==97610910)
result=decoded(h.ep_item_use(token,'',json.dumps({'spids':[target]}).encode()))
check('Selecting TOP10 awards selected exact legendary card at +11',result['result'] and result['player']['spid']==target and result['player']['grade']==11)
count=len(h._state()['teams']['0']['players'])
again=decoded(h.ep_item_use(token,'',json.dumps({'spids':[target]}).encode()))
check('TOP10 opening replay grants no duplicate card',again['result'] and len(h._state()['teams']['0']['players'])==count)
state=h._state();coach=h.my_coach(state);h.inventory_add(coach,97700511,1);h._save(state)
token=next(item['_id'] for item in h.coach_items(h._state(),h._default_slot(h._state())) if item['itemid']==97700511)
result=decoded(h.ep_item_use(token,'',b'{}'))
check('Exclusive random legendary pack guarantees +11 and exact legend pool',result['result'] and result['player']['grade']==11 and result['player']['spid'] in addon['strength_packs']['97700511']['tiers'][0]['pool'])
check('Existing 12 choice packs remain fixed +8',all(h.pack_grades(int(i))==list(enumerate(d['grades'],1)) for i,d in base['strength_packs'].items() if d['mode']=='choice'))
rows=h.shop_list(h._state());ids={r['product']['itemid'] for r in rows}
check('Both elite chains appear while exclusives stay off standalone shelves',{71230101,71230201}<=ids and not set(addon['chain_only_items']) & ids)
(R/'test-results.json').write_text(json.dumps(dict(status='PASS',checks=checks,count=len(checks)),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='PASS',count=len(checks))))
