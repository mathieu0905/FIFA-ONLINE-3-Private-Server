"""Render captions through the existing localized label; keep purchase handlers unchanged."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));import avm_patch as avm
from avm_patch import ABC,Code,u30,dis,instructions
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags,tag
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');SRC=C/'data/ui/components/TileList.big';sha=lambda b:hashlib.sha256(b).hexdigest()
def add_trait(data,trait):
 src=avm.SOURCE.replace('ii = r.u30(); inst.append([name, sup, ii, traits()])',"ii = r.u30(); tp=r.p; tr=traits(); A.setdefault('instance_trait_offsets',[]).append((tp,r.p)); inst.append([name,sup,ii,tr])")
 ns={'__name__':'traits'};exec(compile(src,'traits','exec'),ns);p=ns['parse'](data,0);at,end=p['instance_trait_offsets'][0];r=avm.R(data,at);n=r.u30();entries=r.p;return data[:at]+u30(n+1)+data[entries:end]+trait+data[end:]
def build():
 raw=SRC.read_bytes();member=next(n for n,*_ in bigdir.entries(SRC) if n.endswith('.gfx'));g=bigdir.read(SRC,member);s=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(s[8]>>3)+7)//8+4;ts=list(tags(s,start,len(s)));hits=0
 for ix,(t,b,r) in enumerate(ts):
  if t!=82:continue
  p=b.index(b'\0',4)+1;a=ABC(b[p:]);cls=a.A['cls'][0] if a.A['cls'] else None
  if not cls or cls[0]!='ShopChainedListItemRenderer' or not any(x[1]=='roundPurchaseButton' for x in cls[3]):continue
  hits+=1;helper='_applyRoundCaption';helper_name=a.name(helper)
  def button(c):return c.local(0).ownprop('roundPurchaseButton')
  def label(c):return c.local(0).ownprop('countLabel')
  c=Code(a).local(0).op(0x30);button(c).jump(0x12,'done');label(c).jump(0x12,'done');button(c).prop('visible').jump(0x12,'done')
  for prop in ('x','y'):
   label(c);button(c).prop(prop);c.set(prop)
  for prop in ('scaleX','scaleY'):label(c).number(1).set(prop)
  for prop in ('width','height'):
   label(c);button(c).prop(prop);c.set(prop)
  label(c).number(15).set('fontSize');label(c).string('#F4F6FA').set('fontColor');label(c).string('center').set('align');label(c).op(0x27).set('multiline')
  button(c).prop('label').string('一键购买本轮').jump(0x14,'state_caption');label(c).string('购买本轮').set('text');c.jump(0x10,'render')
  c.label('state_caption');label(c);button(c).prop('label');c.set('text')
  c.label('render');label(c).op(0x26).set('visible');label(c).call('validateNow',0).op(0x29)
  # A display-only label above the native hit target; never intercept clicks.
  label(c).op(0x27).set('mouseEnabled');label(c).op(0x27).set('mouseChildren');label(c).op(0x27).set('buttonMode')
  c.local(0);label(c);c.call('addChild',1).op(0x29)
  button(c).prop('textField').jump(0x12,'done');button(c).prop('textField').op(0x27).set('visible')
  c.label('done').op(0x47);mid=a.add_method(c.done(),a.A['body_records'][4]['fields'][2],2)
  call=Code(a).local(0).op(0x20).op(0x46,helper_name,1).op(0x29).done();patched_methods={}
  for method in (4,17,18,19,20,21):
   code=a.A['body'][method];insertions={}
   for at,end,op,targets in instructions(code):
    if op!=0x46:continue
    reader=avm.R(code,at+1);name=reader.u30();argc=reader.u30()
    if a.A['mn'][name]=='validateNow' and argc==0:
     assert code[end]==0x29;insertions[end+1]=call
   assert insertions;patched_methods[method]=len(insertions);a.modify(method,insertions)
  out=add_trait(a.output(),u30(helper_name)+b'\x01'+u30(0)+u30(mid));checked=ABC(out)
  assert ('method',helper,mid) in checked.A['cls'][0][3]
  for method,code in a.A['body'].items():
   if method not in patched_methods:assert checked.A['body'][method]==code
  # Each existing method changes solely through calls to the caption renderer.
  (R/'insertions.json').write_text(json.dumps(a.insertions,indent=2),encoding='utf8');(R/'list.updated.abc').write_bytes(out)
  (R/'caption.txt').write_text('\n'.join(dis(checked.A,checked.A['body'][mid])),encoding='utf8');ts[ix]=(82,b[:p]+out,tag(82,b[:p]+out))
 assert hits==1
 out=bytearray(s[:start]+b''.join(rr for _,_,rr in ts));struct.pack_into('<I',out,4,len(out));packed=b'CFX'+out[3:8]+zlib.compress(out[8:],9);target=R/'TileList.big';target.write_bytes(raw);bigdir.patch(target,{member:packed});assert bigdir.read(target,member)==packed
 report=dict(status='BUILD_PASS',client_before=sha(raw),client_after=sha(target.read_bytes()),server_before=sha((S/'product_packs.py').read_bytes()),caption_method=mid,caption_calls=patched_methods,purchase_code_only_caption_calls_added=True,native_button_skin_and_timeline_unchanged=True,caption='购买本轮',native_verified=False)
 (R/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':build()
