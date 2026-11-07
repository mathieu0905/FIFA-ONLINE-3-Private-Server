from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
W=Path(__file__).parent;T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
sys.path[:0]=[str(T),r'D:\FO3ID\server\tools\re']
from avm_patch import ABC,instructions,R,u30
import bigdir
from client_patch import control_patch,popup_patch
ns={};exec((T.parents[1]/'work/grade_render_audit/build_display_fix.py').read_text('utf8').split("source=OLD/'TileList.big'")[0],ns)
report={}
for name,cname,patcher in [('TeamManagementPlayerEnhancementTabPage','EnhanceControlPanel',control_patch),('TeamManagementPlayerEnhancingPopupScreen','TeamManagementPlayerEnhancingPopupScreen',popup_patch)]:
 source=W/(name+'-baseline.big');member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
 d=(W/(name+'-baseline.swf')).read_bytes();start=8+(5+4*(d[8]>>3)+7)//8+4;parts=[];found=False
 for kind,body,raw in ns['tags'](d,start,len(d)):
  if kind==82:
   head=body.index(b'\0',4)+1;a=ABC(body[head:])
   if any(c[0]==cname for c in a.A['cls']) and '_preview' in a.A['mn'] if cname=='EnhanceControlPanel' else any(c[0]==cname for c in a.A['cls']) and 'boostInfoPanel' in a.A['mn']:
    assert not found;found=True;before=body[head:];ids=patcher(a);updated=a.output()
    (W/(name+'-before.abc')).write_bytes(before)
    (W/(name+'-ABC.patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
    b=ABC(updated);flips={}
    updated=b.output();check=ABC(updated);original=ABC(before)
    assert original.A['cls']==check.A['cls'] and original.A['sig']==check.A['sig'][:len(original.A['sig'])]
    for mid,row in original.A['body_records'].items():
     if mid not in a.changed and str(mid) not in flips:assert row['raw']==check.A['body_records'][mid]['raw']
    raw=ns['tag'](kind,body[:head]+updated)
    (W/(name+'-after.abc')).write_bytes(updated)
    meta=dict(callbacks=ids,methods=list(a.changed),embed_font_flags=flips,original_signatures_and_traits_preserved=True,all_other_methods_identical=True)
  parts.append(raw)
 assert found
 new=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new));gfx=b'CFX'+new[3:8]+zlib.compress(new[8:],9)
 target=W/(name+'.big');ns['pack_archive'](source,target,{member:gfx},[]);(W/(name+'.swf')).write_bytes(new)
 oldtags=list(ns['tags'](d,start,len(d)));newtags=list(ns['tags'](bytes(new),start,len(new)))
 assert len(oldtags)==len(newtags) and sum(x[2]!=y[2] for x,y in zip(oldtags,newtags))==1
 assert all(x[2]==y[2] for x,y in zip(oldtags,newtags) if x[0]!=82)
 oldraw=source.read_bytes();newraw=target.read_bytes();newentries=bigdir.entries(target)
 for n,o,size,u in bigdir.entries(source):
  if n==member:continue
  _,no,nsz,nu=next(e for e in newentries if e[0]==n);assert (size,u)==(nsz,nu) and oldraw[o:o+size]==newraw[no:no+nsz]
 report[name]=dict(meta,source_sha256=hashlib.sha256(oldraw).hexdigest(),sha256=hashlib.sha256(newraw).hexdigest(),all_non_abc_tags_and_other_archive_members_identical=True,native_verified=False)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
