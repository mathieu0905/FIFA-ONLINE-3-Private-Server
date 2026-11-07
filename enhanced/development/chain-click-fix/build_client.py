"""Give the visible native chain action a real mouse hit surface."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));from avm_patch import ABC,Code,dis
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags,tag
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');SOURCE=C/'data/ui/components/TileList.big'
sha=lambda b:hashlib.sha256(b).hexdigest()
def build():
 raw=SOURCE.read_bytes();member=next(n for n,*_ in bigdir.entries(SOURCE) if n.endswith('.gfx'));g=bigdir.read(SOURCE,member);swf=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4;ts=list(tags(swf,start,len(swf)));hits=0
 for ix,(t,b,r) in enumerate(ts):
  if t!=82:continue
  p=b.index(b'\0',4)+1;a=ABC(b[p:]);cls=a.A['cls'][0] if a.A['cls'] else None
  if not cls or cls[0]!='ShopChainedListItemRenderer' or not any(x[1]=='_chainRoundState' for x in cls[3]):continue
  hits+=1;state=a.name('_chainRoundState');end=len(a.A['body'][4])-1;assert a.A['body'][4][end:]==b'\x47'
  def label(c):return c.local(0).ownprop('countLabel')
  def st(c):return c.local(0).op(0x66,state)
  c=Code(a).local(1).jump(0x12,'done');label(c).call('validateNow',0).op(0x29)
  label(c).prop('graphics').call('clear',0).op(0x29)
  c.local(1).prop('round_buy_supported').jump(0x12,'ordinary')
  label(c).op(0x27).set('mouseChildren');label(c).op(0x20).set('hitArea')
  label(c).op(0x26).set('buttonMode');label(c).op(0x26).set('useHandCursor')
  label(c).prop('graphics').number(0xd8b452).number(18).number(100).op(0xa3).call('beginFill',2).op(0x29)
  label(c).prop('graphics')
  for n in (0,0,190,27):c.number(n)
  c.call('drawRect',4).op(0x29);label(c).prop('graphics').call('endFill',0).op(0x29)
  st(c).prop('pressBound').jump(0x11,'bound')
  label(c).string('mouseDown').op(0x40,11).call('addEventListener',2).op(0x29);st(c).op(0x26).set('pressBound')
  c.label('bound');c.local(1).prop('round_buy_enabled').jump(0x12,'disabled');st(c).prop('busy').jump(0x11,'disabled')
  label(c).op(0x26).set('mouseEnabled');label(c).number(1).set('alpha');c.jump(0x10,'done')
  c.label('disabled');label(c).op(0x27).set('mouseEnabled');label(c).number(6).number(10).op(0xa3).set('alpha');c.jump(0x10,'done')
  c.label('ordinary');label(c).op(0x27).set('mouseEnabled');label(c).op(0x27).set('buttonMode')
  c.label('done');insertion=c.done();a.modify(4,{end:insertion});updated=ABC(a.output())
  for mid,code in a.A['body'].items():
   if mid!=4:assert updated.A['body'][mid]==code
  (R/'list.updated.abc').write_bytes(a.output());(R/'list-patched.txt').write_text('\n'.join(dis(updated.A,updated.A['body'][4])),encoding='utf8')
  ts[ix]=(82,b[:p]+a.output(),tag(82,b[:p]+a.output()));insertion_start=a.insertions[4]['mapping'][end]
 assert hits==1
 s=bytearray(swf[:start]+b''.join(r for _,_,r in ts));struct.pack_into('<I',s,4,len(s));gfx=b'CFX'+s[3:8]+zlib.compress(s[8:],9);target=R/'TileList.big';target.write_bytes(raw);bigdir.patch(target,{member:gfx});assert bigdir.read(target,member)==gfx
 result=dict(status='BUILD_PASS',client_before=sha(raw),client_after=sha(target.read_bytes()),server_before=sha((S/'product_packs.py').read_bytes()),insertion_start=insertion_start,native_verified=False,all_other_methods_including_completion_and_purchase_callbacks_identical=True)
 (R/'build.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
if __name__=='__main__':build()
