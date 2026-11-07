"""Repair the original native GFx carrier without changing any installed ABC."""
from pathlib import Path
import sys,json,hashlib,zlib,struct,collections
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path[:0]=['D:/FO3ID/server/tools/re','D:/fifaol3/season-display','D:/fifaol3/player-detail-traits']
import bigdir
from build_moments_display import tags,replace_ui_member
from inspect_ui import ABC
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def build():
 out=R/'build';out.mkdir(exist_ok=True)
 source=C/'data/ui/SquadAssets.big';baseline=sha(source)
 original=S/'backups/player-detail-traits-20261107-215155-650999/4-SquadAssets.big'
 assert sha(original)=='8fe027c0d20a9de9522697d892178ea61de96bd11368eb58850883a62568f085'
 member='data/ui/SquadAssets.gfx';current=bigdir.read(source,member);native=bigdir.read(original,member)
 assert native[:3]==b'CFX' and current[:3]==b'CWS', 'Fresh carrier requires review'
 repaired=native[:3]+current[3:]
 assert repaired[3:]==current[3:] and len(repaired)==len(current)
 replace_ui_member(source,out/'SquadAssets.big',member,repaired,bigdir)
 readback=bigdir.read(out/'SquadAssets.big',member);assert readback==repaired
 d=b'FWS'+repaired[3:8]+zlib.decompress(repaired[8:]);assert struct.unpack_from('<I',d,4)[0]==len(d)
 start=8+(5+4*(d[8]>>3)+7)//8+4
 tagged=list(tags(d,start));counts=collections.Counter(k for k,_,_ in tagged)
 assert {k:v for k,v in counts.items() if k>=1000}=={1000:1,1009:3,1008:53}
 blocks=[]
 for kind,body,_ in tagged:
  if kind==82:
   pos=body.index(b'\0',4)+1;abc=ABC(body[pos:]);blocks.append(hashlib.sha256(body[pos:]).hexdigest())
   assert abc.A['end']==len(body[pos:])
 original_bytes=source.read_bytes();new_bytes=(out/'SquadAssets.big').read_bytes()
 a=bigdir.entries(source);b=bigdir.entries(out/'SquadAssets.big')
 assert [x[0] for x in a]==[x[0] for x in b]
 for old,new in zip(a,b):
  if old[0]!=member:
   assert original_bytes[old[1]:old[1]+old[2]]==new_bytes[new[1]:new[1]+new[2]] and old[2:]==new[2:]
 assert all(x[1]+x[2]<=y[1] for x,y in zip(b,b[1:]))
 assert sha(source)==baseline
 report=dict(status='NATIVE_CARRIER_REPAIR_BUILD_PASS',source=str(source),source_sha256=baseline,
  original_native_source=str(original),original_native_sha256=sha(original),source_signature=current[:3].decode(),repaired_signature=repaired[:3].decode(),
  output_sha256=sha(out/'SquadAssets.big'),only_uncompressed_member_byte_changes=[0,1,2],
  all_installed_ABC_and_timelines_exact=True,all_font_texture_tags_exact=True,all_other_compressed_members_exact=True,
  abc_blocks=len(blocks),abc_sha256=blocks,GFx_special_tags={k:v for k,v in counts.items() if k>=1000},
  native_player_open_verified=False,match_verified=False,formal_written=False)
 save(out/'report.json',report);print(json.dumps(report));return report
if __name__=='__main__':build()
