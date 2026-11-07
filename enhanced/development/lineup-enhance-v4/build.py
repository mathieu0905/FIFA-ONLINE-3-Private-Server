"""Correct AVM2 back-edge labels; use one untouched native button skin."""
from pathlib import Path
import sys,json,struct,zlib,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,Code,u30,instructions,tags,tag,pack_archive,bigdir
W=Path(__file__).resolve().parent;C=Path(r'D:\FO3ID\32795');V3=W.parent/'lineup-enhance-v3'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report={}
for key,rel,ordinal,mid in [('components-ScrollingList','components/ScrollingList',3451,43),('TeamManagementScreen','TeamManagementScreen',29,20)]:
 source=C/'data/ui'/(rel+'.big');(W/(key+'-baseline.big')).write_bytes(source.read_bytes())
 member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'));gfx=bigdir.read(source,member);swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4
 parts=[];meta={}
 for i,(kind,body,raw) in enumerate(tags(swf,start,len(swf))):
  if i==ordinal:
   assert kind==82;head=body.index(b'\0',4)+1;before=body[head:];a=ABC(before);old=ABC(before);prefix=f'{key}-{i}'
   assert before==(V3/(prefix+'-after.abc')).read_bytes(),'Preserve later legitimate ABC changes'
   if key=='TeamManagementScreen':
    code=a.A['body'][mid];targets={t for at,end,op,ts in instructions(code) for t in(ts or []) if t<=at and code[t]!=9};assert targets=={194,300}
    a.modify(mid,{t:b'\x09' for t in targets});meta=dict(back_edge_targets_before=sorted(targets),fix='explicit AVM2 label 0x09')
   else:
    c=Code(a).local(0).op(0x30).local(0).string('fo3LineupEnhanceV3').call('getChildByName',1).store(2);c.local(2).jump(0x11,'done')
    c.op(0x5d,a.name('getDefinitionByName','flash.utils')).string('PlayerSwapButton').op(0x46,a.name('getDefinitionByName','flash.utils'),1).op(0x42,0).store(2)
    for n,emit in [('name',lambda c:c.string('fo3LineupEnhanceV3')),('focusable',lambda c:c.op(0x27)),('visible',lambda c:c.op(0x27)),('toggle',lambda c:c.op(0x27)),('autoSize',lambda c:c.string('none')),('label',lambda c:c.string(''))]:c.local(2);emit(c);c.set(n)
    c.local(2).lex('ButtonEvent',a.A['mnns'][a.own('ButtonEvent')]).prop('CLICK').local(0).prop('fo3LineupClickV3').call('addEventListener',2).op(0x29)
    c.local(0).local(2).call('addChild',1).op(0x29).label('done').op(0x47)
    code=c.done();rec=a.A['body_records'][mid];a.changed[mid]=u30(mid)+b''.join(u30(n) for n in rec['fields'])+u30(len(code))+code+rec['suffix']
    meta=dict(native_skin='PlayerSwapButton',natural_dimensions=True,custom_graphics=False,compound_clip_resizing=False)
   data=a.output();new=ABC(data)
   for index,rec in old.A['body_records'].items():
    if index!=mid:assert rec['raw']==new.A['body_records'][index]['raw']
   assert old.A['cls']==new.A['cls'] and old.A['sig']==new.A['sig']
   for index,code in new.A['body'].items():
    assert all(code[t]==9 for at,end,op,ts in instructions(code) for t in(ts or []) if t<=at),('Non-label back edge',prefix,index)
   (W/(prefix+'-before.abc')).write_bytes(before);(W/(prefix+'-after.abc')).write_bytes(data);raw=tag(kind,body[:head]+data)
  parts.append(raw)
 out=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',out,4,len(out));target=W/(key+'.big');pack_archive(source,target,{member:b'CFX'+out[3:8]+zlib.compress(out[8:],9)},[])
 assert all(x[2]==y[2] for x,y in zip(tags(swf,start,len(swf)),tags(out,start,len(out))) if x[0]!=82)
 for n,*_ in bigdir.entries(source):
  if n!=member:assert bigdir.read(source,n)==bigdir.read(target,n)
 report[key]=dict(source_sha256=sha(source),sha256=sha(target),method=mid,prefix=prefix,metadata=meta,other_methods_traits_members_preserved=True)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
