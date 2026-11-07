"""Read-only, format-level checks of the emitted timeline/filter references."""
from build import *
class Reader:
 def __init__(self,b):self.b=b;self.p=0
 def read(self,n,signed=False):
  v=0
  for _ in range(n):v=v*2+((self.b[self.p//8]>>(7-self.p%8))&1);self.p+=1
  return v-(1<<n) if signed and v&(1<<(n-1)) else v
def decode_cx(b):
 r=Reader(b);add=r.read(1);mult=r.read(1);n=r.read(4)
 m=[r.read(n,True) for _ in range(4)] if mult else [256]*4
 a=[r.read(n,True) for _ in range(4)] if add else [0]*4
 return m,a,(r.p+7)//8
def check():
 installed='--installed' in sys.argv
 report=json.loads((ROOT/'build.json').read_text('utf8'));results=[]
 for row in report['files']:
  relative=row['relative'];source=CLIENT/relative;target=Path(row['payload'])
  assert sha(source.read_bytes())==row['after_sha256' if installed else 'before_sha256'] and sha(target.read_bytes())==row['after_sha256']
  if installed:target=source
  n=next(n for n,*_ in bigdir.entries(target) if n.endswith('.gfx'));gfx=bigdir.read(target,n)
  swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);assert len(swf)==struct.unpack_from('<I',swf,4)[0]
  start=8+(5+4*(swf[8]>>3)+7)//8+4;ts=list(tags(swf,start,len(swf)))
  defs={struct.unpack_from('<H',b)[0]:(t,b) for t,b,_ in ts if t in(2,22,32,83,39,1008)}
  for grade in range(14,21):
   wrapper=defs[62000+grade][1];fs,tail=frames(wrapper)
   assert len(fs)==48 and struct.unpack_from('<H',wrapper,2)[0]==48
   colors=set()
   for i,frame in enumerate(fs):
    placements=[b for t,b,_ in frame if t==70];assert len(placements)==1
    b=placements[0];assert b[:2]==(b'\x0e\x01' if i==0 else b'\x09\x01') and b[2:4]==b'\x01\x00'
    p=4
    if i==0:
     shape=struct.unpack_from('<H',b,p)[0];assert defs[shape][0] in (2,22,32,83);p+=2
     assert b[p]==0;p+=1
    m,a,size=decode_cx(b[p:]);p+=size
    assert m[3]==256 and a[3]==0 and all(0<=v<16384 for v in m)
    assert b[p:p+2]==b'\x01\x02' and len(b[p:])==17
    colors.add(tuple(b[p+2:p+5]));assert b[-1]==0x21
   assert len(colors)==48
  for cid in CONFIG[relative.removeprefix('data/ui/')]:
   fs,tail=frames(defs[cid][1])
   for grade in range(11,21):
    b=next(b for t,b,_ in fs[grade] if t==26 and b[0]&2 and b[1:3]==b'\x01\0')
    assert b[0]==0xf and b[5]==0
    shape=struct.unpack_from('<H',b,3)[0];m,a,size=decode_cx(b[6:]);assert len(b)==6+size
    if grade<14:assert m==[576,474,51,256] and a==[-12,-10,0,0]
    else:assert shape==62000+grade and m==[256]*4
  results.append(dict(relative=relative,high_grades=7,independent_animation_frames=48,gold_11_13=True))
 result=dict(status='PASS',checks=results,scope='Resource/timeline/filter structure and references; native rendering not observed')
 (ROOT/('checks-installed.json' if installed else 'checks.json')).write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
if __name__=='__main__':check()
