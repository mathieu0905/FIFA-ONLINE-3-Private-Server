from pathlib import Path
import sys,zlib,json,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,'D:/fifaol3/enhancement-entry-fix')
from client_tools import ABC,tags,bigdir,dis
W=Path(__file__).resolve().parent
C=Path('D:/FO3ID/32795/data/ui')
for name in ('libs/Module',):
 p=C/(name+'.big');out=[];found=[]
 for member,*_ in bigdir.entries(p):
  if not member.endswith('.gfx'):continue
  gfx=bigdir.read(p,member);swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4
  for kind,body,raw in tags(swf,start,len(swf)):
   if kind!=82:continue
   head=body.index(b'\0',4)+1;a=ABC(body[head:]);A=a.A
   classes=[r for r in A['cls'] if any(s in r[0].lower() for s in ('offer','transfermarket'))]
   if not classes:continue
   found.extend(r[0] for r in classes)
   for row in classes:
    out.append(repr(row));out.append('CINIT '+str(row[4])+'\\n'+'\\n'.join(dis(A,A['body'][row[4]])))
    for k,n,mid in row[3]+row[5]:
     if k in ('method','get','set') and mid in A['body']:
      out.append('METHOD '+str(mid)+' '+n+'\n'+'\n'.join(dis(A,A['body'][mid])))
   # callbacks/anonymous methods involving relist URI or handlers
   for mid,code in A['body'].items():
    lines=dis(A,code);txt='\n'.join(lines)
    if 'reregistrerButton' in txt or '/transfer/offer/from/' in txt or ('recreate' in txt.lower()):out.append('CALLBACK '+str(mid)+'\n'+txt)
 (W/(name.replace('/','-')+'-analysis.txt')).write_text('\n\n'.join(out),'utf8')
 print(name,hashlib.sha256(p.read_bytes()).hexdigest(),found)




