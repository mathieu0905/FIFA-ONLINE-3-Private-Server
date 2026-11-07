from pathlib import Path
from fractions import Fraction
from unittest.mock import patch
import copy,hashlib,hmac,json,os,sys
R=Path(__file__).resolve().parent;P=R/'sandbox/server';sys.dont_write_bytecode=True
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
def audit(event,args):
    if event=='open':
        name,mode,flags=args
        if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(name)).resolve().is_relative_to(R):raise PermissionError('Outside rights fixture write')
sys.addaudithook(audit)
import http_config as h
# These synthetic issuance checks do not test roster capacity; the live roster
# may already be full. Change only this isolated module's limit, never live data.
h.MAX_PLAYERS=max(h.MAX_PLAYERS,len(h._state()['teams'][str(h._default_slot(h._state()))]['players'])+20)
base=json.loads((P/'gamedata/product_packs.json').read_text(encoding='utf8'));addon=json.loads((P/'gamedata/product_chain_elite.json').read_text(encoding='utf8'))
checks=[]
def check(label,value):
    assert value,label
    checks.append(label);print(label,flush=True)
def chance(d):
    total=sum(t['weight'] for t in d['tiers'])
    return sum((Fraction(t['weight'],total)*Fraction(sum(s//1000000==84 for s in t['pool']),len(t['pool'])) for t in d['tiers']),Fraction())
old=base['risk_packs']['97300012'];safe=addon['risk_packs']['97310012']
check('Old paid risk distribution remains exact including 123/2524 Moments chance',h.product_packs['risk_packs']['97300012']==old and chance(old)==Fraction(123,2524))
check('New quality risk has zero Moments chance, 75/25 tiers and unchanged enhancement curve',chance(safe)==0 and [t['weight'] for t in safe['tiers']]==[75,25] and safe['grades']==old['grades'])
ratings=h.card_ovrs({spid for d in (safe,addon['risk_packs']['97310011']) for tier in d['tiers'] for spid in tier['pool']})
assert all(ratings[spid]+h.GRADE_BOOST[1]>=85 for d in (safe,addon['risk_packs']['97310011']) for tier in d['tiers'] for spid in tier['pool'])
assert all(spid//1000000 in {13,22,23,24,91,27,30,31,33,48,93} for d in (safe,addon['risk_packs']['97310011']) for tier in d['tiers'] for spid in tier['pool'])
check('Both new regular/risk editions guarantee 85+ base ability and exclude cold/ordinary seasons',True)
shock=addon['risk_packs']['97310011'];r9_probability=sum(Fraction(t['weight'],sum(t['weight'] for t in shock['tiers']))*Fraction(t['pool'].count(30037576),len(t['pool'])) for t in shock['tiers'])
check('Gamble pack is entirely classic legends; R9 exactly 5 percent and R9 +11 0.05 percent',r9_probability==Fraction(5,100) and r9_probability*Fraction(str(shock['grades'][10]))/Fraction(str(sum(shock['grades'])))==Fraction(5,10000) and all(s//1000000 in {27,30,31,33,48,93} for t in shock['tiers'] for s in t['pool']))
for section in ('risk_packs','strength_packs'):
    for itemid,definition in addon[section].items():
        if int(itemid) not in (97310084,97819084):assert chance(definition)==0
def reachable(itemid):
    text=str(itemid)
    if text in addon['risk_packs'] or text in addon['strength_packs']:return {itemid}
    if text in base['risk_packs'] or text in base['strength_packs']:return {itemid}
    if text in addon['bundles']:return set().union(*(reachable(child) for child,_ in addon['bundles'][text]['contents']))
    if text in base['bundles']:return set().union(*(reachable(child) for child,_ in base['bundles'][text]['contents']))
    raise AssertionError(itemid)
for root,track in addon['chains'].items():
    for definition in track['packages'].values():
        for child,_ in definition['contents']:
            assert not {97300011,97300012}.intersection(reachable(child))
            for issued in reachable(child):
                if issued==97819084:
                    assert int(root)==71231901 and child==97819084
                    continue
                text=str(issued);definition=addon['risk_packs'].get(text) or addon['strength_packs'].get(text) or base['risk_packs'].get(text) or base['strength_packs'].get(text)
                assert chance(definition)==0
check('Only the explicitly authorized 19-chain fixed +1 bonus reaches Moments; other new chain paths do not',True)
for itemid in (97300011,97300012,97400020,97400100):assert h.pack_cadence.policy(itemid)[1] and h.item_purchase_remaining(h._state(),itemid)==0
check('Both old standalone risks and both bundle future purchase entrances closed',True)
for oldid,newid in ((97400020,97410020),(97400100,97410100)):
    assert h.product_packs['bundles'][str(oldid)]==base['bundles'][str(oldid)]
    assert [list(row) for row in h.PACKAGES[oldid][2]]==base['bundles'][str(oldid)]['contents']
    assert 97300012 in reachable(oldid) and 97300012 not in reachable(newid)
check('Both already-paid old bundles keep original contents; only new versions switch reward SKU',True)
state=h._state();coach=h.my_coach(state)
# Mint a separate synthetic legacy instance; replenishment of a previously used
# stack is retained as a separate nonce regression rather than masking this proof.
coach['items']=[item for item in coach.get('items',[]) if item['itemid']!=97300012]
h.inventory_add(coach,97300012,1);h._save(state)
raw=next(x for x in coach['items'] if x['itemid']==97300012)
text=f'{coach["_id"]}:{coach.get("appat")}:{raw["_id"]}:{raw["itemid"]}:{raw["remains"]}:{base["edition"]}'
legacy_calculated_token=raw['_id']+'_pf_'+hmac.new(bytes.fromhex(base['token_key']),text.encode(),hashlib.sha256).hexdigest()[:24]
token=next(x['_id'] for x in h.coach_items(h._state(),h._default_slot(h._state())) if x['itemid']==97300012)
old_token=token
check('Held legacy SKU receives a valid versioned token without changing its frozen pool',token.startswith(raw['_id']+'_pf_'))
tier=next(t for t in h.product_packs['risk_packs']['97300012']['tiers'] if any(s//1000000==84 for s in t['pool']));spid=next(s for s in tier['pool'] if s//1000000==84)
with patch.object(h.random,'choices',side_effect=[[tier],[11]]),patch.object(h.random,'choice',return_value=spid):
    result=json.loads(h.ep_item_use(old_token,'',b'{}')[1])
print(json.dumps(dict(legacy_result=result.get('result'),legacy_replayed=result.get('replayed'),legacy_reason=result.get('reason'),legacy_player=result.get('player'),expected_spid=spid),ensure_ascii=True),flush=True)
check('Already-held retired old pack can still award season84 at +11 under original contract',result['result'] and result['player']['spid']==spid and result['player']['grade']==11)
before=len(h._state()['teams']['0']['players'])
again=json.loads(h.ep_item_use(old_token,'',b'{}')[1])
check('Legacy paid opening receipt replays without duplicate card',again['result'] and again.get('replayed') and len(h._state()['teams']['0']['players'])==before)
check('Original paid R9 configuration remains exactly unchanged',h.product_packs['risk_packs']['97300011']==base['risk_packs']['97300011'])
state=h._state();coach=h.my_coach(state);coach['items']=[item for item in coach.get('items',[]) if item['itemid']!=97300011];h.inventory_add(coach,97300011,1);h._save(state)
token=next(x['_id'] for x in h.coach_items(h._state(),h._default_slot(h._state())) if x['itemid']==97300011)
tier=h.product_packs['risk_packs']['97300011']['tiers'][1];spid=tier['pool'][0]
with patch.object(h.random,'choices',side_effect=[[tier],[11]]),patch.object(h.random,'choice',return_value=spid):result=json.loads(h.ep_item_use(token,'',b'{}')[1])
check('Original held R9 risk still opens at its frozen low-card +11 contract',result['result'] and result['player']['spid']==spid and result['player']['grade']==11)
check('Old frozen JSON bytes unchanged',hashlib.sha256((P/'gamedata/product_packs.json').read_bytes()).hexdigest()==json.loads((R/'baseline.json').read_text())['gamedata/product_packs.json'])
report=dict(status='PASS',count=len(checks),checks=checks,old_moments_chance=str(chance(old)),new_moments_chance=str(chance(safe)),formal_writes=False)
(R/'moments-rights-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=True))
