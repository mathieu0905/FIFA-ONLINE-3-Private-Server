from pathlib import Path
import sys,zlib,json,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(H));from avm_patch import ABC,dis
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags
R=Path(__file__).resolve().parent
for name,path in [('TileList',Path(r'D:\FO3ID\32795\data\ui\components\TileList.big')),('Module',Path(r'D:\FO3ID\32795\data\ui\libs\Module.big'))]:
 member=next(n for n,*_ in bigdir.entries(path) if n.endswith('.gfx'));g=bigdir.read(path,member);s=b'FWS'+g[3:8]+zlib.decompress(g[8:]);(R/(name+'.swf')).write_bytes(s);start=8+(5+4*(s[8]>>3)+7)//8+4
 for tag,b,raw in tags(s,start,len(s)):
  if tag!=82:continue
  p=b.index(b'\0',4)+1;a=ABC(b[p:])
  if not a.A['cls']:continue
  cls=a.A['cls'][0]
  if cls[0] not in ('ShopController','ShopChainedListItemRenderer','ShopChainedTileItemRenderer'):continue
  lines=[str(cls)]
  for mid,code in a.A['body'].items():lines+=['method '+str(mid)]+list(dis(a.A,code))
  suffix='-core' if any(x[1] in ('_itemsDataProvider','randomContainer','_shoplist') for x in cls[3]) else '-symbol'
  (R/(name+'-'+cls[0]+suffix+'.txt')).write_text('\n'.join(lines),encoding='utf8')
  (R/(name+'-'+cls[0]+suffix+'.abc')).write_bytes(b[p:])
  print(name,cls[0],suffix,cls[3])
print('ARCHIVE DIGESTS',json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(r'D:\FO3ID\32795\data\ui\components\TileList.big'),Path(r'D:\FO3ID\32795\data\ui\libs\Module.big')]}))
