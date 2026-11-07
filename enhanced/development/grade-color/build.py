"""Change vector timeline styling only: gold +9..13, chromatic shimmer +14..20."""
from pathlib import Path
import sys,struct,zlib,hashlib,json,colorsys
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
ROOT=Path(__file__).parent;CLIENT=Path(r'D:\FO3ID\32795');SERVER=Path(r'D:\FO3ID\server')
CONFIG={
 'components/TileList.big':[650,803,1414],
 'components/PlayerInfoNew.big':[203,226,329,475,498],
 'components/Label.big':[777,807],
 'components/ScrollingList.big':[613,636,682,1441],
 'components/SmoothList.big':[178],
 'TeamManagementTeamInfoTabPage.big':[75,107],
}
def sha(b):return hashlib.sha256(b).hexdigest()
def tags(d,p,end):
 while p+2<=end:
  at=p;v=struct.unpack_from('<H',d,p)[0];p+=2;t,n=v>>6,v&63
  if n==63:n=struct.unpack_from('<I',d,p)[0];p+=4
  assert p+n<=end
  yield t,d[p:p+n],d[at:p+n]
  p+=n
  if t==0:break
def tag(t,b):return struct.pack('<HI',t<<6|63,len(b))+b
class Bits:
 def __init__(self):self.bits=[]
 def put(self,v,n):self.bits.extend((v>>i)&1 for i in range(n-1,-1,-1));return self
 def output(self):
  b=self.bits+[0]*((-len(self.bits))%8)
  return bytes(sum(b[i+j]<<(7-j) for j in range(8)) for i in range(0,len(b),8))
def cx(mult,add=(0,0,0)):
 values=[round(x*256) for x in mult]+[256];extra=list(add)+[0];hasadd=any(extra)
 n=max(abs(v).bit_length()+1 for v in values+(extra if hasadd else []));assert n<=15
 b=Bits().put(hasadd,1).put(1,1).put(n,4)
 for v in values:b.put(v,n)
 if hasadd:
  for v in extra:b.put(v,n)
 return b.output()
def placement(cid,transform):
 return tag(26,b'\x0f'+struct.pack('<HH',1,cid)+b'\0'+transform)
def frames(sprite):
 out=[];pending=[]
 for t,b,raw in tags(sprite,4,len(sprite)):
  if t==0:return out,b''.join(pending)+raw
  pending.append((t,b,raw))
  if t==1:out.append(pending);pending=[]
 raise AssertionError('Missing sprite End')
def main_shape(frame):
 main=[struct.unpack_from('<H',b,3)[0] for t,b,_ in frame if t==26 and b[0]&2 and struct.unpack_from('<H',b,1)[0]==1]
 assert len(main)==1
 return main[0]
def glow(rgb):
 # Standard SWF GlowFilter: 2px blur, external glow, composite source retained.
 return b'\x01\x02'+bytes(rgb)+b'\xc0'+struct.pack('<IIH',2*65536,2*65536,320)+b'\x21'
def shimmer(cid,shape,grade):
 body=bytearray(struct.pack('<HH',cid,48));palette=[]
 for f in range(48):
  rgb=tuple(round(v*255) for v in colorsys.hsv_to_rgb(f/48,0.73,1))
  if grade<=15:mult=tuple(v/155 for v in rgb);add=(0,0,0)
  else:
   # Native +16..20 are already yellow. Keep their crisp digits, with a hue sweep
   # in their highlights and full chromatic glow rather than a gray/silver base.
   mult=(0.65+rgb[0]/255*0.6,0.65+rgb[1]/255*0.9,0.25+rgb[2]/255*4)
   add=tuple(round(v*0.11) for v in rgb)
  transform=cx(mult,add)
  # PlaceObject3: filters are independent of the parent's stopped grade frame.
  flags=0x0e if f==0 else 0x09
  b=bytes([flags,1])+struct.pack('<H',1)
  if f==0:b+=struct.pack('<H',shape)+b'\0'
  b+=transform+glow(rgb)
  body+=tag(70,b)+tag(1,b'');palette.append(dict(rgb=rgb,mult=mult,add=add))
 body+=tag(0,b'')
 return bytes(body),palette
