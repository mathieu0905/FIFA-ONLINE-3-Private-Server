"""Execute the emitted AVM2 UI paths with native objects/network mocked in memory."""
from pathlib import Path
import json,sys
R=Path(__file__).parent;HELP=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
sys.path.insert(0,str(HELP));from avm_patch import ABC
source=(HELP/'test_bp_client.py').read_text('utf8').split('def load(name):')[0]
source=source.replace('elif op==0x55:',"elif op==0x42:\n                n=r.u30();args=[pop() for _ in range(n)][::-1];fn=pop();stack.append(fn(*args))\n            elif op==0x55:")
source=source.replace('elif op==0xa9:', 'elif op==0xa3:b=pop();a=pop();stack.append(a/b)\n            elif op==0xa9:')
ns={'__file__':str(HELP/'test_bp_client.py')};exec(source,ns);VM=ns['VM'];Function=ns['Function']
class UI(VM):
 def request(self,uri,body=None):
  row=dict(uri=uri,body=body,handlers={});self.puts.append(row);request={}
  def on(event,fn,owner):row['handlers'][event]=fn;return request
  request.update(on=on,end=lambda:None);return request
 def __init__(self,a,owner):
  super().__init__(a,owner)
  self.globals['ResourceController']['instance'].update(pushGET=self.request,pushPOST=self.request)
  self.globals.update(Sprite=self.sprite,TextField=self.textfield,TextFormat=lambda *args:dict(args=args),
    NetEvent=dict(ON_COMPLETE='complete',ON_ERROR='error'),ShopController=dict(instance=dict(invalidateShoplist=lambda:self.calls.append('refresh'))))
 def sprite(self):
  sprite=dict(children=[],graphics=dict(beginFill=lambda x:self.calls.append(('fill',x)),drawRoundRect=lambda *args:self.calls.append(('roundrect',args)),endFill=lambda:None),listeners={})
  sprite['getChildByName']=lambda n:next((c for c in sprite['children'] if c.get('name')==n),None)
  def add(c):sprite['children'].append(c);return c
  sprite['addChild']=add;sprite['addEventListener']=lambda event,fn:sprite['listeners'].__setitem__(event,fn)
  return sprite
 def textfield(self):return {}
report=json.loads((R/'client-build.json').read_text('utf8'));a=ABC((R/'renderer.updated.abc').read_bytes());ids=report['methods']
mapping=json.loads((R/'client-insertions.json').read_text('utf8'));start=mapping['4']['mapping']['206']
checks=[]
def fixture():
 owner=dict(_chainRoundState=None,data={},titleLabel=dict(x=382,width=500),countLabel=dict(x=1009),tileList=dict(x=48,width=1100),children=[])
 owner['getChildByName']=lambda n:next((c for c in owner['children'] if c.get('name')==n),None)
 owner['addChild']=lambda c:owner['children'].append(c) or c
 return owner,UI(a,owner)
def bind(vm,owner,data):owner['data']=data;vm.run(4,[data],start=start)
event=dict(stopImmediatePropagation=lambda:None)
data=dict(shopid=71250201,round_buy_supported=True,round_buy_enabled=True)
owner,vm=fixture();bind(vm,owner,data);button=owner['children'][0]
assert button['visible'] and button['mouseEnabled'] and button['x']==974 and button['y']==1
assert owner['titleLabel']['x']+owner['titleLabel']['width']<=owner['countLabel']['x']<button['x']
assert ('roundrect',(0,0,170,27,8)) in vm.calls and button['children'][0]['text']=='一键购买本轮'
bind(vm,owner,data);assert len(owner['children'])==1 and len(button['listeners'])==1
checks.append('One native display-list button, header does not overlap counter/cards, renderer reuse creates no duplicate listener')
bind(vm,owner,dict(shopid=70000001));assert not button['visible'] and owner['countLabel']['x']==1009 and owner['titleLabel']['width']==500
bind(vm,owner,data);click=button['listeners']['click'];vm.run(click.mid,[event]);vm.run(click.mid,[event]);assert len(vm.puts)==1 and vm.puts[0]['uri']=='/shop/chain/round/quote?root=71250201'
assert not button['mouseEnabled'] and owner['_chainRoundState']['busy']
quote=dict(root=71250201,signature='signed-quote-for-this-round',nonce='test-only')
vm.run(vm.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,quote=quote,message='本轮余档总价 439300 点券'))])
dialog=vm.dialogs[-1];assert dialog['message']=='本轮余档总价 439300 点券' and dialog['okayButtonLabel']=='购买本轮'
vm.run(dialog['buttonHandler'].mid,[dict(type='cancel')]);assert len(vm.puts)==1 and not owner['_chainRoundState']['busy']
checks.append('Repeated clicks only request one quote; explicit total/confirmation; cancel sends zero purchase')
vm.run(click.mid,[event]);vm.run(vm.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,quote=quote,message='本轮余档总价 439300 点券'))]);dialog=vm.dialogs[-1]
vm.run(dialog['buttonHandler'].mid,[dict(type='ok')]);assert vm.puts[-1]['uri']=='/shop/chain/round/purchase' and vm.puts[-1]['body']==dict(quote=quote)
assert owner['_chainRoundState']['purchasePending'];n=len(vm.puts);vm.run(click.mid,[event]);assert len(vm.puts)==n
checks.append('Only confirmation POSTs the exact signed quote; while pending no second purchase request')
vm.run(vm.puts[-1]['handlers']['error'].mid,[{}]);assert not owner['_chainRoundState']['busy'] and owner['_chainRoundState']['quote']==quote
assert button['children'][0]['text']=='重试本轮购买'
vm.run(click.mid,[event]);assert len(vm.puts)==n+1 and vm.puts[-1]['uri']=='/shop/chain/round/purchase' and vm.puts[-1]['body']==dict(quote=quote)
checks.append('POST network failure retains approved quote; retry reuses same receipt key and never quotes the next round')
vm.run(vm.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,message='本轮完成'))]);assert 'refresh' in vm.calls and not owner['_chainRoundState']['purchasePending'] and owner['_chainRoundState']['quote'] is None
assert button['children'][0]['text']=='一键购买本轮';checks.append('Success refreshes native shop controller, releases busy state and restores label')
bind(vm,owner,dict(data,round_buy_enabled=False));assert not button['mouseEnabled'];n=len(vm.puts);vm.run(click.mid,[event]);assert len(vm.puts)==n
checks.append('Completed/blocked round cannot emit quote/purchase')
bind(vm,owner,data);vm.run(click.mid,[event]);vm.run(vm.puts[-1]['handlers']['error'].mid,[{}]);assert not owner['_chainRoundState']['busy'] and owner['_chainRoundState']['quote'] is None
checks.append('Quote error releases the button with no approved purchase')
for mid in ids.values():assert len(a.A['sig'][mid])==1
checks.append('Every mouse/network/dialog callback declares exactly one argument; no zero-argument completion mismatch')
(R/'client-tests.json').write_text(json.dumps(dict(status='PASS',count=len(checks),checks=checks,native_verified=False),indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',count=len(checks))))
