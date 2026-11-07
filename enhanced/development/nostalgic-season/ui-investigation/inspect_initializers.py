exec((__import__('pathlib').Path(__file__).parent/'inspect_module.py').read_text('utf-8').split('result={};inventory=[];hashes={}')[0])
path=Path(r'D:/FO3ID/32795/data/ui/libs/Module.big');gfx=bigdir.read(path,next(n for n,*_ in bigdir.entries(path) if n.endswith('.gfx')))
plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4;out={}
for kind,body,offset in tags(plain,start):
 if kind!=82:continue
 pos=body.index(b'\0',4)+1;a=ABC(body[pos:])
 for cls,sup,ii,it,ci,ct in a.A['cls']:
  methods={name:mid for k,name,mid in it+ct if k in ('method','get','set')}
  for name,mid in methods.items():
   if 'season' in name.lower() and cls!='PlayerListUtil':
    out[cls+'.'+name]=dict(mid=mid,offset=offset,code='\n'.join(dis(a.A,a.A['body'][mid])) if mid in a.A['body'] else '')
  if cls=='PlayerListUtil':out[cls+'.cinit']=dict(mid=ci,offset=offset,code='\n'.join(dis(a.A,a.A['body'][ci])))
(ROOT/'season-extra-methods.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
print('\n'.join(out))
