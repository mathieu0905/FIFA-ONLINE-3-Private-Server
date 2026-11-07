from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path[:0]=[str(T),r'D:\FO3ID\server\tools\re']
from avm_patch import ABC,Code,dis,instructions
import bigdir
ns={};f=T.parents[1]/'work/grade_render_audit/build_display_fix.py';exec(f.read_text(encoding='utf-8').split("source=OLD/'TileList.big'")[0],ns)
NAME='fo3EnhanceProbability'

def render(a,base,container,preview,waiting=False,popup=False):
 c=Code(a)
 if popup:
  c.local(0).ownprop('boostInfoPanel').store(base)
  c.local(base).jump(0x12,'done')
  c.local(base).prop('boostInfoContainer').store(base)
  c.local(base).jump(0x12,'done')
  c.local(base).prop('boostRate').store(base)
 else:
  # This is the native success-rate bonus section, not the fee panel.
  c.local(0).ownprop('_owner').store(base)
  c.local(base).jump(0x12,'done')
  c.local(base).prop('infoPanel').store(base)
  c.local(base).jump(0x12,'done')
  c.local(base).prop('enhanceRate').store(base)
 c.local(base).jump(0x12,'done')
 # Reuse the original localized title and its existing CJK glyphs.
 c.local(base).string('__id15_' if popup else '__id7_').call('getChildByName',1).store(base+5)
 c.local(base+5).jump(0x12,'title_done')
 c.local(base+5).string('成功率').set('text')
 c.label('title_done')
 if popup:
  c.local(base).prop('rateContainer').store(base+5)
  c.local(base+5).jump(0x12,'done')
  c.local(base+5).op(0x27).set('visible')
 preview(c);c.store(base+1)
 c.local(base).string(NAME).call('getChildByName',1).op(0x80,a.name('TextField','flash.text')).store(base+2)
 c.local(base+2).jump(0x11,'have_field')
 c.op(0x5d,a.name('TextField','flash.text')).op(0x4a,a.name('TextField','flash.text'),0).store(base+2)
 c.local(base+2).string(NAME).set('name')
 for key in ('selectable','embedFonts','mouseEnabled','multiline','wordWrap'):c.local(base+2).op(0x27).set(key)
 c.op(0x5d,a.name('TextFormat','flash.text')).string('Arial').number(40 if popup else 24).number(0xf2c200).op(0x4a,a.name('TextFormat','flash.text'),3).store(base+5 if not popup else base+4)
 fmt=base+4 if popup else base+5
 c.local(fmt).string('center').set('align')
 c.local(base+2).local(fmt).set('defaultTextFormat')
 for key in ('border','background'):c.local(base+2).op(0x26).set(key)
 c.local(base+2).number(0x627580).set('borderColor')
 c.local(base+2).number(0x17232b).set('backgroundColor')
 c.local(base).local(base+2).call('addChild',1).op(0x29)
 c.label('have_field')
 if popup:
  c.local(base+2).local(base+5).prop('x').set('x')
  c.local(base+2).local(base+5).prop('y').number(15).op(0xa0).set('y')
  c.local(base+2).local(base+5).prop('width').set('width')
  c.local(base+2).number(70).set('height')
 else:
  for key,value in [('x',0),('y',36),('width',180),('height',40)]:c.local(base+2).number(value).set(key)
 c.string('...' if waiting else '-').store(base+3)
 c.local(base+1).jump(0x12,'set_text')
 c.local(base+1).prop('probability').store(base+4)
 c.local(base+4).op(0x95).string('number').jump(0x14,'set_text')
 c.op(0x5d,a.name('isFinite')).local(base+4).call('isFinite',1).jump(0x12,'set_text')
 c.local(base+4).number(0).op(0xad).jump(0x11,'set_text')
 c.local(base+4).number(100).op(0xaf).jump(0x11,'set_text')
 c.local(base+4).call('toString',0).string('%').op(0xa0).store(base+3)
 c.label('set_text').local(base+2).local(base+3).set('text')
 c.local(base+2).op(0x26).set('visible')
 c.label('done');return c.done()

