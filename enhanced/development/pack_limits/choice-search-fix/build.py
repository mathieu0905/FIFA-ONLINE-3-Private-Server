from pathlib import Path
import hashlib,json,struct,sys,zlib
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path[:0]=[str(S/'tools/re'),r'D:\fifaol3\season-display',r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\experience_levels']
from avm_patch import ABC,R as Reader,u30,dis
from build_moments_display import tags,tag,replace_ui_member
import bigdir
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=C/'data/ui/TeamManagementDraftPackScreen.big';before_hash=sha(source)
member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'));gfx=bigdir.read(source,member)
plain=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]);start=8+(5+4*(plain[8]>>3)+7)//8+4
out=bytearray(plain[:start]);changed=0
for kind,body,raw in tags(plain,start):
    if kind!=82:out+=raw;continue
    at=body.index(b'\0',4)+1;data=body[at:];a=ABC(data)
    if not any(c[0]=='TeamManagementDraftPackScreen' for c in a.A['cls']):out+=raw;continue
    assert len(a.A['meth'])==70 and a.A['sig'][68]==[65] and a.A['mn'][65]=='Object'
    assert 'newfunction 68' in '\n'.join(dis(a.A,a.A['body'][69]))
    assert 'expandPlayersStaticData (2)' in '\n'.join(dis(a.A,a.A['body'][69]))
    r=Reader(data,a.A['method_entries_pos']);entries=[]
    for mid in range(len(a.A['meth'])):
        begin=r.p;pc=r.u30();ret=r.u30();params=[r.u30() for _ in range(pc)];name=r.u30();flags=r.u8()
        if flags&8:
            for _ in range(r.u30()):r.u30();r.u8()
        if flags&128:
            for _ in range(pc):r.u30()
        entries.append(data[begin:r.p])
        if mid==68:
            assert pc==1 and params==[65] and name==0 and flags==0
            replace=(begin,r.p,u30(0)+u30(ret)+u30(name)+bytes([flags]))
    begin,end,replacement=replace;new=data[:begin]+replacement+data[end:];b=ABC(new)
    assert b.A['sig'][68]==[] and all(b.A['sig'][i]==a.A['sig'][i] for i in range(70) if i!=68)
    assert b.values==a.values and b.A['cls']==a.A['cls']
    assert all(b.A['body_records'][i]['raw']==v['raw'] for i,v in a.A['body_records'].items())
    assert new[:begin]==data[:begin] and new[begin+len(replacement):]==data[end:]
    (R/'before.abc').write_bytes(data);(R/'after.abc').write_bytes(new)
    target_body=body;out+=tag(kind,body[:at]+new);changed+=1
assert changed==1
swf=bytes(out);swf=swf[:4]+struct.pack('<I',len(swf))+swf[8:]
updated=b'CFX'+gfx[3:4]+struct.pack('<I',len(swf))+zlib.compress(swf[8:],9)
target=R/source.name;replace_ui_member(source,target,member,updated,bigdir)
assert sha(source)==before_hash and bigdir.read(target,member)==updated
oldtags=list(tags(plain,start));newtags=list(tags(swf,start));assert len(oldtags)==len(newtags)
assert all(x[2]==y[2] for x,y in zip(oldtags,newtags) if x[0]!=82 or x[1]!=target_body)
report=dict(status='PASS',source=str(source),source_sha256=before_hash,target_sha256=sha(target),method=68,old_required_parameters=1,new_required_parameters=0,all_method_bodies_exact=True,other_signatures_exact=True,constant_pools_and_traits_exact=True,server_changed=False,native_verified=False)
(R/'build-results.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
