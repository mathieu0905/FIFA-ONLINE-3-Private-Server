from pathlib import Path
import sys,zlib
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));from avm_patch import ABC,dis
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags
R=Path(__file__).resolve().parent
for name,rel in [('Scroll','data/ui/components/ScrollingList.big'),('Module','data/ui/libs/Module.big')]:
 p=Path(r'D:\FO3ID\32795')/rel;g=bigdir.read(p,next(n for n,*_ in bigdir.entries(p) if n.endswith('.gfx')));s=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(s[8]>>3)+7)//8+4
 for t,b,_ in tags(s,start,len(s)):
  if t!=82:continue
  pos=b.index(b'\0',4)+1;a=ABC(b[pos:]);cls=a.A['cls'][0] if a.A['cls'] else None
  if not cls or cls[0] not in ('ListItemRendererEx','ListItemRenderer','ResourceController','Pushable','NetEvent'):continue
  (R/(cls[0]+'.abc')).write_bytes(b[pos:]);(R/(cls[0]+'.txt')).write_text(str(cls)+'\n'+'\n\n'.join('method '+str(i)+'\n'+'\n'.join(dis(a.A,code)) for i,code in a.A['body'].items()),encoding='utf8');print(cls[0],cls[3][:22])
