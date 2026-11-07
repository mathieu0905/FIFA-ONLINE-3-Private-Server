from pathlib import Path
import sys,struct
sys.path.insert(0,r'D:\fifaol3\grade-color');from build import tags
s=Path(r'D:\fifaol3\chain-ui-fix\TileList.swf').read_bytes();start=8+(5+4*(s[8]>>3)+7)//8+4
for t,b,_ in tags(s,start,len(s)):
 if t==39 and struct.unpack_from('<H',b)[0]==856:
  for tt,bb,rr in tags(b,4,len(b)):
   if b'buyButton' in bb:print('BUY PLACE',tt,bb.hex(),bb)
 if t in (57,71):print('IMPORT',t,b[:500])
 if t==76:
  p=2;names=[]
  for _ in range(struct.unpack_from('<H',b)[0]):
   cid=struct.unpack_from('<H',b,p)[0];p+=2;e=b.index(0,p);n=b[p:e].decode();p=e+1
   if 'Button' in n:names.append((cid,n))
  print('BUTTON SYMBOLS',names)
