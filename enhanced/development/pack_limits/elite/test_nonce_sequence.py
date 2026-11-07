from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import hashlib,hmac,json,os,sys,uuid
R=Path(__file__).resolve().parent;P=R/'sandbox/server';sys.dont_write_bytecode=True
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
def audit(event,args):
    if event=='open':
        name,mode,flags=args
        if isinstance(name,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(name)).resolve().is_relative_to(R):raise PermissionError('Outside nonce fixture write')
sys.addaudithook(audit)
state_file=P/'gamedata/state.json';state=json.loads(state_file.read_text(encoding='utf8'));base=json.loads((P/'gamedata/product_packs.json').read_text(encoding='utf8'))
coach=next(c for c in state['coaches'] if c['_id']==state['defaultcoachid']);slot=str(coach['slot']);itemid=97300012
coach.pop('_admin_generation',None)
coach['items']=[x for x in coach.get('items',[]) if x['itemid']!=itemid]
raw=dict(_id=uuid.uuid4().hex,itemid=itemid,remains=2);coach['items'].append(raw)
def legacy_token(c,item):
    value=f'{c["_id"]}:{c.get("appat")}:{item["_id"]}:{item["itemid"]}:{item["remains"]}:{base["edition"]}'
    return item['_id']+'_pf_'+hmac.new(bytes.fromhex(base['token_key']),value.encode(),hashlib.sha256).hexdigest()[:24]
pending=legacy_token(coach,raw);iid=raw['_id'];old_complete=legacy_token(coach,dict(raw,_id=uuid.uuid4().hex))
existing=state['teams'][slot]['players'][0];old_player=dict(_id=existing.get('_id','synthetic-legacy-card'),spid=existing['spid'],grade=existing.get('grade',1),price=1)
coach.setdefault('risk_pack_receipts',{})[old_complete]=dict(player=old_player,chosen=None)
state_file.write_text(json.dumps(state),encoding='utf8')
import http_config as h
h.MAX_PLAYERS=10000
checks=[]
def check(label,value):
    assert value,label;checks.append(label);print(label,flush=True)
def saved():return h._state()
def coach_of():return h.my_coach(saved())
def item():return next(x for x in coach_of()['items'] if x['_id']==iid)
def count():return len(saved()['teams'][slot]['players'])
def token(raw_iid=iid):return next(x['_id'] for x in h.coach_items(saved(),h._default_slot(saved())) if x['_id'].startswith(raw_iid+'_pf_'))
def use(t):return json.loads(h.ep_item_use(t,'',b'{}')[1])
before=count();result=use(pending)
check('Pre-upgrade pending legacy token accepted once at initial unversioned sequence zero',result['result'] and not result.get('replayed') and count()==before+1 and item()['product_open_seq']==1 and item()['remains']==1)
first_card=result['player'];state=saved();h.inventory_add(h.my_coach(state),itemid,1);h._save(state)
next_token=token();check('Replenishing same iid to the original quantity preserves sequence and changes token',item()['remains']==2 and item()['product_open_seq']==1 and next_token!=pending)
before=count();result=use(next_token)
check('Fresh token grants a fresh card and consumes exactly one replenished pack',result['result'] and not result.get('replayed') and count()==before+1 and item()['remains']==1 and item()['product_open_seq']==2 and result['player']['_id']!=first_card['_id'])
before=state_file.read_bytes();again=use(pending)
check('Old consumed token replays original card without another debit or grant',again.get('replayed') and again['player']==first_card and state_file.read_bytes()==before)
before=count();again=use(old_complete)
check('Pre-upgrade completed receipt stays replayable without another card',again.get('replayed') and again['player']==old_player and count()==before)
state=saved();c=h.my_coach(state);c['risk_pack_receipts'].pop(pending);c['risk_pack_receipts'].pop(next_token);h.inventory_add(c,itemid,1);h._save(state)
before=state_file.read_bytes()
check('Pruned legacy and versioned stale tokens cannot revive after quantity matches again',not use(pending)['result'] and not use(next_token)['result'] and state_file.read_bytes()==before)
active=token();before=count()
with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(use,[active,active]))
check('Concurrent identical token grants once and replays once',all(r['result'] for r in results) and sum(bool(r.get('replayed')) for r in results)==1 and results[0]['player']['_id']==results[1]['player']['_id'] and count()==before+1 and item()['product_open_seq']==3)
active=token();before=state_file.read_bytes()
with patch.object(h,'_save',side_effect=OSError('injected save failure')):
    try:use(active)
    except OSError:pass
    else:raise AssertionError('Save failure not raised')
check('Save failure leaves sequence, packs, cards and receipt byte-identical',state_file.read_bytes()==before)
import persistence_guard
actual_replace=persistence_guard.os.replace
def fail_state_replace(src,dst):
    if Path(dst).resolve()==state_file.resolve():raise OSError('injected atomic state commit failure')
    return actual_replace(src,dst)
with patch.object(persistence_guard.os,'replace',side_effect=fail_state_replace):
    try:use(active)
    except OSError:pass
    else:raise AssertionError('Atomic commit failure not raised')
check('Real atomic state replacement failure also preserves all four asset fields',state_file.read_bytes()==before)
assert use(active)['result']
check('Normal exhaustion removes only the consumed stack',not any(x['_id']==iid for x in coach_of()['items']))
state=saved();new=h.inventory_add(h.my_coach(state),itemid,2);new_iid=new['_id'];h._save(state)
check('A fresh stack gets a new iid and sequence zero',new_iid!=iid and new['product_open_seq']==0)
new_token=token(new_iid);forged_legacy=legacy_token(coach_of(),new)
check('New stacks cannot accept a forged old-format token',not use(forged_legacy)['result'])
state=saved();h.my_coach(state)['_admin_generation']=uuid.uuid4().hex;h._save(state);before=state_file.read_bytes()
check('Manager lifecycle change rejects old pending token and completed receipts',not use(new_token)['result'] and not use(active)['result'] and not use(old_complete)['result'] and state_file.read_bytes()==before)
report=dict(status='PASS',count=len(checks),checks=checks,source_sha256=hashlib.sha256((P/'product_packs.py').read_bytes()).hexdigest(),formal_writes=False)
(R/'nonce-sequence-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',checks=len(checks))))
