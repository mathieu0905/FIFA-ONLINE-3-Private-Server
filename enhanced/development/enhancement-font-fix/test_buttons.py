from pathlib import Path
import json,math
import test_ui as t
W=Path(__file__).parent;patch=json.loads((W/'TeamManagementPlayerEnhancementTabPage-button.patch.json').read_text())
first={'_id':'matthaus-main','grade':5};second={'_id':'matthaus-material','grade':3}
def run(cost=1324217915,balance=10494743721853,available=True,blocked=False,stale=False,old_cost=0):
 p=dict(first={'_id':'different'} if stale else first,second=second,enhancepay=cost,probability=100)
 if blocked:p['protection']=dict(blocked=True,label='本档已保级，请选择不用')
 o=dict(_preview=p,_available=available,_money=dict(ep=balance),_selectedTargets=[first,second],_enhanceCost=dict(ep=old_cost),enhanceButton=dict(enabled=False))
 t.run_insertion(t.a,patch,26,181,o);return o
o=run();assert o['enhanceButton']['enabled'] and o['_enhanceCost']['ep']==1324217915
assert run(old_cost=-1)['enhanceButton']['enabled']
assert not run(balance=1324217914)['enhanceButton']['enabled']
assert not run(available=False)['enhanceButton']['enabled']
assert not run(stale=True)['enhanceButton']['enabled']
for cost in (None,0,-1,'1324217915',float('nan'),float('inf')):assert not run(cost=cost)['enhanceButton']['enabled']
o=run(blocked=True,cost=0,balance=0);assert o['enhanceButton']['enabled']
vm=t.VM(t.a,o);vm.run(20,start=7);assert not vm.puts and vm.dialogs
calls=[];o={'updateControlButtons':lambda:calls.append('recompute')}
t.run_insertion(t.a,patch,22,23,o);assert calls==['recompute']
for mid,row in patch.items():
 old=bytes.fromhex(row['original']);new=bytes.fromhex(row['updated']);mapping={int(k):v for k,v in row['mapping'].items()};newins={at:(end,op,targets) for at,end,op,targets in t.instructions(new)}
 for at,end,op,targets in t.instructions(old):
  actual=mapping[end]-(end-at);ne,no,nt=newins[actual];assert no==op
  if targets is not None:assert nt==[mapping[k] for k in targets]
  else:assert old[at:end]==new[actual:ne]
r=dict(status='PASS',exact_reported_pair_ready_with_positive_affordable_preview=True,stale_cost_reconciled=True,insufficient_funds_and_busy_and_stale_pair_remain_disabled=True,invalid_fee_rejected=True,blocked_quote_click_zero_put=True,wallet_notification_recomputes=True,all_old_button_opcodes_and_branches_preserved=True,native_verified=False)
(W/'button-tests.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
