from pathlib import Path
import sys,struct,json
W=Path(r'D:\fifaol3\probability-number-box');T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path.insert(0,str(T));s=(T/'layout_probe.py').read_text(encoding='utf-8');ns={};exec(s[s.index('class B:'):s.index("d=Path")].replace('sign and v&','sign and n and v&'),ns);B=ns['B']
def tags(data,start,end):
 while start<end:
  v=struct.unpack_from('<H',data,start)[0];start+=2;k=v>>6;l=v&63
  if l==63:l=struct.unpack_from('<I',data,start)[0];start+=4
  yield k,data[start:start+l];start+=l
  if k==0:break
for name in ('TeamManagementPlayerEnhancementTabPage','TeamManagementPlayerEnhancingPopupScreen'):
 d=(W/(name+'-baseline.swf')).read_bytes();start=8+(5+4*(d[8]>>3)+7)//8+4;report=[]
 for k,body in tags(d,start,len(d)):
  if k!=39:continue
  sid=struct.unpack_from('<H',body)[0]
  for t,b in tags(body,4,len(body)):
   if t not in (26,70):continue
   flags=b[0];flags2=b[1] if t==70 else 0;p=4 if t==70 else 3;cid=None
   if flags2&8 or (flags2&16 and flags&2):p=b.index(0,p)+1
   if flags&2:cid=struct.unpack_from('<H',b,p)[0];p+=2
   r=B(b,p*8);matrix=r.matrix() if flags&4 else None;p=r.p//8
   if flags&8:
    r=B(b,p*8);add=r.r(1);mul=r.r(1);n=r.r(4)
    if mul:[r.r(n,True) for _ in range(4)]
    if add:[r.r(n,True) for _ in range(4)]
    p=(r.p+7)//8
   if flags&16:p+=2
   field=b[p:b.index(0,p)].decode('utf-8') if flags&32 else ''
   if sid in (171,172,181,197,198) or field in ('infoPanel','controlPanel'):report.append(dict(sprite=sid,name=field,cid=cid,matrix=matrix))
 (W/(name+'-layout.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(name,json.dumps([r for r in report if 'caution' in r['name'].lower() or r['name'] in ('costLabel','textContainer','subtractESLabel')]))

