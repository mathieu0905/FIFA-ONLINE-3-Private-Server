from pathlib import Path
import sys,struct
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags
H=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
src=(H/'layout_probe.py').read_text('utf8');src=src[src.index('class B:'):src.index("d=Path(")];src=src.replace('v&(1<<(n-1))','n and v&(1<<(n-1))');exec(src)
s=Path(r'D:\fifaol3\chain-ui-fix\TileList.swf').read_bytes();start=8+(5+4*(s[8]>>3)+7)//8+4;ts=list(tags(s,start,len(s)));ids=[]
for t,b,raw in ts:
 if t==76:
  p=2
  for _ in range(struct.unpack_from('<H',b)[0]):
   sid=struct.unpack_from('<H',b,p)[0];p+=2;e=b.index(0,p);name=b[p:e].decode();p=e+1
   if 'ShopChainedListItemRenderer' in name or 'ShopChainedTileItemRenderer' in name:print('SYMBOL',sid,name);ids.append(sid)
for t,b,raw in ts:
 if t!=39 or struct.unpack_from('<H',b)[0] not in ids:continue
 sid=struct.unpack_from('<H',b)[0];frame=1
 for tt,bb,rr in tags(b,4,len(b)):
  if tt==1:frame+=1
  if tt not in (26,70):continue
  flags=bb[0];flags2=bb[1] if tt==70 else 0;p=4 if tt==70 else 3
  if flags2&8:p=bb.index(0,p)+1
  cid=None
  if flags&2:cid=struct.unpack_from('<H',bb,p)[0];p+=2
  r=B(bb,p*8);matrix=r.matrix() if flags&4 else None;p=r.p//8
  if flags&8:
   r=B(bb,p*8);add=r.r(1);mul=r.r(1);n=r.r(4)
   if mul:[r.r(n,True) for _ in range(4)]
   if add:[r.r(n,True) for _ in range(4)]
   p=(r.p+7)//8
  if flags&16:p+=2
  name=bb[p:bb.index(0,p)].decode('ascii','replace') if flags&32 else ''
  if name:print(sid,'frame',frame,name,cid,matrix)

