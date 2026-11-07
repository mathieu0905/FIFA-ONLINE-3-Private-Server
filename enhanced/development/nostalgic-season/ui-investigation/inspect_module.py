from pathlib import Path
import sys,zlib,struct,json,hashlib,sqlite3
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path[:0]=[str(W/'work/experience_levels'),r'D:/FO3ID/server/tools/re']
from avm_patch import ABC,dis
import bigdir
def tags(data,pos):
 while pos+2<=len(data):
  start=pos;h=struct.unpack_from('<H',data,pos)[0];pos+=2;kind,size=h>>6,h&63
  if size==63:size=struct.unpack_from('<I',data,pos)[0];pos+=4
  yield kind,data[pos:pos+size],start;pos+=size
  if kind==0:break
result={};inventory=[];hashes={}
for path in [Path(r'D:/FO3ID/32795/data/ui/libs/Module.big'),Path(r'D:/FO3ID/32795/data/ui/components/Label.big')]:
 hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
 member=next(n for n,*_ in bigdir.entries(path) if n.endswith('.gfx'))
 gfx=bigdir.read(path,member);plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4
 for kind,body,offset in tags(plain,start):
  if kind!=82:continue
  pos=body.index(b'\0',4)+1
  a=ABC(body[pos:])
  for cls,sup,ii,it,ci,ct in a.A['cls']:
   if any(s in cls.lower() for s in ('season','playerlistutil','playercard','seasonplate')):
    methods={name:mid for k,name,mid in it+ct if k in ('method','get','set')}
    inventory.append(dict(file=path.name,cls=cls,offset=offset,methods=methods))
    for name,mid in methods.items():
     if cls!='PlayerListUtil' or any(x in name.lower() for x in ('season','card','frame')):
      result[f'{path.name}:{cls}.{name} ({mid})']='\n'.join(dis(a.A,a.A['body'][mid])) if mid in a.A['body'] else ''
(ROOT/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),'utf-8')
(ROOT/'methods.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
(ROOT/'methods.txt').write_text('\n\n'.join(k+'\n'+v for k,v in result.items()),'utf-8')
(ROOT/'hashes.json').write_text(json.dumps(hashes,indent=2),'utf-8')
print(json.dumps(inventory,ensure_ascii=True,indent=2))
