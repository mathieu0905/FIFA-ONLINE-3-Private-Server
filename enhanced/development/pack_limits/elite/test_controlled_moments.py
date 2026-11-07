from pathlib import Path
from unittest.mock import patch
import copy,datetime,hashlib,json,os,sys
R=Path(__file__).resolve().parent;P=R/'sandbox/server';sys.dont_write_bytecode=True
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
def audit(event,args):
    if event=='open':
        name,mode,flags=args
        if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(name)).resolve().is_relative_to(R):raise PermissionError('Outside controlled fixture write')
sys.addaudithook(audit)
import http_config as h
h.MAX_PLAYERS=max(h.MAX_PLAYERS,len(h._state()['teams'][str(h._default_slot(h._state()))]['players'])+20)
itemid=97310084;checks=[]
def check(label,value):
    assert value,label
    checks.append(label);print(label,flush=True)
def call(i=itemid):return json.loads(h.ENDPOINTS['/shop/purchase']('',json.dumps(dict(productid=i,bunch=0)).encode())[1])
def raw():return (P/'gamedata/state.json').read_bytes()
definition=h.product_packs['risk_packs'][str(itemid)]
check('Controlled issue is fixed +1, exactly 123 Moments, 600000 points',definition['grades']==[100] and definition['price']==600000 and len(definition['tiers'][0]['pool'])==123 and all(s//1000000==84 for s in definition['tiers'][0]['pool']))
check('Per-manager weekly cap exactly one',h.product_packs['limits'][str(itemid)]==dict(count=1,period='week',scope='manager'))
live_sources=[]
for i in h.PACKS:
    if h.pack_cadence.policy(i)[1] or not h.pack_cadence.active(i):continue
    if any(s//1000000==84 and w>0 for s,w in h.pack_pool(i)):live_sources.append(i)
check('Only one newly purchasable pack can award Moments',live_sources==[itemid])
addon=json.loads((P/'gamedata/product_chain_elite.json').read_text(encoding='utf8'))
assert not any(child==itemid for track in addon['chains'].values() for definition in track['packages'].values() for child,count in definition['contents'])
assert not any(child==itemid for bundle in addon['bundles'].values() for child,count in bundle['contents'])
check('Controlled Moments pack is not in any new bundle or chain',True)
check('Registered Moments remain excluded from NPC minting',set(definition['tiers'][0]['pool'])<=h.market_engine._legend_moments_bulk_npc_exclusion)
state=h._state();coach=h.my_coach(state);coach['cash']=100000000;coach.setdefault('product_purchase_counts',{}).pop(str(itemid),None);h._save(state)
original_id=state['defaultcoachid'];old_global=copy.deepcopy(state.get('product_purchase_counts',{}));before_cash=coach['cash']
check('First purchase succeeds',call()['result'])
state=h._state();coach=h.my_coach(state)
check('Exact debit and manager-only count',coach['cash']==before_cash-600000 and h.item_purchase_remaining(state,itemid)==0 and state.get('product_purchase_counts',{})==old_global and coach['product_purchase_counts'][str(itemid)]['used']==1)
before=raw();again=call()
check('Second purchase/replay refused without any debit or duplicated inventory',not again['result'] and raw()==before)
slot=max(c['slot'] for c in state['coaches'])+1;second=copy.deepcopy(coach);second.update(_id='fixture-elite-second-manager',slot=slot,cash=100000000,items=[]);second['product_purchase_counts']={}
state['coaches'].append(second);state['teams'][str(slot)]=copy.deepcopy(state['teams'][str(h._default_slot(state))]);state['defaultcoachid']=second['_id'];h._save(state)
check('Another manager starts with an independent weekly allowance',h.item_purchase_remaining(h._state(),itemid)==1 and call()['result'])
state=h._state();state['defaultcoachid']=original_id;h._save(state)
check('Returning manager keeps spent allowance',h.item_purchase_remaining(h._state(),itemid)==0)
day=datetime.date.fromisoformat(h.today_wib());next_week=(day+datetime.timedelta(days=7-day.weekday())).isoformat()
with patch.object(h,'today_wib',return_value=next_week):
    check('Allowance refreshes next week and permits one more purchase',h.item_purchase_remaining(h._state(),itemid)==1 and call()['result'] and h.item_purchase_remaining(h._state(),itemid)==0)
state=h._state();token=next(row['_id'] for row in h.coach_items(state,h._default_slot(state)) if row['itemid']==itemid)
result=json.loads(h.ep_item_use(token,'',b'{}')[1])
check('Opening awards an exact Moments candidate at +1',result['result'] and result['player']['spid'] in definition['tiers'][0]['pool'] and result['player']['grade']==1)
count=len(h._state()['teams']['0']['players']);again=json.loads(h.ep_item_use(token,'',b'{}')[1])
check('Opening replay is idempotent',again.get('replayed') and len(h._state()['teams']['0']['players'])==count)
report=dict(status='PASS',count=len(checks),checks=checks,only_active_moments_sku=live_sources,formal_writes=False)
(R/'controlled-moments-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=True))
