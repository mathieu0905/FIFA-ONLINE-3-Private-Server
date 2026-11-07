from pathlib import Path
import copy,hashlib,json,os,shutil,sys
from unittest.mock import patch
R=Path(__file__).resolve().parent;S=R/'sandbox/server';sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf8')
shutil.copyfile(R/'product_packs.py',S/'product_packs.py')
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(S));sys.argv=['http_config.py']
def audit(event,args):
    if event=='open':
        p,mode,flags=args
        if isinstance(p,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_CREAT|os.O_WRONLY|os.O_RDWR|os.O_TRUNC))):
            if not Path(os.fsdecode(p)).resolve().is_relative_to(R):raise PermissionError('Outside isolated workspace write')
sys.addaudithook(audit)
import http_config as h
checks=[]
def check(label,value):
    assert value,label;checks.append(label);print(label,flush=True)
def call(i,bunch=0,**kwargs):return json.loads(h.ENDPOINTS['/shop/purchase']('',json.dumps(dict(productid=i,bunch=bunch,**kwargs)).encode())[1])
def state():return h._state()
def raw():return (S/'gamedata/state.json').read_bytes()
cfg=h.product_packs
seed=state();h.my_coach(seed)['cash']=10**9
seed.pop('product_purchase_counts',None);seed.pop('product_chain_rounds',None)
seed['pack_catalogue_supply']={g:dict(period=h.pack_cadence.periods()['week'] if g.endswith('week') else h.today_wib(),used=9999) for g in ('season_day','legend_day','choice_week')}
seed['pack_cadence_supply']={g:dict(period=h.pack_cadence.periods()['week'] if g.endswith('week') else h.today_wib(),used=9999) for g in h.pack_cadence.config['limits']}
h._save(seed)
def reset():h._save(copy.deepcopy(seed))
original_draws=json.loads((S/'gamedata/pack_cadence.json').read_text(encoding='utf8'))
check('Original frozen cadence remains unchanged',h.pack_cadence.config==original_draws)
for i,d in h.pack_catalogue['items'].items():assert h.pack_pool(int(i))==[(s,1.) for s in d['pool']] and h.pack_grades(int(i))==[(1,1)]
check('All 54 issued catalogue draw rules and grades preserved',True)
check('Shared old exhausted counters no longer block separate CP allowance',h.pack_cadence.remaining(state(),97500022)==100)
check('Another SKU starts with its own 100 allowance',h.pack_cadence.remaining(state(),97500023)==100)
before_groups=copy.deepcopy(state()['pack_catalogue_supply'])
check('Ten-pack purchase succeeds',call(97500022,1)['result'])
check('Ten-pack consumes ten only from its product',h.pack_cadence.remaining(state(),97500022)==90 and h.pack_cadence.remaining(state(),97500023)==100)
check('Historical shared counters preserved, not cleared or increased',state()['pack_catalogue_supply']==before_groups)
check('First self-choice SKU purchase succeeds',call(97600022)['result'])
check('Choice SKUs do not share counts',h.pack_cadence.remaining(state(),97600022)==19 and h.pack_cadence.remaining(state(),97600023)==20)
check('Legend purchase succeeds despite historical shared exhaustion',call(97010004)['result'])
check('Legend and TOP100 have independent remaining',h.pack_cadence.remaining(state(),97010004)==19 and h.pack_cadence.remaining(state(),97010100)==20)
before=h.pack_cadence.remaining(state(),97300011)
check('Bulk twenty-pack gift purchase succeeds',call(97400020)['result'])
check('Gift has separate quota and does not spend child card-pack quota',h.pack_cadence.remaining(state(),97400020)==4 and h.pack_cadence.remaining(state(),97300011)==before)
for root,t in cfg['chains'].items():
    reset();root=int(root);old=copy.deepcopy(state().get('pack_cadence_chains'))
    first=t['round_steps'][0][0]
    bad=call(t['round_steps'][0][1],shopid=root)
    check('Chain rejects skipping stages '+str(root),not bad['result'])
    for round_index,steps in enumerate(t['round_steps']):
        row=h.chained_entry(state(),root)
        assert row['shopid']==root and row['product']['itemid']==steps[0] and f'第{round_index+1}/10轮' in row['chainedproductname']
        for i in steps:
            out=call(i,shopid=root);assert out['result'],(i,out)
        assert state()['product_chain_rounds'][str(root)]==dict(rounds=round_index+1,stage=0,owner=str(h.my_coach(state())['_id']),owner_appat=h.my_coach(state()).get('appat'))
        if round_index==0:
            before=raw();again=call(first,shopid=root);assert not again['result'] and raw()==before
    check('Chain completes 10 rounds with native five-stage pages '+str(root),not h.chained_entry(state(),root)['buy'])
    before=raw();again=call(t['round_steps'][-1][-1],shopid=root)
    check('Eleventh round and stale completed-stage request cannot charge '+str(root),not again['result'] and raw()==before)
    check('Old paid chain rights/progress never reset '+str(root),state().get('pack_cadence_chains')==old)