def build():
 (ROOT/'payload').mkdir(exist_ok=True);reports=[]
 for relative,targets in CONFIG.items():
  source=CLIENT/'data/ui'/relative;raw=source.read_bytes();entries=bigdir.entries(source)
  member=next(n for n,*_ in entries if n.endswith('.gfx'));gfx=bigdir.read(source,member)
  assert gfx[:3]==b'CFX';swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(swf[8]>>3)+7)//8+4
  ts=list(tags(swf,start,len(swf)));defs={struct.unpack_from('<H',b)[0]:(t,b) for t,b,_ in ts if t in(2,22,32,83,39,1008)}
  assert not (set(range(62000,62021))&set(defs))
  changed={};wrappers={};palette={};checks={}
  for cid in targets:
   original=defs[cid][1];fs,tail=frames(original);assert len(fs)>=21
   high={g:main_shape(fs[g]) for g in range(11,21)}
   for g in range(14,21):
    if g in wrappers:assert wrappers[g][0]==high[g]
    else:
     wrapper,pal=shimmer(62000+g,high[g],g);wrappers[g]=(high[g],wrapper);palette[g]=pal
   for g in range(9,21):
    # +9/+10 already use native gold; the unused full-21 atlas symbol alone
    # has copper for these two grades and needs a warm gold transform as well.
    if g<11 and not(relative.endswith('TileList.big') and cid==1414):continue
    replacement=None
    if g>=14:replacement=placement(62000+g,cx((1,1,1)))
    elif g>=11:replacement=placement(high[g],cx((2.25,1.85,0.20),(-12,-10,0)))
    else:replacement=placement(main_shape(fs[g]),cx((1.9,2.5,0.25)))
    rebuilt=[];hits=0
    for t,b,r in fs[g]:
     if cid==1414 and relative.endswith('TileList.big') and t in (26,70,94):
      depth=struct.unpack_from('<H',b,1 if t==26 else 2)[0]
      if depth!=1:continue
     if t==26 and b[0]&2 and struct.unpack_from('<H',b,1)[0]==1:
      if cid==1414 and relative.endswith('TileList.big') and g==9:
       for depth in (2,4,6):rebuilt.append((28,struct.pack('<H',depth),tag(28,struct.pack('<H',depth))))
      rebuilt.append((26,b,replacement));hits+=1
     else:rebuilt.append((t,b,r))
    assert hits==1;fs[g]=rebuilt
   updated=original[:4]+b''.join(r for f in fs for _,_,r in f)+tail
   newframes,_=frames(updated);oldframes,_=frames(original)
   unchanged_count=9 if cid==1414 and relative.endswith('TileList.big') else 11
   assert [b''.join(r for _,_,r in f) for f in oldframes[:unchanged_count]]==[b''.join(r for _,_,r in f) for f in newframes[:unchanged_count]]
   assert newframes[21:]==oldframes[21:] and updated[:4]==original[:4]
   changed[cid]=updated;checks[cid]=dict(frames=len(fs),native_low_frames_identical=unchanged_count,tail_after_grade20_identical=True)
  additions=[tag(39,w[1]) for g,w in sorted(wrappers.items())]
  parts=[];inserted=False
  # Root ShowFrame is reached after the symbol dictionary has been loaded.
  for t,b,r in ts:
   if t==1 and not inserted:parts.extend(additions);inserted=True
   if t==39 and struct.unpack_from('<H',b)[0] in changed:r=tag(t,changed[struct.unpack_from('<H',b)[0]])
   parts.append(r)
  assert inserted
  updated=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',updated,4,len(updated))
  newgfx=b'CFX'+updated[3:8]+zlib.compress(updated[8:],9)
  output=ROOT/'payload'/source.name;output.write_bytes(raw);bigdir.patch(output,{member:newgfx})
  assert bigdir.read(output,member)==newgfx
  after=output.read_bytes()
  for name,off,size,usize in entries:
   if name!=member:
    _,no,ns,nu=next(e for e in bigdir.entries(output) if e[0]==name)
    assert (size,usize)==(ns,nu) and raw[off:off+size]==after[no:no+ns]
  # All ABC, texture IDs, shape-to-image references and non-target definitions stay exact.
  newts=list(tags(updated,start,len(updated)))
  old_other=[r for t,b,r in ts if not(t==39 and struct.unpack_from('<H',b)[0] in changed)]
  new_other=[r for t,b,r in newts if not(t==39 and (struct.unpack_from('<H',b)[0] in changed or 62014<=struct.unpack_from('<H',b)[0]<=62020))]
  assert old_other==new_other
  for g,(shape,w) in wrappers.items():assert defs[shape][0] in (2,22,32,83)
  patchsource=SERVER/'patches'/source.name
  assert patchsource.read_bytes()==raw,'Current runtime and installer source differ; reconcile before styling'
  (ROOT/(source.stem+'.updated.swf')).write_bytes(updated)
  reports.append(dict(relative='data/ui/'+relative,before_sha256=sha(raw),after_sha256=sha(after),payload=str(output),
                      installer_source='patches/'+source.name,sprites=checks,all_abc_and_non_target_swf_tags_identical=True,
                      all_dds_and_other_archive_members_identical=True,high_animation_frames=48,palette=palette))
 report=dict(version='grade-color-v1',gold_grades=[9,10,11,12,13],shimmer_grades=list(range(14,21)),
             files=reports,native_status='NOT_VERIFIED',state_shop_written=False)
 (ROOT/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({'status':'BUILD_PASS','archives':len(reports),'sprites':sum(len(r['sprites']) for r in reports)}))
 return report
if __name__=='__main__':build()
