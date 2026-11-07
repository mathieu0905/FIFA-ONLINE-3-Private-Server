"""Extend the previously verified native draft search ID range for +8 choice SKUs."""
from pathlib import Path
import hashlib,json,struct,sys,zlib
R=Path(__file__).resolve().parent
sys.path.insert(0,r'D:\FO3ID\server\tools\re')
sys.path.insert(0,r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
import bigdir
from avm_patch import ABC,R as Reader,u30,instructions
src=Path(r'D:\FO3ID\32795\data\ui\TeamManagementDraftPackScreen.big')
member=next(n for n,*_ in bigdir.entries(src) if n.endswith('.gfx'));gfx=bigdir.read(src,member)
d=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);pos=8+(5+4*(d[8]>>3)+7)//8+4;parts=[d[:pos]];changes=[]
while pos+2<=len(d):
    start=pos;v=struct.unpack_from('<H',d,pos)[0];pos+=2;t,n=v>>6,v&63
    if n==63:n=struct.unpack_from('<I',d,pos)[0];pos+=4
    body=d[pos:pos+n];pos+=n
    if t==82:
        off=body.index(b'\0',4)+1;abc=body[off:];a=ABC(abc)
        if any(c[0]=='TeamManagementDraftPackScreen' for c in a.A['cls']):
            reader=Reader(abc,4);count=reader.u30();hits=[]
            for i in range(1,count):
                at=reader.p;value=reader.u30()
                if value==97300000:hits.append((i,at,reader.p))
            assert len(hits)==1;index,at,end=hits[0]
            refs=[]
            for mi,code in a.A['body'].items():
                for p,q,op,targets in instructions(code):
                    if op==0x2d and Reader(code,p+1).u30()==index:refs.append(mi)
            assert refs==[50],refs
            new=u30(97700000);assert len(new)==end-at
            updated=abc[:at]+new+abc[end:];b=ABC(updated)
            assert b.A['body']==a.A['body']
            body=body[:off]+updated;changes.append(dict(method=50,old_upper_bound=97300000,new_upper_bound=97700000,method_bytes_identical=True))
            parts.append(struct.pack('<HI',(82<<6)|63,len(body))+body);continue
    parts.append(d[start:pos])
assert len(changes)==1
swf=b''.join(parts);assert len(swf)==len(d)
newgfx=b'CFX'+gfx[3:8]+zlib.compress(swf[8:],9)
target=R/src.name;target.write_bytes(src.read_bytes());bigdir.patch(target,{member:newgfx})
assert bigdir.read(target,member)==newgfx
report=dict(status='PASS',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),target_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),changes=changes)
(R/'native-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
