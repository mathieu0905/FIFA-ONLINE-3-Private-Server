from pathlib import Path
import sys,json
R=Path(__file__).resolve().parent;HELP=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(HELP));from avm_patch import ABC
base=(R.parent/'chain-ui-fix/test_client.py').read_text('utf8').split("a=ABC((R/'list.updated.abc')")[0]
exec(compile(base,'native-contract-harness','exec'),globals())
# Add generic AVM2 call instruction used by getDefinitionByName.
src=(HELP/'test_bp_client.py').read_text('utf8').split('def load(name):')[0]
src=src.replace("elif op in (0x09,0x1d):pass","elif op in (0x02,0x09,0x1d):pass")
src=src.replace('elif op==0x55:', "elif op==0x41:\n                n=r.u30();args=[pop() for _ in range(n)][::-1];receiver=pop();fn=pop();stack.append(fn(*args))\n            elif op==0x42:\n                n=r.u30();args=[pop() for _ in range(n)][::-1];fn=pop();stack.append(fn(*args))\n            elif op==0x55:")
src=src.replace('elif op==0xa9:', 'elif op==0xa3:b=pop();a=pop();stack.append(a/b)\n            elif op==0xa9:')
ns={'__file__':str(HELP/'test_bp_client.py')};exec(src,ns)
class NativeUI(ns['VM']):
 def __init__(self,a,owner):
  super().__init__(a,owner);self.globals.update(ButtonEvent=dict(CLICK='buttonClick'),NetEvent=dict(ON_COMPLETE='complete',ON_ERROR='error'),ShopController=dict(instance=dict(invalidateShoplist=lambda:self.calls.append('refresh'))),getDefinitionByName=self.definition)
  self.globals['ResourceController']['instance'].update(pushGET=self.request,pushPOST=self.request)
 def definition(self,name):
  assert name=='ShopBuyButton';return self.button
 def button(self):
  b=dict(enabled=True,listeners={});b['setSize']=lambda w,h:b.update(width=w,height=h);b['validateNow']=lambda:None;b['addEventListener']=lambda e,f:b['listeners'].__setitem__(e,f);return b
 def request(self,uri,body=None):
  row=dict(uri=uri,body=body,handlers={});self.puts.append(row);req={}
  def on(e,f,owner):row['handlers'][e]=f;return req
  req.update(on=on,end=lambda:None);return req

a=ABC((R/'list.updated.abc').read_bytes());info=json.loads((R/'methods.json').read_text('utf8'));ids=info['ids'];names=info['names'];tests=[]
for root in (71350101,71350201,71350301,71350401,71350501):
 owner=dict(_chainRoundState=None,countLabel=dict(x=1009,visible=True),data=None,children=[])
 v=NativeUI(a,owner);button=v.button();owner['roundPurchaseButton']=button
 for k,mid in ids.items():owner[names[k]]=ns['Function'](mid,owner)
 data=dict(shopid=root,round_buy_supported=True,round_buy_enabled=True);v.run(4,[data],start=206);v.run(4,[data],start=206)
 assert owner['_chainRoundState']['root']==root and owner['_chainRoundState']['canBuy'] and button['width']==172 and button['height']==30 and len(button['listeners'])==1
 click=button['listeners']['buttonClick'];assert click.owner is owner and click.mid==ids['clicked']
 event=dict(target=button,currentTarget=button,stopImmediatePropagation=lambda:None);v.run(click.mid,[event]);assert len(v.puts)==1 and v.puts[-1]['uri']=='/shop/chain/round/quote?root='+str(root)
 assert button['label']=='获取报价…' and not button['enabled'];v.run(click.mid,[event]);assert len(v.puts)==1
 quote=dict(root=root,signature='signed',nonce='in-memory-only');handler=v.puts[-1]['handlers']['complete'];assert handler.owner is owner
 v.run(handler.mid,[dict(body=dict(result=True,quote=quote,message='本轮报价'))]);assert button['label']=='确认本轮报价';dialog=v.dialogs[-1];assert dialog['buttonHandler'].owner is owner
 v.run(dialog['buttonHandler'].mid,[dict(type='cancel')]);assert len(v.puts)==1 and button['enabled'] and button['label']=='一键购买本轮'
 v.run(click.mid,[event]);v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,quote=quote,message='本轮报价'))]);v.run(v.dialogs[-1]['buttonHandler'].mid,[dict(type='ok')]);assert v.puts[-1]['uri']=='/shop/chain/round/purchase' and v.puts[-1]['body']==dict(quote=quote)
 v.run(v.puts[-1]['handlers']['error'].mid,[{}]);assert button['label']=='重试本轮购买';v.run(click.mid,[event]);assert v.puts[-1]['body']==dict(quote=quote)
 v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,message='完成'))]);assert 'refresh' in v.calls and button['label']=='一键购买本轮'
 v.run(4,[dict(data,round_buy_enabled=False)],start=206);n=len(v.puts);v.run(click.mid,[event]);assert len(v.puts)==n and not button['enabled']
 tests.append(root)
source=(HELP/'verify_stacks.py').read_text('utf8').split('results={}')[0].replace('op in (0x46,0x4a,0x4f)','op in (0x45,0x46,0x4a,0x4f)')
source=source.replace('elif op==0x55:', 'elif op==0x87:pops=2;pushes=1\n        elif op==0x56:pops=operand();pushes=1\n        elif op==0x55:')
stackns={'__file__':str(HELP/'verify_stacks.py')};exec(source,stackns);stacks={str(mid):stackns['check'](a,mid) for mid in [4]+list(ids.values())}
from avm_patch import instructions
for mid in [4]+list(ids.values()):assert not any(op==0x40 for at,end,op,targets in instructions(a.A['body'][mid]))
assert all(('method',names[k],ids[k]) in a.A['cls'][0][3] for k in ids)
report=dict(status='PASS',roots=tests,instance_methods_have_explicit_renderer_receiver=True,no_newfunction_capture_in_event_or_network_or_dialog_paths=True,works_with_renderer_data_none=True,immediate_quote_loading_caption=True,cancel_sends_no_purchase=True,approved_retry_reuses_quote=True,stacks=stacks,native_verified=False)
(R/'client-tests.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',roots=len(tests),bound_methods=len(ids))))