reset()
def grant(i):
    st=state();h.inventory_add(h.my_coach(st),i,2);h._save(st)
    return next(row['_id'] for row in h.coach_items(st,h._default_slot(st)) if row['itemid']==i)
token=grant(97300011);d=cfg['risk_packs']['97300011'];count=len(state()['teams']['0']['players'])
with patch.object(h.random,'choices',side_effect=[[d['tiers'][0]],[11]]):out=json.loads(h.ep_item_use(token,'',b'{}')[1])
check('Real open can award exact UL Ronaldo +11',out['result'] and out['player']['spid']==30037576 and out['player']['grade']==11)
before=raw();again=json.loads(h.ep_item_use(token,'',b'{}')[1])
check('Risk-pack repeated opening returns one receipt, no duplicate player',again.get('replayed') and raw()==before and len(state()['teams']['0']['players'])==count+1)
token=next(row['_id'] for row in h.coach_items(state(),h._default_slot(state())) if row['itemid']==97300011)
with patch.object(h.random,'choices',side_effect=[[d['tiers'][1]],[11]]):out=json.loads(h.ep_item_use(token,'',b'{}')[1])
check('Same random-strength pack can award a low ability card at +11',out['player']['spid'] in d['tiers'][1]['pool'] and out['player']['grade']==11)
check('Ronaldo tier exactly 0.1%; combined Ronaldo +11 exactly 0.001%',d['tiers'][0]['weight']/sum(t['weight'] for t in d['tiers'])==.001 and d['grades'][10]/sum(d['grades'])==.01)
dd=cfg['risk_packs']['97300012'];check('Broad variance +11 probability exactly 1%',dd['grades'][10]/sum(dd['grades'])==.01)
curve=[0]*5+[30,28,25,10,6,1]
check('All 42 new random season packs use approved +6..+11 curve',all(d['grades']==curve for d in cfg['strength_packs'].values() if d['mode']=='random'))
check('All 12 new choice packs remain fixed +8',all(d['grades']==[0]*7+[100] for d in cfg['strength_packs'].values() if d['mode']=='choice'))
token=grant(97600911);d=cfg['strength_packs']['97600911'];spid=d['tiers'][0]['pool'][0]
choices=json.loads(h.route('/packchoice/97600911/search')('',b'')[1])
check('New +8 choice UI receives exact ten frozen candidates',len(choices)==10 and all(x['grade']==8 for x in choices))
out=json.loads(h.ep_item_use(token,'',json.dumps({'spids':[spid]}).encode())[1])
check('New choice pack awards selected exact player at +8',out['result'] and out['player']['spid']==spid and out['player']['grade']==8)
st=state();st.setdefault('product_purchase_counts',{})['97500022']=dict(period=h.today_wib(),used=100);h._save(st);before=raw()
check('Exhausting one SKU rejects purchase without a debit',not call(97500022)['result'] and raw()==before)
check('Other SKU still available after first is exhausted',h.pack_cadence.remaining(state(),97500023)==100)
before=raw();listing=json.loads(h.ENDPOINTS['/shop/list']('',b'')[1]);byid={r['product']['itemid']:r for r in listing}
check('Native list exposes correct individual caps and both bundles',byid[97500022]['remained']==0 and byid[97500023]['remained']==100 and 97400100 in byid)
check('Old +1 packs retired from sale, owned draw rules retained',not (set(cfg['retired_sale_items'])&set(byid)))
for i in map(int,cfg['limits']):
    if i in cfg['retired_sale_items']:continue
    assert '本商品独立限购' in h.item_def(i)['description'] and '全账号每周共享' not in h.item_def(i)['description']
check('Every managed SKU description states independent limits',True)
check('Read-only native display does not mutate assets',raw()==before)
st=state();snapshot=copy.deepcopy(st);h.shop_list(st)
check('Shop snapshot cache never mutates its supplied state',st==snapshot)
report=dict(status='PASS',count=len(checks),checks=checks,production_state_written=False,tested_files={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ('product_packs.py','product_packs.json','http_config.py','pack_catalogue.py')})
(R/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False))
