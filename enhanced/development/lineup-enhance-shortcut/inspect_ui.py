from pathlib import Path
import sys,zlib,json,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,tags,bigdir,dis
W=Path(__file__).resolve().parent
C=Path(r'D:\FO3ID\32795')
names=['TeamManagementPlayerPoolTabPage','components/ScrollingList','components/Button','components/Tab','SquadAssets','TeamManagementStartingLineupTabPage','TeamManagementScreen','TeamManagementPlayerEnhancementTabPage','libs/Module']
report={}
for name in names:
 p=C/'data/ui'/(name+'.big');raw=p.read_bytes();key=name.replace('/','-')
 (W/(key+'-baseline.big')).write_bytes(raw)
 gfx=bigdir.read(p,next(n for n,*_ in bigdir.entries(p) if n.endswith('.gfx')))
 swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);(W/(key+'-baseline.swf')).write_bytes(swf)
 start=8+(5+4*(swf[8]>>3)+7)//8+4
 index=[]
 for ordinal,(kind,body,_) in enumerate(tags(swf,start,len(swf))):
  if kind!=82:continue
  head=body.index(b'\0',4)+1;a=ABC(body[head:]);classes=[r[0] for r in a.A['cls']];index+=classes
  wanted=[r for r in a.A['cls'] if (name!='libs/Module' or any(s.lower() in r[0].lower() for s in ('playerlist','enhance','lineup','screen','playercommand')))]
  if not wanted:continue
  prefix=f'{key}-{ordinal}';(W/(prefix+'.abc')).write_bytes(body[head:])
  lines=[]
  for row in wanted:
   lines.append(repr(row))
   for k,n,mid in row[3]+row[5]:
    if k in ('method','get','set') and mid in a.A['body']:
     lines.append(f'METHOD {mid} {n}\n'+'\n'.join(dis(a.A,a.A['body'][mid])))
  (W/(prefix+'.txt')).write_text('\n\n'.join(lines),encoding='utf8')
 report[name]={'sha256':hashlib.sha256(raw).hexdigest(),'classes':index}
(W/'inspection.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:len(v['classes']) for k,v in report.items()}))


