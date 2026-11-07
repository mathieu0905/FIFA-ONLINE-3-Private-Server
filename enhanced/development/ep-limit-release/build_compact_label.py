"""Display-only PriceLabel patch; numeric getters and price inputs stay exact."""
from pathlib import Path
import hashlib,json,struct,sys,zlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
WORK=Path(r'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path.insert(0,str(WORK/'work/bp_client'))
sys.path.insert(0,'D:/FO3ID/server/tools/re')
from avm_patch import ABC,Code,parse,dis,u30
import bigdir

def tags(swf):
    start=8+(5+4*(swf[8]>>3)+7)//8+4
    pos=start
    while pos+2<=len(swf):
        at=pos;word=struct.unpack_from('<H',swf,pos)[0];pos+=2
        kind,size=word>>6,word&63
        if size==63:size=struct.unpack_from('<I',swf,pos)[0];pos+=4
        yield at,pos,pos+size,kind
        pos+=size

def tag(kind,payload):
    n=len(payload)
    return struct.pack('<H',kind<<6|min(63,n))+(struct.pack('<I',n) if n>=63 else b'')+payload

def double(c,value):
    raw=struct.pack('<d',value);vals=c.a.values[2]
    if raw not in vals:
        vals.append(raw);c.a.additions[2].append(raw)
    return c.op(0x2f,vals.index(raw))

def patch(a):
    cls=next(c for c in a.A['cls'] if c[0]=='PriceLabel' and c[1]=='HtmlLabel')
    mid=next(i for k,n,i in cls[3] if k=='set' and n=='value')
    old=a.A['body'][mid];record=a.A['body_records'][mid]
    assert record['exceptions']==0
    lines='\n'.join(dis(a.A,old))
    assert old[:2]==b'\xd0\x30' and '115: getlocal0' in lines and 'initproperty _value' in lines
    # Preserve assignment of the numeric _value and the original small-number,
    # sign, visibility and HtmlLabel update paths. Only _text is abbreviated.
    c=Code(a).raw(old[:15])
    c.lex('Math').local(1).call('abs',1).store(4)
    for index,(base,unit) in enumerate(((10**16,'京'),(10**12,'兆'),(10**8,'亿'),(10**4,'万'))):
        c.local(4);double(c,base);c.jump(0x15,'next'+str(index))
        c.find('_text').lex('Math').local(4);double(c,base)
        c.op(0xa3).number(100).op(0xa2).call('floor',1).number(100).op(0xa3).call('toString',0)
        c.string(unit).op(0xa0).op(0x68,a.own('_text')).jump(0x10,'render')
        c.label('next'+str(index))
    c.raw(old[15:115]).label('render').raw(old[115:])
    body=c.done();fields=list(record['fields']);fields[0]=max(8,fields[0]);fields[1]=max(5,fields[1])
    a.changed[mid]=u30(mid)+b''.join(u30(x) for x in fields)+u30(len(body))+body+record['suffix']
    return mid,old.hex()

if __name__=='__main__':
    source=Path('D:/FO3ID/32795/data/ui/components/Label.big')
    target=ROOT/'payload/Label.big';member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
    gfx=bigdir.read(source,member);swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:])
    parts=[];first=None;changes=[]
    for at,pos,end,kind in tags(swf):
        if first is None:first=at
        raw=swf[at:end]
        if kind==82:
            payload=swf[pos:end];off=payload.index(b'\0',4)+1;a=ABC(payload[off:])
            if any(c[0]=='PriceLabel' and c[1]=='HtmlLabel' for c in a.A['cls']):
                mid,original=patch(a);abc=a.output();check=parse(abc,0)
                raw=tag(kind,payload[:off]+abc)
                changes.append(dict(method=mid,original_body=original,
                                    updated_disassembly=dis(check,check['body'][mid]),
                                    all_other_methods_identical=True))
        parts.append(raw)
    assert len(changes)==1
    out=bytearray(swf[:first]+b''.join(parts));struct.pack_into('<I',out,4,len(out))
    import shutil
    shutil.copyfile(source,target)
    bigdir.patch(target,{member:b'CFX'+gfx[3:4]+struct.pack('<I',len(out))+zlib.compress(out[8:],9)})
    assert zlib.decompress(bigdir.read(target,member)[8:])==out[8:]
    old=source.read_bytes();new=target.read_bytes();updated={n:(o,s,u) for n,o,s,u in bigdir.entries(target)}
    for n,o,s,u in bigdir.entries(source):
        if n==member:continue
        no,ns,nu=updated[n];assert old[o:o+s]==new[no:no+ns] and u==nu
    (ROOT/'native/Label-compact.swf').write_bytes(out)
    report=dict(source=str(source),source_sha256=hashlib.sha256(old).hexdigest(),sha256=hashlib.sha256(new).hexdigest(),
                changes=changes,other_archive_members_identical=True,price_input_unchanged=True,numeric_value_getter_unchanged=True,
                precision='truncate to at most two decimal places; numeric values untouched',native_status='PENDING')
    (ROOT/'native/compact-label-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=2))
