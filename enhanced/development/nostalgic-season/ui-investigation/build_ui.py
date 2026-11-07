"""Source-bound season19 UI delta. Writes only caller-selected work artifacts."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,struct,sys,zlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
WORK=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path[:0]=[str(WORK/'work/experience_levels'),r'D:/FO3ID/server/tools/re']
from avm_patch import ABC,Code,parse,dis
import bigdir
SID=19
KEY='FC_CUSTOM_SEASON_19'
NAME='怀旧神兽'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):Path(p).write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')
def tag(kind,body):return struct.pack('<HI',kind<<6|63,len(body))+body
def tags(data,pos):
 while pos+2<=len(data):
  start=pos;h=struct.unpack_from('<H',data,pos)[0];pos+=2;kind,size=h>>6,h&63
  if size==63:size=struct.unpack_from('<I',data,pos)[0];pos+=4
  yield kind,data[pos:pos+size],data[start:pos+size];pos+=size
  if kind==0:break
def load_gfx(path):
 member=next(n for n,*_ in bigdir.entries(path) if n.endswith('.gfx'));gfx=bigdir.read(path,member)
 assert gfx[:3] in (b'CFX',b'CWS')
 plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4
 return member,plain,start
def repack(source,target,member,replacement):
 # Private UI-container repack; retains every other compressed payload, not the global BIG writer.
 original=Path(source).read_bytes();records=[]
 for name,offset,size,usize in bigdir.entries(source):records.append((name,replacement if name==member else original[offset:offset+size],0 if name==member else usize))
 minimum=17+sum(17+len(n.encode('latin1')) for n,*_ in records);header_size=max(len(bigdir.table(source)),(minimum+127)//128*128)
 output=bytearray(header_size);table=bytearray(b'BIg4'+bytes(4)+struct.pack('>II',bigdir.enc(len(records)),bigdir.enc(header_size))+b'\0')
 for name,payload,usize in records:
  offset=(len(output)+127)//128*128;output+=bytes(offset-len(output))+payload
  table+=struct.pack('>4I',bigdir.enc(offset),bigdir.enc(len(payload)),bigdir.enc(usize),bigdir.enc(len(name)))
  key=len(payload)&255
  for ch in name.encode('latin1'):
   v=ch^key;table.append(((v<<4)|(v>>4))&255);key=((v or len(payload)&255)-0x66)&255
  table.append(0)
 struct.pack_into('<I',table,4,len(output));output[:len(table)]=table;Path(target).write_bytes(output)
 for old,new in zip(bigdir.entries(source),bigdir.entries(target)):
  assert old[0]==new[0]
  if old[0]!=member:assert original[old[1]:old[1]+old[2]]==output[new[1]:new[1]+new[2]]
def save_gfx(source,target,member,plain):
 plain=bytearray(plain);struct.pack_into('<I',plain,4,len(plain));repack(source,target,member,b'CFX'+plain[3:8]+zlib.compress(plain[8:],9))
 assert zlib.decompress(bigdir.read(target,member)[8:])==plain[8:]
def symbols(rows):
 result={}
 for kind,body,_ in rows:
  if kind not in (56,76):continue
  count=struct.unpack_from('<H',body)[0];pos=2
  for _ in range(count):
   cid=struct.unpack_from('<H',body,pos)[0];pos+=2;end=body.index(b'\0',pos);result[body[pos:end].decode('utf-8')]=cid;pos=end+1
 return result
def frame_labels(body):
 frame=1;result={}
 for kind,payload,_ in tags(body,4):
  if kind==43:result[payload.split(b'\0')[0].decode('utf-8')]=frame
  if kind==1:frame+=1
 return result
def placement_depth(kind,payload):
 if kind==26:return struct.unpack_from('<H',payload,1)[0]
 if kind==70:return struct.unpack_from('<H',payload,2)[0]
 if kind in (4,5):return struct.unpack_from('<H',payload,2)[0]
 if kind==28:return struct.unpack_from('<H',payload)[0]
def display_state(body,until=None):
 frame=1;active=set();commands=[]
 for kind,payload,raw in tags(body,4):
  if until is not None and frame>until:break
  if kind in (4,26,70):active.add(placement_depth(kind,payload));commands.append(raw)
  if kind in (5,28):active.discard(placement_depth(kind,payload));commands.append(raw)
  if kind==1:frame+=1
 return active,commands
def append_frame(body,commands):
 labels=frame_labels(body);label=f'{SID}season';assert label not in labels
 old=list(tags(body,4));assert old[-1][0]==0
 oldprefix=b''.join(raw for kind,payload,raw in old[:-1]);count=struct.unpack_from('<H',body,2)[0]
 active,_=display_state(body)
 new=body[:2]+struct.pack('<H',count+1)+oldprefix+tag(43,label.encode()+b'\0')
 new+=b''.join(tag(28,struct.pack('<H',depth)) for depth in sorted(active))
 new+=b''.join(commands)+tag(1,b'')+tag(0,b'')
 assert new[4:4+len(oldprefix)]==oldprefix
 assert {k:v for k,v in frame_labels(new).items() if k!=label}==labels
 assert frame_labels(new)[label]==count+1
 return new

# Pure-vector OG shield, no font, external image ID or texture dependency.
POLYGONS=[(1,[(100,30),(900,30),(980,130),(940,760),(500,1000),(60,760),(20,130)]),
          (2,[(135,95),(865,95),(910,160),(875,720),(500,915),(125,720),(90,160)]),
          (3,[(190,300),(440,300),(440,365),(190,365)]),(3,[(190,365),(255,365),(255,625),(190,625)]),
          (3,[(375,365),(440,365),(440,625),(375,625)]),(3,[(190,625),(440,625),(440,690),(190,690)]),
          (3,[(530,300),(810,300),(810,365),(530,365)]),(3,[(530,365),(595,365),(595,625),(530,625)]),
          (3,[(530,625),(810,625),(810,690),(530,690)]),(3,[(745,510),(810,510),(810,625),(745,625)]),
          (3,[(655,485),(810,485),(810,550),(655,550)])]
def vector_shape(cid,bounds):
 # Reuse the already audited shape-bit encoder, with task-owned geometry only.
 source=Path('D:/fifaol3/season-display/build_moments_display.py')
 spec=importlib.util.spec_from_file_location('og_shape_encoder',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.POLYGONS=POLYGONS
 return m.shape(cid,bounds)
def shape_id(rows):
 defined={2,6,7,10,11,14,20,21,22,32,33,34,35,36,37,39,46,48,60,75,83,84,87,91}
 ids=[struct.unpack_from('<H',body)[0] for kind,body,_ in rows if kind in defined and len(body)>=2]
 ids+=list(symbols(rows).values());result=max(ids)+1;assert result+1<65535;return result

def build_ui(sourceModule,sourceLabel,output,sourcePlayerInfo=None,sourceLanguage=None):
 sourceModule,sourceLabel,output=map(lambda p:Path(p).resolve(),(sourceModule,sourceLabel,output))
 sourcePlayerInfo=Path(sourcePlayerInfo or sourceLabel.parent/'PlayerInfoNew.big').resolve()
 sourceLanguage=Path(sourceLanguage or 'D:/FO3ID/server/patches/language_chi.big').resolve()
 assert not output.exists()
 for protected in (Path('D:/FO3ID/server'),Path('D:/FO3ID/32795')):assert not output.is_relative_to(protected)
 sources=[sourceModule,sourceLabel,sourcePlayerInfo,sourceLanguage];before={str(p):sha(p) for p in sources};output.mkdir(parents=True)
 member,plain,start=load_gfx(sourceModule);oldrows=list(tags(plain,start));parts=[];modified=[]
 for kind,body,raw in oldrows:
  if kind==82 and b'PlayerListUtil' in body:
   at=body.index(b'\0',4)+1;a=ABC(body[at:])
   if a.A['cls'][0][0]=='PlayerListUtil':
    methods={name:mid for k,name,mid in a.A['cls'][0][5] if k in ('method','get','set')};mid=methods['getSeasonString'];old=dict(a.A['body']);assert KEY.encode() not in body
    c=Code(a).local(1).number(SID).jump(0x14,'original').op(0x60,a.own('Localization')).string(KEY).call('getLocalizedString',1).op(0x48).label('original')
    a.modify(mid,{2:c.done()});new=a.output();parsed=parse(new,0)
    assert set(parsed['body'])==set(old) and all(parsed['body'][i]==value for i,value in old.items() if i!=mid)
    raw=tag(kind,body[:at]+new);modified.append(mid)
    (output/'getSeasonString.txt').write_text('\n'.join(dis(parsed,parsed['body'][mid])),'utf-8')
  parts.append(raw)
 assert modified==[14]
 save_gfx(sourceModule,output/'Module.big',member,plain[:start]+b''.join(parts))
 member,plain,start=load_gfx(sourceLabel);rows=list(tags(plain,start));names=symbols(rows);targets={names['DefaultSeasonIcon']:False,names['seasonIconBig']:True};newid=shape_id(rows);parts=[];icon_frames=[]
 for kind,body,raw in rows:
  if kind==39 and struct.unpack_from('<H',body)[0] in targets:
   cid=struct.unpack_from('<H',body)[0];big=targets[cid];sid=newid+(1 if big else 0)
   # Define the new shape before the sprite that references it.
   parts.append(tag(2,vector_shape(sid,(-40,720,-20,700) if big else (-40,400,-40,440))))
   commands=[tag(26,b'\x06'+struct.pack('<HH',1,sid)+b'\0')]
   new=append_frame(body,commands);raw=tag(kind,new);icon_frames.append(dict(sprite=cid,frame=frame_labels(new)[f'{SID}season'],shape=sid,big=big))
  parts.append(raw)
 assert len(icon_frames)==2
 save_gfx(sourceLabel,output/'Label.big',member,plain[:start]+b''.join(parts))
 member,plain,start=load_gfx(sourcePlayerInfo);rows=list(tags(plain,start));names=symbols(rows);target=next(v for k,v in names.items() if k.endswith('.cardBackground_59'));parts=[];bg=[]
 for kind,body,raw in rows:
  if kind==39 and struct.unpack_from('<H',body)[0]==target:
   labels=frame_labels(body);assert '30season' in labels
   _,commands=display_state(body,labels['30season']);new=append_frame(body,commands);raw=tag(kind,new)
   bg.append(dict(sprite=target,donor_season=30,frame=frame_labels(new)[f'{SID}season'],replayed_commands=len(commands)))
  parts.append(raw)
 assert len(bg)==1
 save_gfx(sourcePlayerInfo,output/'PlayerInfoNew.big',member,plain[:start]+b''.join(parts))
 values=json.loads(bigdir.read(sourceLanguage,'data/ui/external/LANGUAGESTRING_CHI.json'));assert KEY not in values;oldvalues=dict(values);values[KEY]=NAME
 repack(sourceLanguage,output/'language_chi.big','data/ui/external/LANGUAGESTRING_CHI.json',json.dumps(values,ensure_ascii=False,separators=(',',':')).encode())
 checked_language=json.loads(bigdir.read(output/'language_chi.big','data/ui/external/LANGUAGESTRING_CHI.json'))
 assert all(checked_language[k]==v for k,v in oldvalues.items())
 colors={1:'#e1b64e',2:'#19202f',3:'#ffefbb'}
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="-60 -40 1120 1120">'+''.join('<polygon fill="'+colors[fill]+'" points="'+' '.join(f'{x},{y}' for x,y in points)+'"/>' for fill,points in POLYGONS)+'</svg>'
 (output/'og-badge.svg').write_text(svg,'utf-8')
 assert all(sha(Path(p))==v for p,v in before.items())
 report=dict(status='SOURCE_BOUND_UI_DELTA_NOT_INSTALLED',season=SID,name=NAME,key=KEY,module_only_method14_changed=True,all_other_module_methods_exact=True,
             xp_and_currency_preserved=True,label_all_old_frames_exact=True,label_all_abc_exact=True,icons=icon_frames,playerinfo_all_old_frames_exact=True,
             playerinfo_all_abc_exact=True,background=bg,all_old_language_keys_preserved=True,source_hashes=before,shape_encoder_sha256=sha('D:/fifaol3/season-display/build_moments_display.py'),
             output_hashes={n:sha(output/n) for n in ('Module.big','Label.big','PlayerInfoNew.big','language_chi.big')},native_verified=False,production_written=False)
 write(output/'ui-manifest.json',report);return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--module',required=True);p.add_argument('--label',required=True);p.add_argument('--out',required=True);p.add_argument('--player-info');p.add_argument('--language');a=p.parse_args()
 print(json.dumps(build_ui(a.module,a.label,a.out,a.player_info,a.language),ensure_ascii=True,indent=2))
