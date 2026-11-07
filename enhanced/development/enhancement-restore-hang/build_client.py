"""Fix callback receivers and pre-pushscope restore guards on current resources."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
W=Path(__file__).parent;T=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
sys.path[:0]=[str(T),r'D:\FO3ID\server\tools\re']
from avm_patch import ABC,Code,R,instructions
import bigdir
ns={};exec((T.parents[1]/'work/grade_render_audit/build_display_fix.py').read_text('utf8').split("source=OLD/'TileList.big'")[0],ns)
report={}
for name,cname in [('TeamManagementPlayerEnhancementTabPage','EnhanceControlPanel'),('TeamManagementPlayerEnhancingPopupScreen','TeamManagementPlayerEnhancingPopupScreen')]:
 source=W/(name+'-baseline.big');member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'));d=(W/(name+'-baseline.swf')).read_bytes()
 start=8+(5+4*(d[8]>>3)+7)//8+4;parts=[];found=False
 for kind,body,raw in ns['tags'](d,start,len(d)):
  if kind==82:
   head=body.index(b'\0',4)+1;a=ABC(body[head:])
   if any(row[0]==cname for row in a.A['cls']) and ('_preview' if name.endswith('TabPage') else 'boostInfoPanel') in a.A['mn']:
    assert not found;found=True;changed={}
    (W/(name+'-before.abc')).write_bytes(body[head:])
    if name.endswith('TabPage'):
     # Current official callback already uses event.currentTarget; retain it exactly.
     assert b'fo3RememberProtection' in body
    else:
     for mid,native_at in ((46,43),(48,22)):
      original=a.A['body'][mid]
      assert original[0]==0x5d and original[native_at]==0xd0
      native=original[native_at:]
      # Original relative native branches remain exact after stripping a prefix.
      assert all(t>=native_at for at,e,op,ts in instructions(original) if at>=native_at for t in (ts or []))
      c=Code(a).local(0).ownprop('_restorePlayerData').jump(0x12,'native')
      if mid==46:
       c.local(0).ownprop('_restorePlayerData').prop('restoreSpaceState').string('pending').jump(0x13,'skip')
       c.local(0).ownprop('_restorePlayerData').prop('restoreSpaceState').string('done').jump(0x14,'native')
       c.label('skip').op(0x47)
      else:c.local(0).ownprop('_restorePlayerData').string('done').set('restoreSpaceState')
      c.label('native');a.A['body'][mid]=native;a.modify(mid,{0:c.done()})
      changed[str(mid)]=dict(reason='Instance receiver is not yet on lexical scope before native pushscope',old_prefix_bytes=native_at,old_prefix=original[:native_at].hex())
     # v2.5's first Restore is a visual reveal of the already-saved grade.
     # Expand that actual card once; never loop through +0..N or call paid APIs.
     mid=47;base=a.A['body_records'][mid]['fields'][1]
     c=Code(a).local(0).ownprop('_version').string('v2_5').jump(0x14,'native')
     c.local(0).ownprop('_result').jump(0x12,'native')
     c.local(0).ownprop('_result').prop('resultgrade').store(base)
     c.local(base).op(0x95).string('number').jump(0x14,'native')
     c.op(0x5d,a.name('isFinite')).local(base).call('isFinite',1).jump(0x12,'native')
     c.local(base).number(0).op(0xad).jump(0x11,'native');c.local(base).number(20).op(0xaf).jump(0x11,'native')
     c.local(0).ownprop('_restoreButton').op(0x27).set('enabled')
     c.local(0).local(base).ownset('_restoreCount')
     c.local(0).op(0x60,a.own('ObjectUtil')).local(0).ownprop('_data').prop('firstPlayer').call('deepCopy',1).ownset('_restorePlayerData')
     c.local(0).ownprop('_restorePlayerData').op(0x60,a.own('ObjectUtil')).local(0).ownprop('_data').prop('info').prop('levelinfo').call('deepCopy',1).set('levelinfo')
     c.local(0).ownprop('_restorePlayerData').local(base).set('grade')
     c.local(0).ownprop('_restorePlayerData').string('pending').set('restoreSpaceState')
     c.local(0).ownprop('_restorePlayerData').op(0x21).set('staticdata')
     c.local(0).ownprop('container').call('stop',0).op(0x29)
     c.op(0x60,a.own('PlayerListUtil')).local(0).ownprop('_restorePlayerData').op(0x40,61).call('expandPlayerStaticData',2).op(0x29).op(0x47)
     c.label('native');assert a.A['body'][mid][:2]==b'\xd0\x30'
     a.modify(mid,{2:c.done()},locals_extra=1)
     changed[str(mid)]=dict(reason='One visual refresh to the real server result, zero paid recovery requests',inserted_after_native_pushscope=True)
    updated=a.output();b=ABC(updated);before=ABC(body[head:])
    assert before.A['cls']==b.A['cls'] and before.A['sig']==b.A['sig'] and before.A['meth']==b.A['meth']
    for mid,row in before.A['body_records'].items():
     if mid not in a.changed:assert row['raw']==b.A['body_records'][mid]['raw']
    (W/(name+'-after.abc')).write_bytes(updated)
    (W/(name+'-ABC.patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
    raw=ns['tag'](kind,body[:head]+updated)
  parts.append(raw)
 assert found
 new=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new));gfx=b'CFX'+new[3:8]+zlib.compress(new[8:],9)
 target=W/(name+'.big');ns['pack_archive'](source,target,{member:gfx},[]);(W/(name+'.swf')).write_bytes(new)
 oldtags=list(ns['tags'](d,start,len(d)));newtags=list(ns['tags'](bytes(new),start,len(new)))
 assert len(oldtags)==len(newtags) and sum(x[2]!=y[2] for x,y in zip(oldtags,newtags))==bool(changed)
 assert all(x[2]==y[2] for x,y in zip(oldtags,newtags) if x[0]!=82)
 oldraw=source.read_bytes()
 if not changed:target.write_bytes(oldraw)
 newraw=target.read_bytes();entries=bigdir.entries(target)
 for n,o,size,u in bigdir.entries(source):
  if n==member:continue
  _,no,nsz,nu=next(e for e in entries if e[0]==n);assert (size,u)==(nsz,nu) and oldraw[o:o+size]==newraw[no:no+nsz]
 report[name]=dict(source_sha256=hashlib.sha256(oldraw).hexdigest(),sha256=hashlib.sha256(newraw).hexdigest(),changes=changed,other_methods_and_traits_identical=True,other_tags_and_members_identical=True,native_verified=False)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
