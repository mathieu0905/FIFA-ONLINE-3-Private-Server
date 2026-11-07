"""Real handler regression with temporary state, no listener or game automation."""
from pathlib import Path
import copy, hashlib, json, os, sys, time
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;P=R/'sandbox/server';S=Path('D:/FO3ID/server')
os.environ.update(FO3_GAME='D:/FO3ID/32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
def audit(event,args):
    if event=='open':
        path,mode,flags=args
        if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Write outside temporary regression data')
sys.addaudithook(audit)
import http_config as h
assert Path(h.HERE).resolve()==P.resolve()
def decode(result):return json.loads(result[1])
def buy(i,root=None):return decode(h.ENDPOINTS['/shop/purchase']('',json.dumps(dict(productid=i,shopid=root or i,bunch=0)).encode()))
def row(root):return next(x for x in h.shop_list(h._state()) if x['shopid']==root)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
production_before={str(p):digest(p) for p in [S/'gamedata/state.json',S/'gamedata/shop.json',S/'product_packs.py',S/'gamedata/product_packs.json',S/'gamedata/product_chain_elite.json']}
checks=[]
def check(label,value):assert value,label;checks.append(label);print(label,flush=True)
seed=copy.deepcopy(h._state());h.my_coach(seed)['cash']=999000000
for i in (97961011,97960011):seed.get('product_purchase_counts',{}).pop(str(i),None)
def fresh(root=None):
    st=copy.deepcopy(seed)
    if root is not None:st.setdefault('product_chain_rounds',{})[str(root)]=dict(rounds=0,stage=0,owner=None,owner_appat=None)
    h._save(st)
def no_charge(fn):
    before=Path(h.STATE).read_bytes();out=fn();assert not out['result'];assert Path(h.STATE).read_bytes()==before;return out
fresh()
addon=json.loads((P/'gamedata/shop_value_products.json').read_text('utf-8'));cfg=h.product_packs
check('Every valued product has strict once < chain < ordinary quotes',all(v['quotes']['once']<v['quotes']['chain']<v['quotes']['ordinary'] for v in addon['value_prices'].values()))
from pack_value import ValueModel
class ArithmeticFixture:
    PACKS={1:('weighted',{})};PACKAGES={2:('bundle','icon',[(1,3)],'')};MONTHLY={};EP_ITEM=999;ES_ITEM=998;ITEMS={}
    product_packs={};pack_catalogue={}
    def pack_pool(self,i):return [(10,3),(20,1)]
    def pack_grades(self,i):return [(1,1),(2,3)]
    def player_value_price(self,s,g):return s*10*g
fake=ArithmeticFixture();arithmetic=ValueModel(fake,1)
check('Expected value uses both card and grade weights, then sums bundle contents',arithmetic.value(1)==218.75 and arithmetic.value(2)==656.25)
fake.product_packs={'strength_packs':{'1':{'mode':'choice'}}}
check('Choice value uses selectable maximum rather than random average',ValueModel(fake,1).value(1)==350)
check('Five rewards have increasing expected value and fixed 8/9/10/11/11 grades',
      all(a<b for a,b in zip([addon['value_prices'][str(i)]['expected_ep'] for i in range(71240101,71240106)], [addon['value_prices'][str(i)]['expected_ep'] for i in range(71240102,71240106)])) and
      [next(g for g,w in h.pack_grades(i) if w) for i in (97950008,97950009,97950010,97950011,97950111)]==[8,9,10,11,11])
check('Same final pack costs least once, then chain, then normal',h.product_price(97961011,1)<h.product_price(71240105,1)<h.product_price(97960011,1))
check('Old issued product/cadence/elite configuration remains exact',all(digest(P/'gamedata'/n)==digest(S/'gamedata'/n) for n in ('product_packs.json','product_chain_elite.json','pack_cadence.json')))
check('Retired high-strength chain cannot start a new round',not any(x['shopid']==71220101 for x in h.shop_list(h._state())) and not buy(71220101,71220101)['result'])
st=h._state();st.setdefault('product_chain_rounds',{})['71220101']=dict(rounds=0,stage=1,owner=None,owner_appat=None);h._save(st)
check('Existing unfinished retired round retains its progress and original price',row(71220101)['step']==1 and h.product_price(71220102,1)==15000)
no_charge(lambda:buy(71220101,71220101))
check('Existing unfinished old round can continue',buy(71220102,71220101)['result'])
def shape(root,done,complete=False,entry=None,verify_get=True):
    entry=row(root) if entry is None else entry;parts=[entry]+entry['chained']
    assert len(parts)==5 and entry['step']==min(done,4)
    assert all(p['shopid']==root and p['_id']==str(root) and p['index']==k+1 for k,p in enumerate(parts))
    for k,p in enumerate(parts):
        expected='complete' if complete or k<done else 'activity' if k==done else 'default'
        assert p['currentstep']==expected,(root,done,k,p['currentstep'],expected)
    if verify_get:
        counts=decode(h.ENDPOINTS['/shop/remained/limited']('',b''));quota=next(v for v in counts if v['shopid']==root)
        assert quota['step']==entry['step'] and quota['buy']==entry['buy']
        assert decode(h.from_file('/shop/remained/limited'))==counts
        assert next(v for v in decode(h.from_file('/shop/list')) if v['shopid']==root)['step']==entry['step']
    return entry
tracks={int(k):v for k,v in cfg['chains'].items() if int(k)!=71220101}
for root,t in tracks.items():
    fresh(root);shape(root,0);no_charge(lambda:buy(t['steps'][1],root))
    rounds_to_test=10 if root==71240101 else 2
    cash=h.my_coach(h._state())['cash'];paid=0;grants={}
    for round_index in range(rounds_to_test):
        for k,i in enumerate(t['round_steps'][round_index]):
            no_charge(lambda:buy(i,root+900000))
            cost=h.product_price(i,1);out=buy(i,root);assert out['result'] and out['spent']==cost;paid+=cost
            for child,n in t['packages'][str(i)]['contents']:grants[child]=grants.get(child,0)+n
            resources={x['uri']:x['body'] for x in out['resources']}
            assert '/shop/list' in resources and '/shop/remained/limited' in resources
            current=next(v for v in resources['/shop/list'] if v['shopid']==root)
            assert out['states'][str(root)]['step']==current['step'] and out['states'][str(root)]['buy']==current['buy']
            quota=next(v for v in resources['/shop/remained/limited'] if v['shopid']==root)
            assert quota['step']==current['step'] and quota['buy']==current['buy']
            check_get=round_index==0 and k in (1,4) or round_index+1>=t['rounds']
            if k<4:shape(root,k+1,entry=current,verify_get=check_get)
            elif round_index+1>=t['rounds']:shape(root,5,True,entry=current,verify_get=check_get)
            else:shape(root,0,entry=current,verify_get=check_get)
            no_charge(lambda:buy(i,root))
    assert cash-h.my_coach(h._state())['cash']==paid
    old={};now={}
    for item in h.my_coach(seed).get('items',[]):old[item['itemid']]=old.get(item['itemid'],0)+item['remains']
    for item in h.my_coach(h._state()).get('items',[]):now[item['itemid']]=now.get(item['itemid'],0)+item['remains']
    assert all(now.get(i,0)-old.get(i,0)==n for i,n in grants.items())
    check('Sequential state/resources/root IDs/exact cash+inventory/replay protection '+str(root),True)
fresh();before=h.my_coach(h._state())['cash'];price=h.product_price(97961011,1)
assert buy(97961011)['result'];assert before-h.my_coach(h._state())['cash']==price
no_charge(lambda:buy(97961011))
st=h._state();other=copy.deepcopy(h.my_coach(st));other.update(_id='temporary-other-manager',slot=1,appat='temporary-other');st['coaches'].append(other);st['teams']['1']=copy.deepcopy(st['teams']['0']);st['defaultcoachid']=other['_id'];h._save(st)
no_charge(lambda:buy(97961011))
check('Once-only offer persists across manager switch and repeated purchase',h.item_purchase_remaining(h._state(),97961011)==0)
fresh();assert buy(97960011)['result'];check('Ordinary matching offer has separate remaining count',h.item_purchase_remaining(h._state(),97960011)==4)
# Exercise the exact choice inventory token and selected result, without production assets.
fresh();st=h._state();h.inventory_add(h.my_coach(st),97950111,1);h._save(st)
fn=next(fn for p,fn in h.ROUTES if p.pattern==r'/packchoice/(\d+)/search')
choices=decode(fn('97950111','',b''));assert len(choices)==10 and {r['grade'] for r in choices}=={11}
token=next(x['_id'] for x in h.coach_items(h._state(),h._default_slot(h._state())) if x['itemid']==97950111)
selected=choices[0]['spid'];opened=decode(h.ep_item_use(token,'',json.dumps(dict(spids=[selected])).encode()))
assert opened['result'] and opened['player']['spid']==selected and opened['player']['grade']==11
check('Final choice pack actually grants selected +11, exact ten native candidates',True)
check('No regression writes outside temporary data; formal code/config stays exact',all(digest(p)==v for p,v in production_before.items() if not p.endswith(('state.json','shop.json'))))
started=time.perf_counter();h.shop_list(h._state());listing_ms=round((time.perf_counter()-started)*1000,2)
report=dict(status='PASS',checks=checks,production_written=False,native_verified=False,private_service_started=False)
report['listing_ms']=listing_ms
(R/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(dict(status='PASS',count=len(checks))))