def control_patch(a):
 points={32:7,35:119,18:7,25:7}
 for mid,offset in points.items():
  row=json.loads((Path(r'D:\fifaol3\enhancement-probability-ui')/'TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())[str(mid)]
  assert a.A['body'][mid]==bytes.fromhex(row['updated'])
  a.A['body'][mid]=bytes.fromhex(row['original'])
  base=a.A['body_records'][mid]['fields'][1]
  code=render(a,base,lambda c:c.local(0).ownprop('textContainer'),lambda c:c.op(0x20) if mid in (18,35,25) else c.local(0).ownprop('_preview'),waiting=mid==35)
  a.modify(mid,{offset:code},locals_extra=6)
 return points

def popup_patch(a):
 mid=25;row=json.loads((Path(r'D:\fifaol3\enhancement-probability-ui')/'TeamManagementPlayerEnhancingPopupScreen-ABC.patch.json').read_text())[str(mid)];assert a.A['body'][mid]==bytes.fromhex(row['updated']);a.A['body'][mid]=bytes.fromhex(row['original']);offset=len(a.A['body'][mid])-1;assert a.A['body'][mid][offset]==0x47;base=a.A['body_records'][mid]['fields'][1]
 c=Code(a);c.local(1).jump(0x12,'skip')
 c.local(1).prop('cmd').string('setData').jump(0x14,'skip')
 c.raw(render(a,base,lambda c:c.local(0).owncall('getEnhanceCautionLabel',0),lambda c:c.local(1).prop('info'),popup=True))
 c.label('skip');a.modify(mid,{offset:c.done()},locals_extra=6);return {mid:offset}

reports={}
for name,offset,patcher in [('TeamManagementPlayerEnhancementTabPage',0x246ff,control_patch),('TeamManagementPlayerEnhancingPopupScreen',0x929ae,popup_patch)]:
 source=W/(name+'-baseline.big');member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'));d=(W/(name+'-baseline.swf')).read_bytes();start=8+(5+4*(d[8]>>3)+7)//8+4;parts=[];found=False;details={}
 for kind,body,raw in ns['tags'](d,start,len(d)):
  if kind==82:
   head=body.index(b'\0',4)+1
   if d.find(body)+head==offset:
    assert not found;found=True;a=ABC(body[head:]);points=patcher(a);updated=a.output();b=ABC(updated)
    assert a.A['cls']==b.A['cls'] and a.A['sig']==b.A['sig'] and a.A['meth']==b.A['meth']
    for mid,row in a.A['body_records'].items():
     assert row['suffix']==b.A['body_records'][mid]['suffix']
     if mid not in a.changed:assert row['raw']==b.A['body_records'][mid]['raw']
    raw=ns['tag'](kind,body[:head]+updated)
    (W/(name+'-before.abc')).write_bytes(body[head:]);(W/(name+'-after.abc')).write_bytes(updated)
    (W/(name+'-ABC.patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf-8')
    for mid in a.changed:details[str(mid)]='\n'.join(dis(b.A,b.A['body'][mid]))
  parts.append(raw)
 assert found
 new=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new));gfx=b'CFX'+new[3:8]+zlib.compress(new[8:],9);target=W/(name+'.big');ns['pack_archive'](source,target,{member:gfx},[])
 assert zlib.decompress(bigdir.read(target,member)[8:])==new[8:]
 (W/(name+'.swf')).write_bytes(new);(W/(name+'-changes.txt')).write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
 oldtags=list(ns['tags'](d,start,len(d)));newtags=list(ns['tags'](bytes(new),start,len(new)))
 assert len(oldtags)==len(newtags) and sum(x[2]!=y[2] for x,y in zip(oldtags,newtags))==1
 assert all(x[2]==y[2] for x,y in zip(oldtags,newtags) if x[0]!=82)
 oraw=source.read_bytes();nraw=target.read_bytes();entries=bigdir.entries(target)
 for n,o,size,u in bigdir.entries(source):
  if n==member:continue
  _,no,nsz,nu=next(e for e in entries if e[0]==n);assert (size,u)==(nsz,nu) and oraw[o:o+size]==nraw[no:no+nsz]
 reports[name]=dict(source_sha256=hashlib.sha256(oraw).hexdigest(),sha256=hashlib.sha256(nraw).hexdigest(),methods=points,all_other_methods_and_traits_identical=True,other_swf_tags_and_archive_members_identical=True,native_verified=False)
(W/'build.json').write_text(json.dumps(reports,indent=2),encoding='utf-8');print(json.dumps(reports,indent=2))
