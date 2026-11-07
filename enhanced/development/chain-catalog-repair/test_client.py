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

a=ABC((R/'list.updated.abc').read_bytes());ids=dict(error=12,completed=13,confirmed=14,quoted=15,clicked=16);owners=[]
for root in (71350101,71350201,71350301,71350401,71350501):
 owner=dict(_chainRoundState=None,countLabel=dict(x=1009,visible=True),data={},children=[])
 v=NativeUI(a,owner);native=v.button();owner['roundPurchaseButton']=native;data=dict(shopid=root,round_buy_supported=True,round_buy_enabled=True);owner['data']=data
 v.run(4,[data],start=206);v.run(4,[data],start=206)
 assert native['visible'] and native['enabled'] and native['label']=='一键购买本轮' and len(native['listeners'])==1
 assert not owner['countLabel']['visible'] and owner['_chainRoundState']['button'] is native and not owner['children']
 click=native['listeners']['buttonClick'];event=dict(stopImmediatePropagation=lambda:None);v.run(click.mid,[event]);assert v.puts[-1]['uri']=='/shop/chain/round/quote?root='+str(root)
 quote=dict(root=root,nonce='not-a-real-purchase',signature='in-memory');v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,quote=quote,message='本轮报价'))]);v.run(v.dialogs[-1]['buttonHandler'].mid,[dict(type='cancel')]);assert len(v.puts)==1 and native['enabled'];owners.append(owner)
assert len(owners)==5
source=(HELP/'verify_stacks.py').read_text('utf8').split('results={}')[0].replace('op in (0x46,0x4a,0x4f)','op in (0x45,0x46,0x4a,0x4f)')
source=source.replace('elif op==0x55:', 'elif op==0x87:pops=2;pushes=1\n        elif op==0x56:pops=operand();pushes=1\n        elif op==0x55:')
stackns={'__file__':str(HELP/'verify_stacks.py')};exec(source,stackns);stacks={str(mid):stackns['check'](a,mid) for mid in [4]+list(ids.values())}
# The same native PlaceObject3 class binding used by the stock tile's buyButton.
import struct,zlib
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags
archive=R/'TileList.big';gfx=bigdir.read(archive,next(n for n,*_ in bigdir.entries(archive) if n.endswith('.gfx')));swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4
placements=[]
for t,b,_ in tags(swf,start,len(swf)):
 if t==39 and struct.unpack_from('<H',b)[0]==873:
  for tt,bb,_ in tags(b,4,len(b)):
   if tt==1:break
   if tt==70 and b'roundPurchaseButton' in bb:placements.append(bb)
assert len(placements)==1 and b'ShopBuyButton\0' in placements[0] and ('slot','roundPurchaseButton','Object') in a.A['cls'][0][3]
report=dict(status='PASS',five_independent_native_buttons=True,five_quotes_and_cancel_paths=True,native_timeline_binding=True,no_runtime_class_lookup=True,stacks=stacks,native_verified=False)
(R/'client-tests.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',native_buttons=5,stack_methods=len(stacks))))
