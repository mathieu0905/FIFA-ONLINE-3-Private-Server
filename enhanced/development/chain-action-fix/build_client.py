"""Bound native instance handlers and an unstretched header-size native skin."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));import avm_patch as avm
from avm_patch import ABC,Code,u30,dis
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags,tag
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');SRC=C/'data/ui/components/TileList.big';sha=lambda b:hashlib.sha256(b).hexdigest()
def body(a,mid,code):
 rec=a.A['body_records'][mid];fields=list(rec['fields']);fields[0]=max(fields[0],32);a.changed[mid]=u30(mid)+b''.join(u30(x) for x in fields)+u30(len(code))+code+rec['suffix']
def add_traits(data,traits):
 src=avm.SOURCE.replace('ii = r.u30(); inst.append([name, sup, ii, traits()])',"ii = r.u30(); tp=r.p; tr=traits(); A.setdefault('instance_trait_offsets',[]).append((tp,r.p)); inst.append([name,sup,ii,tr])")
 ns={'__name__':'trait_offsets'};exec(compile(src,'trait-offsets','exec'),ns);p=ns['parse'](data,0);at,end=p['instance_trait_offsets'][0];reader=avm.R(data,at);count=reader.u30();entries=reader.p
 return data[:at]+u30(count+len(traits))+data[entries:end]+b''.join(traits)+data[end:]
def build():
 raw=SRC.read_bytes();member=next(n for n,*_ in bigdir.entries(SRC) if n.endswith('.gfx'));gfx=bigdir.read(SRC,member);s=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(s[8]>>3)+7)//8+4;ts=list(tags(s,start,len(s)));hits=0;styles=0
 for ix,(t,b,r) in enumerate(ts):
  if t==39 and struct.unpack_from('<H',b)[0]==873:
   frames=list(tags(b,4,len(b)));parts=[]
   for tt,bb,rr in frames:
    if tt==70 and b'roundPurchaseButton\0' in bb:
     assert bb.count(b'ShopBuyButton\0')==1;bb=bb.replace(b'ShopBuyButton\0',b'BlackAquaButton\0');rr=tag(tt,bb);styles+=1
    parts.append(rr)
   nb=b[:4]+b''.join(parts);ts[ix]=(39,nb,tag(39,nb))
  if t!=82:continue
  pos=b.index(b'\0',4)+1;a=ABC(b[pos:]);cls=a.A['cls'][0] if a.A['cls'] else None
  if not cls or cls[0]!='ShopChainedListItemRenderer' or not any(x[1]=='roundPurchaseButton' for x in cls[3]):continue
  hits+=1;state=a.name('_chainRoundState');slot=a.name('roundPurchaseButton');scope=a.A['body_records'][4]['fields'][2]
  names=dict(error='_chainRoundError',completed='_chainRoundCompleted',confirmed='_chainRoundConfirmed',quoted='_chainRoundQuoted',clicked='_chainRoundClicked')
  ids={k:len(a.A['meth'])+i for i,k in enumerate(names)};traits=[]
  def code():return Code(a).local(0).op(0x30)
  def st(c):return c.local(0).op(0x66,state)
  def prop(c,n):return st(c).prop(n)
  def button(c):return c.local(0).op(0x66,slot)
  def assign(c,n,fn):st(c);fn(c);c.set(n)
  def caption(c,text):button(c).string(text).set('label');button(c).call('validateNow',0).op(0x29)
  def reset(c,clear=False):
   assign(c,'busy',lambda c:c.op(0x27));button(c);prop(c,'canBuy');c.set('enabled');button(c).number(1).set('alpha')
   if clear:assign(c,'quote',lambda c:c.op(0x20));assign(c,'purchasePending',lambda c:c.op(0x27));caption(c,'一键购买本轮')
  def dialog(c,message,handler=None):
   c.lex('Dialog','fok.controls').string('title').string('本轮连锁购买').string('message');message(c);c.string('autoSizing').op(0x26).string('align').string('left').string('okayButtonLabel').string('购买本轮' if handler else '确定').string('buttonType').lex('Dialog','fok.controls').prop('BUTTON_OK');n=6
   if handler:c.lex('Dialog','fok.controls').prop('BUTTON_CANCEL').op(0xa9);c.string('cancelButtonLabel').string('取消').string('buttonHandler').local(0).prop(names[handler]);n+=2
   c.op(0x55,n).call('showMessage',1).op(0x29)
  def request(c,method,uri,complete,post=False):
   c.lex('ResourceController','fok.net').prop('instance');uri(c)
   if post:c.string('quote');prop(c,'quote');c.op(0x55,1)
   c.call(method,2 if post else 1).lex('NetEvent','fok.events').prop('ON_COMPLETE').local(0).prop(names[complete]).local(0).call('on',3).lex('NetEvent','fok.events').prop('ON_ERROR').local(0).prop(names['error']).local(0).call('on',3).call('end',0).op(0x29)
  def emit(key,c):
   mid=a.add_method(c.done(),scope,3);assert mid==ids[key];traits.append(u30(a.name(names[key]))+b'\x01'+u30(0)+u30(mid))
  c=code();reset(c);prop(c,'purchasePending').jump(0x12,'quote_error');caption(c,'重试本轮购买');dialog(c,lambda c:c.string('购买请求尚未确认，请重试核对原请求，不会重复扣款。'));c.op(0x47);c.label('quote_error');reset(c,True);dialog(c,lambda c:c.string('获取本轮报价失败，请稍后重试。'));c.op(0x47);emit('error',c)
  c=code().local(1).prop('body').store(2);reset(c,True);c.local(2).jump(0x12,'bad');c.local(2).prop('result').jump(0x12,'display');c.lex('ShopController','fok.net').prop('instance').call('invalidateShoplist',0).op(0x29);c.label('display');c.local(2).prop('message').jump(0x12,'bad');dialog(c,lambda c:c.local(2).prop('message'));c.op(0x47);c.label('bad');dialog(c,lambda c:c.string('响应异常，请刷新商城核对余额和背包。'));c.op(0x47);emit('completed',c)
  c=code().lex('Dialog','fok.controls').call('close',0).op(0x29);c.local(1).prop('type').lex('DialogEvent','fok.events').prop('OK').jump(0x13,'buy');reset(c,True);c.op(0x47);c.label('buy');prop(c,'quote').jump(0x12,'missing');assign(c,'purchasePending',lambda c:c.op(0x26));caption(c,'正在购买…');request(c,'pushPOST',lambda c:c.string('/shop/chain/round/purchase'),'completed',True);c.op(0x47);c.label('missing');reset(c,True);c.op(0x47);emit('confirmed',c)
  c=code().local(1).prop('body').store(2);c.local(2).jump(0x12,'failed');c.local(2).prop('result').jump(0x12,'failed');assign(c,'quote',lambda c:c.local(2).prop('quote'));caption(c,'确认本轮报价');dialog(c,lambda c:c.local(2).prop('message'),'confirmed');c.op(0x47);c.label('failed');reset(c,True);dialog(c,lambda c:c.string('当前轮次无法报价，请刷新商城重试。'));c.op(0x47);emit('quoted',c)
  c=code().local(1).call('stopImmediatePropagation',0).op(0x29);prop(c,'busy').jump(0x11,'done');prop(c,'canBuy').jump(0x12,'done');assign(c,'busy',lambda c:c.op(0x26));button(c).op(0x27).set('enabled');prop(c,'purchasePending').jump(0x12,'new');caption(c,'核对原购买…');request(c,'pushPOST',lambda c:c.string('/shop/chain/round/purchase'),'completed',True);c.op(0x47);c.label('new');caption(c,'获取报价…');request(c,'pushGET',lambda c:c.string('/shop/chain/round/quote?root=').raw(prop(Code(a),'root').done()).op(0xa0),'quoted');c.label('done').op(0x47);emit('clicked',c)
  prefix=a.A['body'][4][:206];c=Code(a).local(1).jump(0x12,'done');button(c).jump(0x12,'done');st(c).jump(0x11,'exists')
  c.local(0).string('busy').op(0x27).string('quote').op(0x20).string('purchasePending').op(0x27).op(0x55,3).op(0x61,state)
  button(c).lex('ButtonEvent','scaleform.clik.events').prop('CLICK').local(0).prop(names['clicked']).call('addEventListener',2).op(0x29)
  for key,val in [('autoSize','none')]:button(c).string(val).set(key)
  for key,val in [('autoRepeat',False),('toggle',False),('selected',False),('enableInitCallback',False),('preventAutosizing',False),('selectable',True),('hoverable',True)]:button(c).op(0x26 if val else 0x27).set(key)
  button(c).number(172).number(30).call('setSize',2).op(0x29)
  c.label('exists');assign(c,'root',lambda c:c.local(1).prop('shopid'));assign(c,'canBuy',lambda c:c.local(1).prop('round_buy_enabled').op(0x76));button(c).local(1).prop('round_buy_supported').op(0x76).set('visible');c.local(0).ownprop('countLabel').local(1).prop('round_buy_supported').op(0x96).set('visible')
  prop(c,'canBuy').jump(0x12,'disabled');prop(c,'busy').jump(0x11,'disabled');button(c).op(0x26).set('enabled');c.jump(0x10,'caption');c.label('disabled');button(c).op(0x27).set('enabled')
  c.label('caption');prop(c,'busy').jump(0x11,'done');caption(c,'一键购买本轮');c.label('done').op(0x47);body(a,4,prefix+c.done());patched=add_traits(a.output(),traits);check=ABC(patched)
  assert all(('method',names[k],ids[k]) in check.A['cls'][0][3] for k in names)
  for mid,old in a.A['body'].items():
   if mid!=4:assert check.A['body'][mid]==old
  (R/'list.updated.abc').write_bytes(patched);(R/'methods.json').write_text(json.dumps(dict(ids=ids,names=names)),encoding='utf8');(R/'patched.txt').write_text('\n\n'.join('method '+str(i)+'\n'+'\n'.join(dis(check.A,check.A['body'][i])) for i in [4]+list(ids.values())),encoding='utf8');ts[ix]=(82,b[:pos]+patched,tag(82,b[:pos]+patched))
 assert hits==styles==1
 out=bytearray(s[:start]+b''.join(rr for _,_,rr in ts));struct.pack_into('<I',out,4,len(out));packed=b'CFX'+out[3:8]+zlib.compress(out[8:],9);target=R/'TileList.big';target.write_bytes(raw);bigdir.patch(target,{member:packed});assert bigdir.read(target,member)==packed
 report=dict(status='BUILD_PASS',client_before=sha(raw),client_after=sha(target.read_bytes()),server_before=sha((S/'product_packs.py').read_bytes()),native_skin='BlackAquaButton',button_size=[172,30],bound_instance_methods=ids,all_other_methods_including_completion_identical=True,native_verified=False)
 (R/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':build()
