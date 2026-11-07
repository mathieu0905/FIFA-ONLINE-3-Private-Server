from pathlib import Path
import sys,struct,zlib
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));from avm_patch import ABC,dis
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
R=Path(__file__).resolve().parent
for n,rel in [('Buttons','data/ui/components/Button.big'),('Tiles','data/ui/components/TileList.big')]:
 p=Path(r'D:\FO3ID\32795')/rel;g=bigdir.read(p,next(n for n,*_ in bigdir.entries(p) if n.endswith('.gfx')));s=b'FWS'+g[3:8]+zlib.decompress(g[8:]);(R/(n+'.swf')).write_bytes(s);start=8+(5+4*(s[8]>>3)+7)//8+4
 for t,b,_ in tags(s,start,len(s)):
  if t!=82:continue
  pos=b.index(b'\0',4)+1;a=ABC(b[pos:]);cls=a.A['cls'][0] if a.A['cls'] else None
  if not cls:continue
  if n=='Buttons' and cls[0] in ('ShopBuyButton','ButtonEx','ButtonEvent','Button'):
   (R/(cls[0]+'.abc')).write_bytes(b[pos:]);(R/(cls[0]+'.txt')).write_text(str(cls)+'\n'+'\n\n'.join('method '+str(i)+'\n'+'\n'.join(dis(a.A,code)) for i,code in a.A['body'].items()),encoding='utf8');print(cls[0],cls[1],cls[3][:12])
  if n=='Tiles' and cls[0]=='ShopChainedTileItemRenderer' and any(x[1]=='randomContainer' for x in cls[3]):
   print('Native events NS',[(name,a.A['mnns'][i]) for i,name in enumerate(a.A['mn']) if name in ('ButtonEvent','CLICK','ButtonEx')]);print('Native listener','\n'.join(dis(a.A,a.A['body'][5])))
