exec((__import__('pathlib').Path(__file__).parent/'inspect_module.py').read_text('utf-8').split('result={};inventory=[];hashes={}')[0])
path=Path(r'D:/FO3ID/32795/data/ui/components/Label.big');member=next(n for n,*_ in bigdir.entries(path) if n.endswith('.gfx'))
gfx=bigdir.read(path,member);plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4
symbols={};sprites={}
for kind,body,offset in tags(plain,start):
 if kind in (56,76):
  count=struct.unpack_from('<H',body)[0];pos=2
  for i in range(count):
   cid=struct.unpack_from('<H',body,pos)[0];pos+=2;end=body.index(b'\0',pos);name=body[pos:end].decode('utf-8');pos=end+1;symbols[cid]=name
 if kind==39:sprites[struct.unpack_from('<H',body)[0]]=(body,offset)
out={}
for cid,name in symbols.items():
 if not any(s in name.lower() for s in ('seasonicon','seasonplate','season1')):continue
 if cid not in sprites:continue
 body,offset=sprites[cid];frame=1;labels={};placements=[]
 for kind,payload,at in tags(body,4):
  if kind==43:labels[payload.split(b'\0')[0].decode('utf-8')]=frame
  if kind==1:frame+=1
  if kind==26 and payload[0]&2:placements.append(dict(frame=frame,character=struct.unpack_from('<H',payload,3)[0]))
  if kind==70 and payload[0]&2:
   # Optional class name can precede character ID for PlaceObject3.
   pos=4
   if payload[1]&8 or (payload[1]&16 and payload[0]&2):pos=payload.index(b'\0',pos)+1
   placements.append(dict(frame=frame,character=struct.unpack_from('<H',payload,pos)[0]))
 out[name]=dict(id=cid,offset=offset,frames=struct.unpack_from('<H',body,2)[0],labels=labels,placements=placements)
(ROOT/'labels.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(out,ensure_ascii=True,indent=2))
