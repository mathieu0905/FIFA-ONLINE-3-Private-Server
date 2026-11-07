"""Compact shared currency labels; the separate PriceInput parser is untouched."""
from pathlib import Path
import hashlib,json,shutil,struct,sys,zlib
sys.dont_write_bytecode=True
from build_compact_label import ABC,Code,tags,tag,double,parse,bigdir
R=Path(__file__).resolve().parent
O=R/'compact-module';(O/'payload').mkdir(parents=True,exist_ok=True)
source=Path('D:/FO3ID/32795/data/ui/libs/Module.big')
member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
gfx=bigdir.read(source,member);swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:])
parts=[];changes=[];first=None
for at,pos,end,kind in tags(swf):
    if first is None:first=at
    raw=swf[at:end]
    if kind==82:
        payload=swf[pos:end];off=payload.index(b'\0',4)+1;a=ABC(payload[off:])
        for cls in a.A['cls']:
            if cls[0]!='StringUtil':continue
            mid=next(i for k,n,i in cls[5] if k=='method' and n=='formatToCurrency')
            original=a.A['body'][mid]
            assert original[:2]==b'\xd0\x30'
            c=Code(a).lex('Math').local(1).call('abs',1).store(4)
            for i,(base,unit) in enumerate(((10**16,'京'),(10**12,'兆'),(10**8,'亿'),(10**4,'万'))):
                c.local(4);double(c,base);c.jump(0x15,'next'+str(i))
                c.local(1).number(0).jump(0x15,'negative'+str(i))
                c.string('').jump(0x10,'magnitude'+str(i)).label('negative'+str(i)).string('-').label('magnitude'+str(i))
                c.lex('Math').local(4);double(c,base)
                c.op(0xa3).number(100).op(0xa2).call('floor',1).number(100).op(0xa3).call('toString',0)
                c.op(0xa0).string(unit).op(0xa0).op(0x48).label('next'+str(i))
            a.modify(mid,{2:c.done()},locals_extra=1)
            newabc=a.output();raw=tag(kind,payload[:off]+newabc)
            (O/'StringUtil.abc').write_bytes(newabc)
            changes.append(dict(class_name='StringUtil',method=mid,original_body=original.hex(),other_methods_identical=True))
    parts.append(raw)
assert len(changes)==1
out=bytearray(swf[:first]+b''.join(parts));struct.pack_into('<I',out,4,len(out))
target=O/'payload/Module.big';shutil.copyfile(source,target)
bigdir.patch(target,{member:b'CFX'+gfx[3:4]+struct.pack('<I',len(out))+zlib.compress(out[8:],9)})
assert zlib.decompress(bigdir.read(target,member)[8:])==out[8:]
old=source.read_bytes();new=target.read_bytes();updated={n:(o,s,u) for n,o,s,u in bigdir.entries(target)}
for n,o,s,u in bigdir.entries(source):
    if n==member:continue
    no,ns,nu=updated[n];assert old[o:o+s]==new[no:no+ns] and u==nu
(O/'Module.swf').write_bytes(out)
report=dict(status='BUILT_NATIVE_PENDING',source_sha256=hashlib.sha256(old).hexdigest(),sha256=hashlib.sha256(new).hexdigest(),
            changes=changes,other_archive_members_identical=True,price_input_untouched=True,XP_and_AI_methods_unchanged=True)
(O/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=2))
