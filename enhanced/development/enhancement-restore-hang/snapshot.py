from pathlib import Path
import sys,zlib,struct,json,hashlib
sys.dont_write_bytecode=True
W=Path(r'D:\fifaol3\enhancement-restore-hang');T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path[:0]=[str(T),r'D:\FO3ID\server\tools\re']
import bigdir
from avm_patch import ABC,dis
# Read-only snapshot of the exact running installation for byte-level analysis.
report={}
for name in ('TeamManagementPlayerEnhancementTabPage','TeamManagementPlayerEnhancingPopupScreen'):
 p=Path(r'D:\FO3ID\32795\data\ui')/(name+'.big');raw=p.read_bytes();(W/(name+'-baseline.big')).write_bytes(raw)
 member=next(n for n,*_ in bigdir.entries(p) if n.endswith('.gfx'));g=bigdir.read(p,member);d=b'FWS'+g[3:8]+zlib.decompress(g[8:]);(W/(name+'-baseline.swf')).write_bytes(d)
 at=8+(5+4*(d[8]>>3)+7)//8+4;rows=[];classes=[]
 while at<len(d):
  n=struct.unpack_from('<H',d,at)[0];at+=2;k=n>>6;l=n&63
  if l==63:l=struct.unpack_from('<I',d,at)[0];at+=4
  b=d[at:at+l]
  if k==82:
   head=b.index(b'\0',4)+1;a=ABC(b[head:]);offset=at+head
   for cname,sup,ii,it,ci,ct in a.A['cls']:
    if any(word in cname for word in ('Enhance','Enhancing')):
     classes.append(dict(offset=offset,name=cname,methods=[t for t in it+ct if t[0] in ('method','get','set')]))
     for kind,key,mid in [('ctor','ctor',ii)]+[t for t in it+ct if t[0] in ('method','get','set')]:
      if mid in a.A['body']:rows.append(f'ABC {offset:#x} method {mid} {cname}.{key}\n'+'\n'.join(dis(a.A,a.A['body'][mid])))
  at+=l
 (W/(name+'-baseline.txt')).write_text('\n\n'.join(rows),encoding='utf-8');report[name]=dict(source=str(p),sha256=hashlib.sha256(raw).hexdigest(),member=member,classes=classes)
(W/'source-evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('Read current source snapshots and exact class/method inventories')



