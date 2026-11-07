"""Reproduce the original same-stack replenishment bug in temporary data only."""
from pathlib import Path
import hashlib,json,os,sys
R=Path(__file__).resolve().parent;P=R/'sandbox/server';sys.dont_write_bytecode=True
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
import http_config as h
h.MAX_PLAYERS=10000
state=h._state();coach=h.my_coach(state);coach['items']=[x for x in coach['items'] if x['itemid']!=97300012];item=h.inventory_add(coach,97300012,2);iid=item['_id'];h._save(state)
def token():return next(x['_id'] for x in h.coach_items(h._state(),h._default_slot(h._state())) if x['itemid']==97300012)
first=token();out=json.loads(h.ep_item_use(first,'',b'{}')[1]);assert out['result']
state=h._state();h.inventory_add(h.my_coach(state),97300012,1);h._save(state)
second=token();before=len(h._state()['teams']['0']['players']);again=json.loads(h.ep_item_use(second,'',b'{}')[1]);state=h._state()
report=dict(status='REPRODUCED_ORIGINAL_BUG',same_iid=next(x for x in h.my_coach(state)['items'] if x['itemid']==97300012)['_id']==iid,same_token=first==second,replayed_old_card=again.get('replayed'),remaining=next(x for x in h.my_coach(state)['items'] if x['itemid']==97300012)['remains'],new_cards=len(state['teams']['0']['players'])-before,source_sha256=hashlib.sha256((P/'product_packs.py').read_bytes()).hexdigest(),formal_writes=False)
assert report['same_iid'] and report['same_token'] and report['replayed_old_card'] and report['remaining']==2 and report['new_cards']==0
(R/'nonce-bad-sample.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
