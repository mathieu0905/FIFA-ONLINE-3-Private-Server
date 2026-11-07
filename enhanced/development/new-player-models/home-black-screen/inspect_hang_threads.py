"""Read AMD64 and saved WOW64 thread contexts from a captured minidump."""
import json,struct,sys
from minidump_read import Dump
d=Dump(sys.argv[1]);rva,_=d.streams[3];rows=[]
for i in range(struct.unpack_from('<I',d.data,rva)[0]):
    at=rva+4+i*48;tid=struct.unpack_from('<I',d.data,at)[0];teb=struct.unpack_from('<Q',d.data,at+16)[0];size,ctx=struct.unpack_from('<II',d.data,at+40)
    row=dict(tid=tid,teb=hex(teb),context_size=size,context_prefix=d.data[ctx:ctx+64].hex())
    if size>=256:
        row.update(rip=hex(struct.unpack_from('<Q',d.data,ctx+248)[0]),rsp=hex(struct.unpack_from('<Q',d.data,ctx+152)[0]))
    candidates=[]
    for base in [teb,teb-0x2000,teb+0x2000]:
        for tls in [0x1488]:
            try:
                ptr=struct.unpack('<Q',d.read(base+tls,8))[0]
                for extra in [0,4,16]:
                    c=ptr+extra;flags=d.u32(c)
                    if flags&0xffff0000==0x10000:
                        candidates.append(dict(address=hex(c),flags=hex(flags),ebp=hex(d.u32(c+180)),eip=hex(d.u32(c+184)),esp=hex(d.u32(c+196))))
            except (KeyError,struct.error):pass
    for candidate in candidates:
        chain=[];bp=int(candidate['ebp'],16)
        for step in range(40):
            try:
                next_,ret=struct.unpack('<II',d.read(bp,8));chain.append(dict(bp=hex(bp),ret=hex(ret)))
                if next_<=bp or next_-bp>0x100000:break
                bp=next_
            except KeyError:break
        candidate['chain']=chain
        try:
            esp=int(candidate['esp'],16);words=struct.unpack('<1024I',d.read(esp,4096))
            candidate['game_stack_candidates']=[dict(at=hex(esp+j*4),value=hex(v)) for j,v in enumerate(words) if 0x400000<=v<0x2146000][:80]
        except KeyError:pass
    row['wow64']=candidates;rows.append(row)
print(json.dumps(rows[:1],indent=2))
d.path.with_suffix('.threads.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
