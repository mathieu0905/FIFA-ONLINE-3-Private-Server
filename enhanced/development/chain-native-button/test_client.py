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

a=ABC((R/'list.updated.abc').read_bytes());ids=json.loads((R/'build.json').read_text('utf8'))['methods'];owner=dict(_chainRoundState=None,countLabel=dict(x=1009,visible=True),data={},children=[]);owner['addChild']=lambda b:owner['children'].append(b) or b;v=NativeUI(a,owner)
def bind(data):owner['data']=data;v.run(4,[data],start=206)
data=dict(shopid=71350401,round_buy_supported=True,round_buy_enabled=True);bind(data);button=owner['children'][0];assert button['label']=='一键购买本轮' and button['enabled'] and not owner['countLabel']['visible'];assert list(button['listeners'])==['buttonClick'];assert button['width']==190 and button['height']==27
bind(data);assert len(owner['children'])==1 and len(button['listeners'])==1
click=button['listeners']['buttonClick'];event=dict(stopImmediatePropagation=lambda:None);v.run(click.mid,[event]);v.run(click.mid,[event]);assert len(v.puts)==1 and not button['enabled']
quote=dict(root=71350401,nonce='in-memory',signature='signed');v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,quote=quote,message='本轮报价'))]);v.run(v.dialogs[-1]['buttonHandler'].mid,[dict(type='cancel')]);assert len(v.puts)==1 and button['enabled']
v.run(click.mid,[event]);v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,quote=quote,message='本轮报价'))]);v.run(v.dialogs[-1]['buttonHandler'].mid,[dict(type='ok')]);assert v.puts[-1]['body']==dict(quote=quote)
v.run(v.puts[-1]['handlers']['error'].mid,[{}]);assert button['label']=='重试本轮购买';v.run(click.mid,[event]);assert v.puts[-1]['body']==dict(quote=quote)
v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,message='完成'))]);assert 'refresh' in v.calls and button['label']=='一键购买本轮'
bind(dict(data,round_buy_enabled=False));assert not button['enabled'];bind(dict(shopid=70000001));assert not button['visible'] and owner['countLabel']['visible']
source=(HELP/'verify_stacks.py').read_text('utf8').split('results={}')[0].replace('op in (0x46,0x4a,0x4f)','op in (0x45,0x46,0x4a,0x4f)')
source=source.replace('elif op==0x55:', 'elif op==0x41:pops=operand()+2;pushes=1\n        elif op==0x42:pops=operand()+1;pushes=1\n        elif op==0x87:pops=2;pushes=1\n        elif op==0x56:pops=operand();pushes=1\n        elif op==0x55:')
stackns={'__file__':str(HELP/'verify_stacks.py')};exec(source,stackns);stacks={str(mid):stackns['check'](a,mid) for mid in [4]+list(ids.values())}
report=dict(status='PASS',native_class_contract='ShopBuyButton/ButtonEx',event_contract='scaleform.clik.events.ButtonEvent.CLICK',confirmation_cancel_retry_and_disabled_paths=True,stacks=stacks,native_verified=False)
(R/'client-tests.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',native_class='ShopBuyButton',methods=len(stacks))))
