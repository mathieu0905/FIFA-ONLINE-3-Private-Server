"""Repair chain UI using native label controls and explicit completion text."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));import avm_patch as avm
from avm_patch import ABC,Code,u30,dis
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags,tag
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');SOURCE=C/'data/ui/components/TileList.big'
def sha(b):return hashlib.sha256(b).hexdigest()
def body(a,mid,code):
 record=a.A['body_records'][mid];fields=list(record['fields']);fields[0]=max(fields[0],32)
 a.changed[mid]=u30(mid)+b''.join(u30(x) for x in fields)+u30(len(code))+code+record['suffix']
def build():
 raw=SOURCE.read_bytes();member=next(n for n,*_ in bigdir.entries(SOURCE) if n.endswith('.gfx'));g=bigdir.read(SOURCE,member);swf=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4;ts=list(tags(swf,start,len(swf)));reports=[]
 for ix,(t,b,r) in enumerate(ts):
  if t!=82:continue
  pos=b.index(b'\0',4)+1;a=ABC(b[pos:]);cls=a.A['cls'][0] if a.A['cls'] else None
  if not cls:continue
  if cls[0]=='ShopChainedListItemRenderer' and any(x[1]=='_chainRoundState' for x in cls[3]):
   state=a.name('_chainRoundState');prefix=a.A['body'][4][:206];assert prefix[-1]==0x29
   def st(c):return c.local(0).op(0x66,state)
   def label(c):return c.local(0).ownprop('countLabel')
   c=Code(a).local(1).jump(0x12,'done')
   st(c).jump(0x11,'exists')
   c.local(0).string('busy').op(0x27).string('quote').op(0x20).string('purchasePending').op(0x27).string('button');label(c);c.op(0x55,4).op(0x61,state)
   label(c).string('click').op(0x40,11).call('addEventListener',2).op(0x29)
   c.label('exists');st(c);label(c);c.set('button')
   c.local(1).prop('round_buy_supported').jump(0x12,'ordinary')
   label(c).number(1).set('scaleX');label(c).number(1).set('scaleY')
   label(c).number(190).set('width');label(c).number(27).set('height')
   label(c).string('center').set('align');label(c).number(16).set('fontSize');label(c).string('#e8c571').set('fontColor')
   label(c).op(0x26).set('visible');label(c).op(0x26).set('buttonMode')
   c.local(1).prop('round_buy_enabled').jump(0x12,'disabled');st(c).prop('busy').jump(0x11,'disabled')
   label(c).op(0x26).set('mouseEnabled');label(c).number(1).set('alpha');c.jump(0x10,'caption')
   c.label('disabled');label(c).op(0x27).set('mouseEnabled');label(c).number(6).number(10).op(0xa3).set('alpha')
   c.label('caption');st(c).prop('purchasePending').jump(0x12,'normal');label(c).string('重试本轮购买').set('text');c.jump(0x10,'done')
   c.label('normal');label(c).string('【一键购买本轮】').set('text');c.jump(0x10,'done')
   c.label('ordinary');label(c).op(0x27).set('mouseEnabled');label(c).op(0x27).set('buttonMode');label(c).number(1).set('alpha')
   c.label('done').op(0x47);new=prefix+c.done();body(a,4,new)
   # Existing quote, confirmation, cancellation and idempotent retry code is retained.
   old=Code(a).op(0x5d,state).op(0x66,state).prop('button').string('caption').call('getChildByName',1).done()
   replacement=Code(a).op(0x5d,state).op(0x66,state).prop('button').done();counts={}
   for mid in range(7,12):
    code=a.A['body'][mid];count=code.count(old);counts[mid]=count
    if count:body(a,mid,code.replace(old,replacement+b'\x02'*(len(old)-len(replacement))))
   assert sum(counts.values())>=3
   checked=ABC(a.output());(R/'list.updated.abc').write_bytes(a.output())
   reports.append(dict(renderer=cls[0],methods=[4]+[i for i,n in counts.items() if n],insertion=206,caption_replacements=counts))
  elif cls[0]=='ShopChainedTileItemRenderer' and any(x[1]=='randomContainer' for x in cls[3]):
   c=Code(a);c.local(0).prop('usingIcon').jump(0x12,'done')
   c.local(1).prop('currentstep').string('complete').jump(0x14,'not_complete')
   for key,val in [('text','购买完成'),('fontColor','#7ee7ac'),('align','center')]:c.local(0).prop('usingIcon').string(val).set(key)
   for key,val in [('scaleX',1),('scaleY',1),('x',30),('y',162),('width',160),('height',27),('fontSize',16)]:c.local(0).prop('usingIcon').number(val).set(key)
   c.local(0).prop('usingIcon').op(0x26).set('visible');c.local(0).prop('usingIcon').op(0x27).set('mouseEnabled')
   c.local(0).local(0).prop('usingIcon').call('addChild',1).op(0x29)
   c.local(0).prop('buyButton').jump(0x12,'done');c.local(0).prop('buyButton').op(0x27).set('visible');c.jump(0x10,'done')
   c.label('not_complete').local(0).prop('usingIcon').op(0x27).set('visible')
   c.label('done');insertion=c.done();original=a.A['body'][12];assert original[1829:]==b'\x47';body(a,12,original[:1829]+insertion+original[1829:]);checked=ABC(a.output());(R/'tile.updated.abc').write_bytes(a.output())
   reports.append(dict(renderer=cls[0],methods=[12],insertion=1829))
  else:continue
  for mid,code in a.A['body'].items():
   if mid not in a.changed:assert checked.A['body'][mid]==code
  (R/(cls[0]+'-patched.txt')).write_text('\n\n'.join('method '+str(mid)+'\n'+'\n'.join(dis(checked.A,checked.A['body'][mid])) for mid in a.changed),encoding='utf8')
  ts[ix]=(82,b[:pos]+a.output(),tag(82,b[:pos]+a.output()))
 assert len(reports)==2
 updated=bytearray(swf[:start]+b''.join(r for _,_,r in ts));struct.pack_into('<I',updated,4,len(updated));gfx=b'CFX'+updated[3:8]+zlib.compress(updated[8:],9);target=R/'TileList.big';target.write_bytes(raw);bigdir.patch(target,{member:gfx});assert bigdir.read(target,member)==gfx
 for n,o,size,usize in bigdir.entries(SOURCE):
  if n!=member:
   _,o2,size2,usize2=next(e for e in bigdir.entries(target) if e[0]==n);assert(size,usize)==(size2,usize2) and raw[o:o+size]==target.read_bytes()[o2:o2+size2]
 source=(S/'product_packs.py').read_bytes();needle=b"part.update(index=index+1,maxCount=len(t['steps']),limitcountperaccount=1,";assert source.count(needle)==1
 server=source.replace(needle,b"part.update(chained=True,index=index+1,maxCount=len(t['steps']),limitcountperaccount=1,")
 (R/'product_packs.py').write_bytes(server)
 result=dict(status='BUILD_PASS',client_before=sha(raw),client_after=sha(target.read_bytes()),server_before=sha(source),server_after=sha(server),reports=reports,native_verified=False,non_target_methods_identical=True,non_code_swf_tags_identical=True)
 (R/'build.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
if __name__=='__main__':build()


