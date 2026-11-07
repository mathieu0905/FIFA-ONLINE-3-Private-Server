from pathlib import Path
import sys,zlib,struct,json,hashlib
W=Path(r'D:\fifaol3\enhancement-progression');T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client');sys.path[:0]=[str(T),r'D:\FO3ID\server\tools\re'];sys.dont_write_bytecode=True
import bigdir
from avm_patch import ABC,u30
ns={};f=T.parents[1]/'work/grade_render_audit/build_display_fix.py';exec(f.read_text(encoding='utf-8').split("source=OLD/'TileList.big'")[0],ns)
p=Path(r'D:\FO3ID\32795\data\ui\TeamManagementPlayerEnhancingPopupScreen.big');member=next(n for n,*_ in bigdir.entries(p) if n.endswith('.gfx'));g=bigdir.read(p,member);d=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(d[8]>>3)+7)//8+4
old='保护已生效：本次强化失败，主卡保级，经验/角色保留；材料已消耗，费用已收取。不产生恢复报价。';new='本次失败已保级：经验保留、材料已消耗；按确认的普通或付费保护方案收费，无需恢复。'
needle=u30(len(old.encode()))+old.encode();replacement=u30(len(new.encode()))+new.encode();parts=[];changed=0
for kind,body,raw in ns['tags'](d,start,len(d)):
 if needle in body:
  assert kind==82 and body.count(needle)==1;head=body.index(b'\0',4)+1;a=ABC(body[head:]);updated=body.replace(needle,replacement);b=ABC(updated[head:]);assert a.A['cls']==b.A['cls'] and a.A['sig']==b.A['sig']
  assert all(row['raw']==b.A['body_records'][m]['raw'] for m,row in a.A['body_records'].items())
  raw=ns['tag'](kind,updated);changed+=1
 parts.append(raw)
assert changed==1
out=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',out,4,len(out));gfx=b'CFX'+out[3:8]+zlib.compress(out[8:],9);target=W/p.name;ns['pack_archive'](p,target,{member:gfx},[])
assert zlib.decompress(bigdir.read(target,member)[8:])==out[8:]
oldraw=p.read_bytes();newraw=target.read_bytes();entries=bigdir.entries(target)
for n,o,l,u in bigdir.entries(p):
 if n==member:continue
 _,no,nl,nu=next(e for e in entries if e[0]==n);assert (l,u)==(nl,nu) and oldraw[o:o+l]==newraw[no:no+nl]
r=dict(status='PASS',source_sha256=hashlib.sha256(oldraw).hexdigest(),sha256=hashlib.sha256(newraw).hexdigest(),only_one_existing_abc_string_changed=True,all_method_records_and_classes_identical=True,other_archive_members_identical=True,native_pass=False)
(W/'client-text.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
# Retain formal line endings for the incrementally changed source files.
S=Path(r'D:\FO3ID\server')
for n,dest in [('http_config.py','http_config.py'),('enhancement_protection40.py','enhancement_protection40.py'),('admin/index.html','index.html')]:
 raw=(S/n).read_bytes()
 if raw.count(b'\n')==raw.count(b'\r\n'):(W/dest).write_bytes((W/dest).read_text(encoding='utf-8').replace('\n','\r\n').encode('utf-8'))
