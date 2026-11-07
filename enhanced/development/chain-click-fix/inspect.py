from pathlib import Path
import sys,struct,zlib
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));from avm_patch import ABC,dis
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
R=Path(__file__).resolve().parent
for name,rel in [('Module','data/ui/libs/Module.big'),('TileList','data/ui/components/TileList.big'),('Labels','data/ui/components/Label.big')]:
 p=Path(r'D:\FO3ID\32795')/rel;member=next(n for n,*_ in bigdir.entries(p) if n.endswith('.gfx'));g=bigdir.read(p,member);s=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(s[8]>>3)+7)//8+4
 for t,b,_ in tags(s,start,len(s)):
  if t!=82:continue
  pos=b.index(b'\0',4)+1;a=ABC(b[pos:])
  if not a.A['cls']:continue
  cls=a.A['cls'][0]
  if cls[0] not in ('LocalizedHtmlLabel','HtmlLabel','Label','ListItemRendererEx','ShopChainedListItemRenderer','UIComponent'):continue
  suffix='-core' if cls[0]!='ShopChainedListItemRenderer' or any(x[1]=='_chainRoundState' for x in cls[3]) else '-symbol'
  out=R/(name+'-'+cls[0]+suffix);out.with_suffix('.abc').write_bytes(b[pos:]);out.with_suffix('.txt').write_text(str(cls)+'\n'+'\n\n'.join('method '+str(m)+'\n'+'\n'.join(dis(a.A,code)) for m,code in a.A['body'].items()),encoding='utf8');print(cls[0],cls[3])
