"""Use the client's registered embedded font for all added enhancement fields."""
from pathlib import Path
import sys,zlib,struct,json,hashlib
sys.dont_write_bytecode=True
W=Path(__file__).parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
sys.path[:0]=[str(T),str(S/'tools/re')]
from avm_patch import ABC,instructions,u30,R
import bigdir
ns={};f=T.parents[1]/'work/grade_render_audit/build_display_fix.py';exec(f.read_text('utf8').split("source=OLD/'TileList.big'")[0],ns)
report={}
for name,cname in [('TeamManagementPlayerEnhancementTabPage','EnhanceControlPanel'),('TeamManagementPlayerEnhancingPopupScreen','TeamManagementPlayerEnhancingPopupScreen')]:
 source=C/'data/ui'/(name+'.big');(W/(name+'-baseline.big')).write_bytes(source.read_bytes())
 member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'));g=bigdir.read(source,member);d=b'FWS'+g[3:8]+zlib.decompress(g[8:])
 start=8+(5+4*(d[8]>>3)+7)//8+4;parts=[];found=False
 for kind,body,raw in ns['tags'](d,start,len(d)):
  if kind==82:
   head=body.index(b'\0',4)+1;a=ABC(body[head:])
   if any(c[0]==cname for c in a.A['cls']) and 'Microsoft YaHei' in a.values[3]:
    assert not found;found=True;original=body[head:];(W/(name+'-before.abc')).write_bytes(original)
    # Rebuild only the string pool, retaining every existing constant index.
    begin,count,entries,end=a.pools[3];values=list(a.values[3]);replaced=[]
    for i,value in enumerate(values):
     if value in ('Arial','Microsoft YaHei'):
      replaced.append(dict(index=i,before=value,after='$NormalFont'));values[i]='$NormalFont'
    pool=u30(count)+b''.join(u30(len(v.encode('utf8')))+v.encode('utf8') for v in values[1:])
    a=ABC(original[:begin]+pool+original[end:]);changed={}
    for mid,code in a.A['body'].items():
     rows=list(instructions(code));new=bytearray(code);flips=[]
     for j,(at,e,op,_) in enumerate(rows):
      if op not in (0x61,0x68):continue
      r=R(code,at+1);mn=r.u30()
      if a.A['mn'][mn]!='embedFonts':continue
      prior=rows[j-1]
      if prior[2]==0x27:
       assert prior[1]==at;new[prior[0]]=0x26;flips.append(prior[0])
     if flips:
      record=a.A['body_records'][mid]
      a.changed[mid]=u30(mid)+b''.join(u30(v) for v in record['fields'])+u30(len(new))+bytes(new)+record['suffix']
      changed[str(mid)]=flips
    updated=a.output();check=ABC(updated);before=ABC(original)
    assert check.A['cls']==before.A['cls'] and check.A['sig']==before.A['sig'] and check.A['meth']==before.A['meth']
    for mid,code in before.A['body'].items():
     actual=check.A['body'][mid];allowed=set(changed.get(str(mid),[]));assert len(actual)==len(code)
     assert all((old==new) if i not in allowed else (old,new)==(0x27,0x26) for i,(old,new) in enumerate(zip(code,actual)))
    assert not {'Arial','Microsoft YaHei'} & set(check.values[3])
    button_changes={}
    if cname=='EnhanceControlPanel':
     from button_patch import patch
     a=ABC(updated);patch(a);updated=a.output();button_changes=a.insertions
    (W/(name+'-button.patch.json')).write_text(json.dumps(button_changes,indent=2),encoding='utf8')
    (W/(name+'-after.abc')).write_bytes(updated)
    raw=ns['tag'](kind,body[:head]+updated)
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
 report[name]=dict(source_sha256=hashlib.sha256(oldraw).hexdigest(),sha256=hashlib.sha256(newraw).hexdigest(),
  font_constants=replaced,embed_font_flags=changed,button_state_methods=list(button_changes),only_font_flags_and_button_state_injections=True,traits_and_signatures_identical=True,non_abc_and_other_members_identical=True,native_verified=False)
(W/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
