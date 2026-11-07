exec((__import__('pathlib').Path(__file__).parent/'inspect_module.py').read_text('utf-8').split('result={};inventory=[];hashes={}')[0])
path=Path(r'D:/FO3ID/32795/data/ui/components/PlayerInfoNew.big');gfx=bigdir.read(path,next(n for n,*_ in bigdir.entries(path) if n.endswith('.gfx')))
plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4;out={}
for kind,body,offset in tags(plain,start):
 if kind!=82:continue
 pos=body.index(b'\0',4)+1;a=ABC(body[pos:])
 for cls,sup,ii,it,ci,ct in a.A['cls']:
  methods={name:mid for k,name,mid in it+ct if k in ('method','get','set')}
  for name,mid in methods.items():
   if mid not in a.A['body']:continue
   code='\n'.join(dis(a.A,a.A['body'][mid]))
   if 'getSeason ' in code and ('gotoAndStop' in code or 'Bg' in code):
    out[cls+'.'+name]=dict(mid=mid,offset=offset,code=code)
(ROOT/'playerinfo-season-methods.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8')
(ROOT/'playerinfo-season-methods.txt').write_text('\n\n'.join(k+'\n'+v['code'] for k,v in out.items()),'utf-8')
print('\n'.join(out))
