from pathlib import Path
import hashlib,json,sys,zlib
sys.dont_write_bytecode=True
from build_compact_label import ABC,bigdir,tags,dis
R=Path(__file__).resolve().parent;root=Path('D:/FO3ID/32795/data/ui');out=[];errors=[];scanned=0
for p in root.rglob('*.big'):
    try:
        names=[n for n,*_ in bigdir.entries(p) if n.endswith('.gfx')]
        for member in names:
            gfx=bigdir.read(p,member)
            if gfx[:3]!=b'CFX':continue
            d=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);scanned+=1
            if b'addComma' not in d:continue
            for at,pos,end,k in tags(d):
                if k!=82:continue
                payload=d[pos:end];off=payload.index(b'\0',4)+1
                if b'addComma' not in payload[off:]:continue
                a=ABC(payload[off:])
                for cls in a.A['cls']:
                    for kind,name,mi in cls[3]+cls[5]:
                        if name!='addComma' or mi not in a.A['body']:continue
                        out.append(dict(file=str(p),member=member,class_name=cls[0],method=mi,
                            source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),disassembly=dis(a.A,a.A['body'][mi])))
    except Exception as e:errors.append(dict(file=str(p),error=repr(e)))
report=dict(scanned_gfx=scanned,definitions=out,errors=errors)
(R/'native/comma-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(scanned_gfx=scanned,definitions=[(x['file'],x['class_name'],x['method']) for x in out],errors=errors),ensure_ascii=True,indent=2))
