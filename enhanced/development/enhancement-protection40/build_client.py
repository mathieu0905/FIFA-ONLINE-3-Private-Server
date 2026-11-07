from pathlib import Path
import sys, json, hashlib, struct, zlib
sys.dont_write_bytecode=True
W=Path(r'D:\fifaol3\enhancement-protection40')
ORIG=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online')
T=ORIG/'work/bp_client'
sys.path[:0]=[str(T),r'D:\FO3ID\server\tools\re']
import bigdir
from avm_patch import ABC,parse,dis
s=(T/'build_bp_client.py').read_text(encoding='utf-8')
s=s[:s.index('def build():')]
s=s.replace("W=Path(__file__).resolve().parents[2];OUT=W/'outputs/FO3ID/BP保级保护客户端'", "W=Path(r'"+str(ORIG)+"');OUT=Path(r'"+str(W)+"')")
s=s.replace('BP保级保护','强化保护（40%身价）')
ns={'__file__':str(T/'build_bp_client.py')};exec(compile(s,'<existing-client-patch-definitions>','exec'),ns)
report={}
for name, cname, patcher in [('TeamManagementPlayerEnhancementTabPage','EnhanceControlPanel',ns['control_patch']),('TeamManagementPlayerEnhancingPopupScreen','TeamManagementPlayerEnhancingPopupScreen',ns['popup_patch'])]:
    source=Path(r'D:\FO3ID\32795\data\ui')/(name+'.big')
    member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
    g=bigdir.read(source,member);d=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(d[8]>>3)+7)//8+4
    parts=[];found=False
    for kind,body,raw in ns['tags'](d,start,len(d)):
        if kind==82:
            head=body.index(b'\0',4)+1
            a=ABC(body[head:])
            if d.find(body)+head == (0x246ff if name=='TeamManagementPlayerEnhancementTabPage' else 0x929ae):
                assert not found
                found=True
                (W/(name+'-before.abc')).write_bytes(body[head:])
                ids=patcher(a);updated=a.output();b=ABC(updated)
                assert a.A['cls']==b.A['cls'] and a.A['sig']==b.A['sig'][:len(a.A['sig'])]
                for mid,row in a.A['body_records'].items():
                    if mid not in a.changed:assert row['raw']==b.A['body_records'][mid]['raw']
                    else:assert row['suffix']==b.A['body_records'][mid]['suffix']
                raw=ns['tag'](kind,body[:head]+updated)
                (W/(name+'-ABC.patch.json')).write_text(json.dumps(a.insertions,indent=2),encoding='utf-8')
                (W/(name+'-after.abc')).write_bytes(updated)
                report[name]={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'changed_methods':sorted(a.changed),'added_methods':ids,'original_class_traits_and_method_signatures_preserved':True,'all_other_method_records_unchanged':True}
        parts.append(raw)
    assert found,(name,cname)
    target=W/(name+'.big');new=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new))
    gfx=b'CFX'+new[3:8]+zlib.compress(new[8:],9)
    ns['pack_archive'](source,target,{member:gfx},[])
    (W/(name+'.swf')).write_bytes(new)
    oldtags=list(ns['tags'](d,start,len(d)));newtags=list(ns['tags'](bytes(new),start,len(new)))
    assert len(oldtags)==len(newtags)
    assert sum(aa[2]!=bb[2] for aa,bb in zip(oldtags,newtags))==1
    assert all(aa[2]==bb[2] for aa,bb in zip(oldtags,newtags) if aa[0]!=82)
    oldraw=source.read_bytes();newraw=target.read_bytes();entries=bigdir.entries(target)
    for n,o,l,u in bigdir.entries(source):
        if n==member:continue
        _,no,nl,nu=next(e for e in entries if e[0]==n)
        assert (l,u)==(nl,nu) and oldraw[o:o+l]==newraw[no:no+nl]
    report[name].update(sha256=hashlib.sha256(newraw).hexdigest(),non_abc_tags_and_other_archive_members_unchanged=True,native_pass=False)
(W/'client-build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
