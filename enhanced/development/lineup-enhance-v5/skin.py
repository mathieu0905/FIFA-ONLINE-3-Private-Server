"""Code-native SWF upgrade glyph over the original capsule and bitmap atlas.
No DDS pixels, original symbols or original classes are changed.
"""
from pathlib import Path
import sys,struct,zlib,json
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\fifaol3\enhancement-entry-fix')
from client_tools import ABC,R,u30,tags,tag,pack_archive,bigdir
W=Path(__file__).resolve().parent
class Bits:
 def __init__(self):self.bits=[]
 def u(self,v,n):self.bits += [(v>>i)&1 for i in range(n-1,-1,-1)];return self
 def s(self,v,n):return self.u(v&((1<<n)-1),n)
 def bytes(self):
  b=self.bits+[0]*((-len(self.bits))%8);return bytes(sum(b[i+j]<<(7-j) for j in range(8)) for i in range(0,len(b),8))
def width(*vals):return max(1,max(abs(v).bit_length()+1 for v in vals))
def rect(x,y):
 n=width(0,x,0,y);return Bits().u(n,5).s(0,n).s(x,n).s(0,n).s(y,n).bytes()
def matrix(sx,sy,tx=0,ty=0):
 a,b=round(sx*65536),round(sy*65536);n=width(a,b);m=width(tx,ty)
 return Bits().u(1,1).u(n,5).s(a,n).s(b,n).u(0,1).u(m,5).s(tx,m).s(ty,m).bytes()
def shape(cid,bitmap,state):
 colors=[(0x48,0x81,0x9a),(0x74,0xa8,0xc0),(0x37,0x65,0x7b)]
 light=[(0xbd,0xcc,0xd3),(0xe0,0xec,0xf1),(0x9b,0xb2,0xbe)]
 fills=b'\x04'+b'\x41'+struct.pack('<H',bitmap)+matrix(20,20)+b'\x41'+struct.pack('<H',bitmap)+matrix(580,20,-6600,0)+b'\x00'+bytes(light[state])+b'\x00'+bytes(colors[state])
 bits=Bits().u(3,4).u(0,4)
 def path(style,points):
  points=[(int(x*20),int(y*20)) for x,y in points];x,y=points[0];n=width(x,y)
  bits.u(0,1).u(5,5).u(n,5).s(x,n).s(y,n).u(style,3)
  for nx,ny in points[1:]+[points[0]]:
   dx,dy=nx-x,ny-y;n=max(2,width(dx,dy));bits.u(1,1).u(1,1).u(n-2,4)
   if dx and dy:bits.u(1,1).s(dx,n).s(dy,n)
   else:bits.u(0,1).u(1 if dy else 0,1).s(dy if dy else dx,n)
   x,y=nx,ny
 path(1,[(0,0),(67,0),(67,35),(0,35)])
 # Reuse a clean vertical strip of the same atlas button to clear only the
 # old exchange glyph area. Outline, capsule corners and shading stay native.
 path(2,[(18,0),(47,0),(47,35),(18,35)])
 path(3,[(23,17),(32,8),(41,17),(37,17),(32,12),(27,17)])
 path(4,[(23,24),(32,15),(41,24),(37,24),(32,19),(27,24)])
 bits.u(0,6)
 return struct.pack('<H',cid)+rect(1340,700)+fills+b'\x00'+bits.bytes()

def build():
 source=Path(r'D:\FO3ID\32795\data\ui\components\Button.big');(W/'components-Button-baseline.big').write_bytes(source.read_bytes());member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'));gfx=bigdir.read(source,member);swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4
 records=list(tags(swf,start,len(swf)));sprites={};shapes={};symbols={};abc=None;symbol_ordinal=None;maxid=0
 for i,(k,b,_) in enumerate(records):
  if k in (2,6,10,11,20,21,22,32,33,35,36,37,39,48,75,83,90,1008):maxid=max(maxid,int.from_bytes(b[:2],'little'))
  if k==39:sprites[int.from_bytes(b[:2],'little')]=b
  if k==2:shapes[int.from_bytes(b[:2],'little')]=b
  if k==76:
   symbol_ordinal=i
   p=2
   for _ in range(int.from_bytes(b[:2],'little')):
    cid=int.from_bytes(b[p:p+2],'little');p+=2;e=b.index(b'\0',p);symbols[b[p:e].decode()]=cid;p=e+1
  if k==82:
   h=b.index(b'\0',4)+1;a=ABC(b[h:])
   if any(c[0]=='PlayerSwapButton' for c in a.A['cls']):abc=b[h:]
 assert abc and symbol_ordinal is not None and 'Fo3LineupUpgradeButton' not in symbols
 sprite=sprites[symbols['PlayerSwapButton']];ids=[]
 for k,b,_ in tags(sprite,4,len(sprite)):
  if k==26 and b[0]&2:
   cid=int.from_bytes(b[3:5],'little')
   if cid not in ids:ids.append(cid)
 assert ids==[2402,2404,2406]
 replacement={old:maxid+1+i for i,old in enumerate(ids)};newid=maxid+4;added=[]
 for i,cid in enumerate(ids):
  b=shapes[cid];p=2+(5+(b[2]>>3)*4+7)//8;assert b[p:p+2]==b'\x01\x41';bitmap=int.from_bytes(b[p+2:p+4],'little');added.append(tag(2,shape(replacement[cid],bitmap,i)))
 parts=[]
 for k,b,raw in tags(sprite,4,len(sprite)):
  if k==26 and b[0]&2:
   b=b[:3]+struct.pack('<H',replacement[int.from_bytes(b[3:5],'little')])+b[5:];raw=tag(k,b)
  parts.append(raw)
 added.append(tag(39,struct.pack('<H',newid)+sprite[2:4]+b''.join(parts)))
 a=ABC(abc);_,count,entries,end=a.pools[3];r=R(abc,entries);strings=[]
 for _ in range(count-1):
  n=r.u30();value=abc[r.p:r.p+n];r.p+=n;value=value.replace(b'PlayerSwapButton',b'Fo3LineupUpgradeButton');strings.append(u30(len(value))+value)
 newabc=abc[:entries]+b''.join(strings)+abc[end:];check=ABC(newabc);assert check.A['cls'][0][0]=='Fo3LineupUpgradeButton'
 for mid,body in a.A['body_records'].items():assert body['raw']==check.A['body_records'][mid]['raw']
 added.append(tag(82,b'\x00\x00\x00\x00Fo3LineupUpgradeButton\x00'+newabc))
 out=[]
 for i,(k,b,raw) in enumerate(records):
  if i==symbol_ordinal:
   out+=added;raw=tag(76,struct.pack('<H',int.from_bytes(b[:2],'little')+1)+b[2:]+struct.pack('<H',newid)+b'Fo3LineupUpgradeButton\x00')
  out.append(raw)
 result=bytearray(swf[:start]+b''.join(out));struct.pack_into('<I',result,4,len(result));target=W/'components-Button.big';pack_archive(source,target,{member:b'CFX'+result[3:8]+zlib.compress(result[8:],9)},[])
 for name,*_ in bigdir.entries(source):
  if name!=member:assert bigdir.read(source,name)==bigdir.read(target,name)
 (W/'Fo3LineupUpgradeButton.abc').write_bytes(newabc)
 return dict(new_class='Fo3LineupUpgradeButton',native_state_timeline_preserved=True,all_original_symbols_and_dds_preserved=True,native_dimensions=[67,35],new_symbol=newid)
if __name__=='__main__':print(json.dumps(build()))
