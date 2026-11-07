"""Append a renderer state slot, native display-list button and explicit round quote UI."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
HELP=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
sys.path.insert(0,str(HELP));import avm_patch as avm
from avm_patch import ABC,Code,u30,parse,dis
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags,tag
R=Path(__file__).parent;SOURCE=Path(r'D:\FO3ID\32795\data\ui\components\TileList.big')
def sha(b):return hashlib.sha256(b).hexdigest()
def build():
 raw=SOURCE.read_bytes();member=next(n for n,*_ in bigdir.entries(SOURCE) if n.endswith('.gfx'));g=bigdir.read(SOURCE,member)
 s=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(s[8]>>3)+7)//8+4;ts=list(tags(s,start,len(s)));matches=[]
 for ix,(t,b,r) in enumerate(ts):
  if t!=82:continue
  p=b.index(b'\0',4)+1;a=ABC(b[p:])
  if a.A['cls'][0][0]=='ShopChainedListItemRenderer' and any(x[1]=='_itemsDataProvider' for x in a.A['cls'][0][3]):matches.append((ix,p,b,a))
 assert len(matches)==1
 ix,p,body,a=matches[0];state=a.name('_chainRoundState');object_type=a.name('Object')
 def owner(c):return c.op(0x5d,state)
 def st(c):return owner(c).op(0x66,state)
 def prop(c,n):return st(c).prop(n)
 def assign(c,n,fn):st(c);fn(c);c.set(n)
 def caption(c,text):prop(c,'button').string('caption').call('getChildByName',1).string(text).set('text')
 def reset(c,clear=False):
  assign(c,'busy',lambda c:c.op(0x27))
  prop(c,'button').op(0x26).set('mouseEnabled');prop(c,'button').number(1).set('alpha')
  if clear:
   assign(c,'quote',lambda c:c.op(0x20));assign(c,'purchasePending',lambda c:c.op(0x27));caption(c,'一键购买本轮')
 def dialog(c,message,handler=None):
  c.lex('Dialog','fok.controls').string('title').string('本轮连锁购买').string('message');message(c)
  c.string('autoSizing').op(0x26).string('align').string('left').string('okayButtonLabel').string('购买本轮' if handler is not None else '确定')
  c.string('buttonType').lex('Dialog','fok.controls').prop('BUTTON_OK')
  n=6
  if handler is not None:
   c.lex('Dialog','fok.controls').prop('BUTTON_CANCEL').op(0xa9)
   c.string('cancelButtonLabel').string('取消').string('buttonHandler').op(0x40,handler);n+=2
  c.op(0x55,n).call('showMessage',1).op(0x29)
 def request(c,method,uri,complete,error,post=False):
  c.lex('ResourceController','fok.net').prop('instance');uri(c)
  if post:c.string('quote');prop(c,'quote');c.op(0x55,1)
  c.call(method,2 if post else 1).lex('NetEvent','fok.events').prop('ON_COMPLETE').op(0x40,complete);owner(c);c.call('on',3)
  c.lex('NetEvent','fok.events').prop('ON_ERROR').op(0x40,error);owner(c);c.call('on',3).call('end',0).op(0x29)
 scope=a.A['body_records'][4]['fields'][2]+1;base=len(a.A['meth']);ids=dict(error=base,completed=base+1,confirmed=base+2,quoted=base+3,clicked=base+4)
 c=Code(a);reset(c)
 prop(c,'purchasePending').jump(0x12,'quote_error');caption(c,'重试本轮购买')
 dialog(c,lambda c:c.string('网络请求未完成。请点击“重试本轮购买”，系统会核对原请求，避免重复扣款。'));c.op(0x47)
 c.label('quote_error');reset(c,True);dialog(c,lambda c:c.string('获取本轮价格失败，请稍后重试。'));c.op(0x47)
 assert a.add_method(c.done(),scope)==ids['error']
 c=Code(a).local(1).prop('body').store(2);reset(c,True)
 c.local(2).jump(0x12,'bad_reply');c.local(2).prop('result').jump(0x12,'display')
 c.lex('ShopController','fok.net').prop('instance').call('invalidateShoplist',0).op(0x29)
 c.label('display');c.local(2).prop('message').jump(0x12,'bad_reply');dialog(c,lambda c:c.local(2).prop('message'));c.op(0x47)
 c.label('bad_reply');dialog(c,lambda c:c.string('本轮购买响应异常，请刷新商城核对余额和背包。'));c.op(0x47)
 assert a.add_method(c.done(),scope,3)==ids['completed']
 c=Code(a).lex('Dialog','fok.controls').call('close',0).op(0x29)
 c.local(1).prop('type').lex('DialogEvent','fok.events').prop('OK').jump(0x13,'buy')
 reset(c,True);c.op(0x47)
 c.label('buy');prop(c,'quote').jump(0x12,'no_quote');assign(c,'purchasePending',lambda c:c.op(0x26))
 request(c,'pushPOST',lambda c:c.string('/shop/chain/round/purchase'),ids['completed'],ids['error'],True);c.op(0x47)
 c.label('no_quote');reset(c,True);c.op(0x47)
 assert a.add_method(c.done(),scope)==ids['confirmed']
 c=Code(a).local(1).prop('body').store(2);c.local(2).jump(0x12,'failed');c.local(2).prop('result').jump(0x12,'failed')
 assign(c,'quote',lambda c:c.local(2).prop('quote'));dialog(c,lambda c:c.local(2).prop('message'),ids['confirmed']);c.op(0x47)
 c.label('failed');reset(c,True);dialog(c,lambda c:c.string('当前轮次无法获取购买报价，请刷新商城后重试。'));c.op(0x47)
 assert a.add_method(c.done(),scope,3)==ids['quoted']
 c=Code(a).local(1).call('stopImmediatePropagation',0).op(0x29)
 prop(c,'busy').jump(0x11,'done')
 owner(c).prop('data').jump(0x12,'done');owner(c).prop('data').prop('round_buy_enabled').jump(0x12,'done')
 assign(c,'busy',lambda c:c.op(0x26));prop(c,'button').op(0x27).set('mouseEnabled');prop(c,'button').number(6).number(10).op(0xa3).set('alpha')
 prop(c,'purchasePending').jump(0x12,'new_quote')
 request(c,'pushPOST',lambda c:c.string('/shop/chain/round/purchase'),ids['completed'],ids['error'],True);c.op(0x47)
 c.label('new_quote')
 request(c,'pushGET',lambda c:c.string('/shop/chain/round/quote?root=').raw(owner(Code(a)).prop('data').prop('shopid').done()).op(0xa0),ids['quoted'],ids['error'])
 c.label('done').op(0x47)
 assert a.add_method(c.done(),scope)==ids['clicked']
 # setData runs after the native title/counter and five stages have been bound.
 c=Code(a).local(1).jump(0x12,'done')
 c.local(0).op(0x66,state).jump(0x11,'state_exists')
 c.local(0).string('busy').op(0x27).string('quote').op(0x20).string('purchasePending').op(0x27)
 c.string('oldCountX').local(0).ownprop('countLabel').prop('x').string('oldTitleWidth').local(0).ownprop('titleLabel').prop('width').op(0x55,5).op(0x61,state)
 c.label('state_exists').local(0).string('chainRoundButton').call('getChildByName',1).store(5)
 c.local(5).jump(0x11,'button_exists')
 c.lex('Sprite','flash.display').op(0x42,0).store(5)
 c.local(5).string('chainRoundButton').set('name');c.local(5).op(0x26).set('buttonMode');c.local(5).op(0x27).set('mouseChildren')
 c.local(5).prop('graphics').number(0xd8b452).call('beginFill',1).op(0x29)
 c.local(5).prop('graphics')
 for n in [0,0,170,27,8]:c.number(n)
 c.call('drawRoundRect',5).op(0x29);c.local(5).prop('graphics').call('endFill',0).op(0x29)
 c.lex('TextField','flash.text').op(0x42,0).store(6)
 for n,v in [('name','caption'),('text','一键购买本轮')]:
  if n=='text':continue
  c.local(6).string(v).set(n)
 for n,v in [('width',166),('height',25),('x',2),('y',1)]:c.local(6).number(v).set(n)
 for n in ['selectable','mouseEnabled','embedFonts']:c.local(6).op(0x27).set(n)
 c.local(6).lex('TextFormat','flash.text').string('Microsoft YaHei').number(14).number(0x171717).op(0x26).op(0x42,4).set('defaultTextFormat')
 c.local(6).string('一键购买本轮').set('text')
 c.local(5).local(6).call('addChild',1).op(0x29)
 c.local(5).string('click').op(0x40,ids['clicked']).call('addEventListener',2).op(0x29)
 c.local(0).local(5).call('addChild',1).op(0x29)
 c.label('button_exists');st(c).local(5).set('button')
 c.local(5).local(1).prop('round_buy_supported').op(0x76).set('visible')
 c.local(1).prop('round_buy_supported').jump(0x11,'layout')
 c.local(0).ownprop('countLabel');prop(c,'oldCountX');c.set('x')
 c.local(0).ownprop('titleLabel');prop(c,'oldTitleWidth');c.set('width');c.jump(0x10,'done')
 c.label('layout').local(5).local(0).ownprop('tileList').prop('x').local(0).ownprop('tileList').prop('width').op(0xa0).number(174).op(0xa1).set('x')
 c.local(5).number(1).set('y')
 c.local(0).ownprop('countLabel').local(5).prop('x').number(180).op(0xa1).set('x')
 c.local(0).ownprop('titleLabel').local(5).prop('x').local(0).ownprop('titleLabel').prop('x').op(0xa1).number(190).op(0xa1).set('width')
 c.local(1).prop('round_buy_enabled').jump(0x12,'disabled');prop(c,'busy').jump(0x11,'disabled')
 c.local(5).op(0x26).set('mouseEnabled');c.local(5).number(1).set('alpha');c.jump(0x10,'label')
 c.label('disabled').local(5).op(0x27).set('mouseEnabled');c.local(5).number(6).number(10).op(0xa3).set('alpha')
 c.label('label');prop(c,'purchasePending').jump(0x12,'regular_label');caption(c,'重试本轮购买');c.jump(0x10,'done')
 c.label('regular_label');caption(c,'一键购买本轮')
 c.label('done');a.modify(4,{206:c.done()},locals_extra=2)
 patched=a.output()
 # Add a real Object slot to this sealed native renderer; do not write an
 # undeclared property or rely on a mutable server data object as UI storage.
 source=avm.SOURCE.replace('ii = r.u30(); inst.append([name, sup, ii, traits()])',
  "ii = r.u30(); tp=r.p; tr=traits(); A.setdefault('instance_trait_offsets',[]).append((tp,r.p)); inst.append([name,sup,ii,tr])")
 ns={'__name__':'trait_offsets'};exec(compile(source,'trait-offsets','exec'),ns);before=ns['parse'](patched,0);tp,end=before['instance_trait_offsets'][0];reader=avm.R(patched,tp);count=reader.u30();entries=reader.p
 slot=u30(state)+b'\x00'+u30(0)+u30(object_type)+u30(0)
 patched=patched[:tp]+u30(count+1)+patched[entries:end]+slot+patched[end:]
 checked=ABC(patched);assert ('slot','_chainRoundState','Object') in checked.A['cls'][0][3]
 assert all(checked.A['body'][m]==code for m,code in a.A['body'].items() if m!=4)
 verify={'__file__':str(HELP/'verify_stacks.py')}
 stack_source=(HELP/'verify_stacks.py').read_text('utf8').split('results={}')[0]
 stack_source=stack_source.replace('op in (0x46,0x4a,0x4f)','op in (0x45,0x46,0x4a,0x4f)').replace('elif op==0x55:', 'elif op==0x42:pops=1+operand();pushes=1\n        elif op==0x87:pops=2;pushes=1\n        elif op==0x55:')
 stack_source=stack_source.replace('elif op==0x55:', 'elif op==0x56:pops=operand();pushes=1\n        elif op==0x55:')
 exec(stack_source,verify)
 stacks={str(m):verify['check'](checked,m) for m in [4]+list(ids.values())}
 ts[ix]=(82,body[:p]+patched,tag(82,body[:p]+patched));updated=bytearray(s[:start]+b''.join(r for _,_,r in ts));struct.pack_into('<I',updated,4,len(updated))
 gfx=b'CFX'+updated[3:8]+zlib.compress(updated[8:],9)
 target=R/'TileList.big';target.write_bytes(raw);bigdir.patch(target,{member:gfx})
 assert bigdir.read(target,member)==gfx
 current=target.read_bytes()
 for n,o,size,usize in bigdir.entries(SOURCE):
  if n!=member:
   _,no,nsz,nu=next(e for e in bigdir.entries(target) if e[0]==n);assert (size,usize)==(nsz,nu) and raw[o:o+size]==current[no:no+nsz]
 (R/'TileList.updated.swf').write_bytes(updated);(R/'renderer.updated.abc').write_bytes(patched)
 (R/'client-insertions.json').write_text(json.dumps(a.insertions,indent=2),'utf8')
 (R/'client-disassembly.txt').write_text('\n\n'.join('method '+str(m)+'\n'+'\n'.join(dis(checked.A,checked.A['body'][m])) for m in [4]+list(ids.values())),'utf8')
 report=dict(status='BUILD_PASS',before_sha256=sha(raw),after_sha256=sha(current),methods=ids,scope=scope,stacks=stacks,
  non_target_methods_and_ABC_byte_identical=True,all_shapes_sprites_images_and_color_animations_unchanged=True,non_gfx_archive_payloads_identical=True,native_verified=False)
 (R/'client-build.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps(dict(status='BUILD_PASS',methods=ids,sha256=report['after_sha256'])))
if __name__=='__main__':build()
