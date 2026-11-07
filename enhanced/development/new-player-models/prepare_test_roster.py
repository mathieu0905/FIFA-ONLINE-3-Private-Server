"""Arrange nine model subjects only in the named private session's save."""
from pathlib import Path
import json,secrets,hashlib
R=Path(__file__).resolve().parent
session=json.loads((R/'current-native-session.json').read_text('utf8'));P=Path(session['private_server']).resolve()
assert P.parent==Path('D:/FO3QA/modern_player_integration_v2/private-servers').resolve() and P.name.startswith('model9-main-')
assert not (P/'model-test-roster.json').exists(),'Prepare a fresh private session instead of replacing its baseline'
state=P/'gamedata/state.json';before=state.read_bytes();st=json.loads(before);team=st['teams']['0']
subjects=json.loads((R/'integration-PASS.json').read_text('utf8'))['identities'];assert len(subjects)==9
ids={};added=[]
for row in subjects:
 cards=[p for p in team['players'] if p['spid']==row['spid']]
 if cards:p=cards[0]
 else:
  used={p.get('jersey') for p in team['players']};jersey=next((n for n in range(12,100) if n not in used),99)
  p=dict(_id=secrets.token_hex(12),spid=row['spid'],expandme='player',grade=1,jersey=jersey,jerseyname=row['name_zh']);team['players'].append(p);added.append(p['_id'])
 p.pop('team2',None);ids[row['playerid']]=p['_id']
assignments={4:243715,6:251854,7:257534,12:246669,13:252371,15:256790,16:238794,24:277643,26:256630}
old_positions=json.loads(json.dumps(team['squad']['positions']))
for slot in team['squad']['positions']:
 if slot['pos'] in assignments:
  pid=assignments[slot['pos']];slot.update(id=ids[pid],spid=next(r['spid'] for r in subjects if r['playerid']==pid))
team['squad']['captain']=ids[252371]
team['squad']['kickers']=[ids[p] for p in [238794,277643,252371,256630,257534]]
team['squad']['positions']=[p for p in team['squad']['positions'] if p['pos']<28]
starting={p['id'] for p in team['squad']['positions']}
for p in team['players']:
 if p.get('_id',str(p['spid'])) in starting:p.pop('team2',None)
 else:p['team2']=True
assert sum(x['pos']<28 for x in team['squad']['positions'])==11 and len(team['players'])<=200
(P/'model-state-before-fixture.json').write_bytes(before)
state.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding='utf8')
report=dict(status='PRIVATE_NINE_MODEL_FIXTURE_READY',private_server=str(P),added_instances=added,subject_ids=ids,previous_positions=old_positions,testing_positions=team['squad']['positions'],production_written=False,fixture_copied_to_production=False,source_private_state_sha256=hashlib.sha256(before).hexdigest())
(P/'model-test-roster.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(dict(status=report['status'],private_count=len(team['players']),added=len(added)),ensure_ascii=False))
