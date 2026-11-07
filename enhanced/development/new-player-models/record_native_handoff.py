"""Read-only formal integrity checks and honest interrupted native-QA record."""
from pathlib import Path
import hashlib,json,datetime,urllib.request
R=Path(__file__).resolve().parent
P=Path(json.loads((R/'current-native-session.json').read_text('utf8'))['private_server'])
M=json.loads((P/'model-session.json').read_text('utf8'))
S=Path('D:/FO3ID/server'); C=Path('D:/FO3ID/32795')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
changed=[r for r,h in M['production_code_hashes'].items() if sha(S/r)!=h]
client_changed=[r for r,h in M['current_client_hashes'].items() if sha(C/r)!=h]
before=json.loads((P/'model-state-before-fixture.json').read_text('utf8'))
after=json.loads((S/'gamedata/state.json').read_text('utf8'))
state_diff=[]
def diff(a,b,path=''):
 if type(a)!=type(b):state_diff.append(dict(path=path,before=a,after=b));return
 if isinstance(a,dict):
  for k in a.keys()|b.keys():diff(a.get(k),b.get(k),path+'/'+k)
 elif isinstance(a,list):
  if len(a)!=len(b):state_diff.append(dict(path=path+'/length',before=len(a),after=len(b)))
  for i,(x,y) in enumerate(zip(a,b)):diff(x,y,path+'/'+str(i))
 elif a!=b:state_diff.append(dict(path=path,before=a,after=b))
diff(before,after)
non_market_diff=[x for x in state_diff if not x['path'].startswith('/market_simulation/')]
with urllib.request.urlopen('http://127.0.0.1:8088/api/summary',timeout=5) as f:summary=json.load(f)
result=dict(status='NATIVE_QA_STOPPED_BY_USER_NO_MODEL_VERDICT',recorded_at=datetime.datetime.now().astimezone().isoformat(),
 private_server=str(P),formal_source_changed=changed,formal_client_changed=client_changed,formal_state_diff=state_diff,
 non_market_state_diff=non_market_diff,
 formal_card_identity_list_preserved=[(x.get('_id',str(x['spid'])),x['spid']) for x in before['teams']['0']['players']]==[(x.get('_id',str(x['spid'])),x['spid']) for x in after['teams']['0']['players']],
 formal_squad_preserved=before['teams']['0']['squad']==after['teams']['0']['squad'],
 formal_players=summary['players'],formal_team2=summary['team2'],formal_coach=summary['coach'],
 production_fixture_written=False,private_state_copied_back=False,near_models_observed=[],match_observed=False,
 blocker='Startup notice remained visible. User observed Computer Use prevented mouse entering game; disabling Computer Use restored input.',
 cause_scope='User-reported input conflict; not an independently established engine or model fault.',
 computer_use_stopped=True,formal_services_restored=True,
 screenshot=str(R/'audit/native-20261106/notice-blocked.png'),
 logs=str(P/'captures'))
(R/'audit/native-20261106/result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
delivery=json.loads((R/'delivery-status.json').read_text('utf8'))
delivery['status']='NINE_MODELS_INSTALLED_OFFLINE_PASS_NATIVE_QA_INTERRUPTED'
delivery['latest_native_attempt']=str(R/'audit/native-20261106/result.json')
delivery['native_limitation']=result['blocker']
(R/'delivery-status.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='formal_state_diff'},ensure_ascii=False))
assert not [r for r in changed if r!='gamedata/state.json'] and not client_changed,'Formal resources differ: review before handoff'
