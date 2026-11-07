from client_tools import *
from entry_patch import control_patch,owner_patch,popup_patch,add_public_trait,MEMBER
report={}
for name in NAMES:
    source=W/(name+'-baseline.big');swf=(W/(name+'-baseline.swf')).read_bytes();member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
    start=8+(5+4*(swf[8]>>3)+7)//8+4;parts=[];blocks={}
    for kind,body,raw in tags(swf,start,len(swf)):
        if kind==82:
            head=body.index(b'\0',4)+1;a=ABC(body[head:]);classes={row[0] for row in a.A['cls']};selected=None
            if name==NAMES[0]:
                if 'EnhanceControlPanel' in classes and '_preview' in a.A['mn']:selected=('control',control_patch,name)
                elif 'EnhancePlayerPanel' in classes and '_players' in a.A['mn']:selected=('owner',owner_patch,'EnhancePlayerPanel')
            elif 'TeamManagementPlayerEnhancingPopupScreen' in classes and 'boostInfoPanel' in a.A['mn']:selected=('popup',popup_patch,name)
            if selected:
                key,patcher,prefix=selected;assert key not in blocks
                before=body[head:];callbacks=patcher(a)
                if key=='owner':public_name=a.name(MEMBER)
                updated=a.output()
                if key=='owner':updated=add_public_trait(updated,'EnhancePlayerPanel',public_name,callbacks['public_method_id'])
                b=ABC(updated);old=ABC(before)
                assert old.A['sig']==b.A['sig'][:len(old.A['sig'])]
                for oldrow,newrow in zip(old.A['cls'],b.A['cls']):
                    if key=='owner' and oldrow[0]=='EnhancePlayerPanel':assert oldrow[:3]==newrow[:3] and oldrow[3]==newrow[3][:-1] and oldrow[4:]==newrow[4:]
                    else:assert oldrow==newrow
                for mid,row in old.A['body_records'].items():
                    if mid not in a.changed:assert row['raw']==b.A['body_records'][mid]['raw']
                (W/(prefix+'-before.abc')).write_bytes(before);(W/(prefix+'-after.abc')).write_bytes(updated)
                (W/(prefix+'-ABC.patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf8')
                raw=tag(kind,body[:head]+updated);blocks[key]=dict(prefix=prefix,methods=sorted(a.changed),callbacks=callbacks,added_methods=list(range(len(old.A['meth']),len(b.A['meth']))))
        parts.append(raw)
    assert set(blocks)==({'control','owner'} if name==NAMES[0] else {'popup'})
    new=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new));gfx=b'CFX'+new[3:8]+zlib.compress(new[8:],9)
    target=W/(name+'.big');pack_archive(source,target,{member:gfx},[]);(W/(name+'.swf')).write_bytes(new)
    oldtags=list(tags(swf,start,len(swf)));newtags=list(tags(bytes(new),start,len(new)))
    assert len(oldtags)==len(newtags) and sum(x[2]!=y[2] for x,y in zip(oldtags,newtags))==(2 if name==NAMES[0] else 0)
    assert all(x[2]==y[2] for x,y in zip(oldtags,newtags) if x[0]!=82)
    oldraw=source.read_bytes();newraw=target.read_bytes();newentries=bigdir.entries(target)
    for n,o,length,u in bigdir.entries(source):
        if n==member:continue
        _,no,nl,nu=next(e for e in newentries if e[0]==n);assert (length,u)==(nl,nu) and oldraw[o:o+length]==newraw[no:no+nl]
    report[name]=dict(source_sha256=sha(source),sha256=sha(target),blocks=blocks,other_archive_members_preserved=True,other_methods_traits_signatures_preserved=True,native_verified=False)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
