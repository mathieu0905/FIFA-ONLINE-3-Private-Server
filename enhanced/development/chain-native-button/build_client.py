"""Use the shipped ShopBuyButton and ButtonEvent.CLICK contract."""
from pathlib import Path
import sys,struct,zlib,json,hashlib,textwrap
sys.dont_write_bytecode=True
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));from avm_patch import ABC,Code,u30,dis
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags,tag
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');SOURCE=C/'data/ui/components/TileList.big';sha=lambda b:hashlib.sha256(b).hexdigest()
def body(a,mid,code):
 rec=a.A['body_records'][mid];fields=list(rec['fields']);fields[0]=max(32,fields[0]);a.changed[mid]=u30(mid)+b''.join(u30(x) for x in fields)+u30(len(code))+code+rec['suffix']
def build():
 raw=SOURCE.read_bytes();member=next(n for n,*_ in bigdir.entries(SOURCE) if n.endswith('.gfx'));g=bigdir.read(SOURCE,member);swf=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4;ts=list(tags(swf,start,len(swf)));hits=0
 for ix,(t,b,r) in enumerate(ts):
  if t!=82:continue
  pos=b.index(b'\0',4)+1;a=ABC(b[pos:]);cls=a.A['cls'][0] if a.A['cls'] else None
  if not cls or cls[0]!='ShopChainedListItemRenderer' or not any(x[1]=='_chainRoundState' for x in cls[3]):continue
  hits+=1
  # Append fresh purchase callbacks while preserving existing methods verbatim.
  src=(R.parent/'chain-round-buy/build_client.py').read_text('utf8');frag=textwrap.dedent(' '+src[src.index("state=a.name('_chainRoundState')"):src.index(' # setData runs after')])
  frag=frag.replace("prop(c,'button').string('caption').call('getChildByName',1).string(text).set('text')", "prop(c,'button').string(text).set('label')")
  frag=frag.replace("set('mouseEnabled')","set('enabled')")
  scope={'a':a,'Code':Code};exec(compile(frag,'native-button-callbacks','exec'),scope);ids=scope['ids'];state=a.name('_chainRoundState');prefix=a.A['body'][4][:206]
  def st(c):return c.local(0).op(0x66,state)
  def button(c):return st(c).prop('button')
  c=Code(a).local(1).jump(0x12,'done');st(c).jump(0x11,'exists')
  c.local(0).string('busy').op(0x27).string('quote').op(0x20).string('purchasePending').op(0x27).op(0x55,3).op(0x61,state)
  # Same exported class used by buyButton in the shipped chain-tile timeline.
  c.lex('getDefinitionByName','flash.utils').op(0x20).string('ShopBuyButton').op(0x41,1).op(0x42,0).store(5)
  c.local(5).string('chainRoundNativeButton').set('name');c.local(5).op(0x27).set('focusable')
  c.local(5).number(190).number(27).call('setSize',2).op(0x29)
  c.local(5).lex('ButtonEvent','scaleform.clik.events').prop('CLICK').op(0x40,ids['clicked']).call('addEventListener',2).op(0x29)
  c.local(0).local(5).call('addChild',1).op(0x29);st(c).local(5).set('button')
  c.label('exists');button(c).local(0).ownprop('countLabel').prop('x').set('x');button(c).number(2).set('y')
  button(c).local(1).prop('round_buy_supported').op(0x76).set('visible')
  c.local(0).ownprop('countLabel').local(1).prop('round_buy_supported').op(0x96).set('visible')
  c.local(1).prop('round_buy_enabled').jump(0x12,'disabled');st(c).prop('busy').jump(0x11,'disabled')
  button(c).op(0x26).set('enabled');c.jump(0x10,'caption')
  c.label('disabled');button(c).op(0x27).set('enabled')
  c.label('caption');st(c).prop('purchasePending').jump(0x12,'normal');button(c).string('重试本轮购买').set('label');c.jump(0x10,'validate')
  c.label('normal');button(c).string('一键购买本轮').set('label')
  c.label('validate');button(c).call('validateNow',0).op(0x29)
  c.label('done').op(0x47);body(a,4,prefix+c.done());patched=a.output();checked=ABC(patched)
  for mid,code in a.A['body'].items():
   if mid!=4:assert checked.A['body'][mid]==code
  (R/'list.updated.abc').write_bytes(patched);(R/'list-patched.txt').write_text('\n\n'.join('method '+str(i)+'\n'+'\n'.join(dis(checked.A,checked.A['body'][i])) for i in [4]+list(ids.values())),encoding='utf8');ts[ix]=(82,b[:pos]+patched,tag(82,b[:pos]+patched))
 assert hits==1
 s=bytearray(swf[:start]+b''.join(r for _,_,r in ts));struct.pack_into('<I',s,4,len(s));gfx=b'CFX'+s[3:8]+zlib.compress(s[8:],9);target=R/'TileList.big';target.write_bytes(raw);bigdir.patch(target,{member:gfx});assert bigdir.read(target,member)==gfx
 report=dict(status='BUILD_PASS',client_before=sha(raw),client_after=sha(target.read_bytes()),server_before=sha((S/'product_packs.py').read_bytes()),methods=ids,all_other_methods_including_completion_identical=True,native_button_class='ShopBuyButton',event_namespace='scaleform.clik.events.ButtonEvent.CLICK',native_verified=False)
 (R/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':build()
