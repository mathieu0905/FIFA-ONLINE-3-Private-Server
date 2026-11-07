"""Use the client's original HTTP SQL path, removing this task's failed callback wrapper."""
from pathlib import Path
import json,struct,sys,zlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from build_names_route import ABC,tags,tag,bigdir,sha,C,S
from avm_patch import s24,instructions,dis
from build_sql_fallback import verify_server

def abc_named(d,name):
    start=8+(5+4*(d[8]>>3)+7)//8+4
    for k,b,raw in tags(d,start):
        if k==82:
            head=b.index(b'\0',4)+1;a=ABC(b[head:])
            if any(cl[0]==name for cl in a.A['cls']):return b[head:]
    raise AssertionError(name)
def build():
    prior=json.loads((ROOT/'sql-fallback-installed.json').read_text('utf8'))
    source=C/'data/ui/libs/Module.big';assert sha(source.read_bytes())==prior['hashes'][str(source).replace('/','\\')]
    member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
    g=bigdir.read(source,member);d=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(d[8]>>3)+7)//8+4
    original=ABC(abc_named((ROOT/'current-Module.swf').read_bytes(),'SQLConnection'))
    parts=[];proof=None
    for k,b,raw in tags(d,start):
        if k==82:
            head=b.index(b'\0',4)+1;current=ABC(b[head:])
            classes=[cl for cl in current.A['cls'] if cl[0]=='SQLConnection']
            if classes:
                mid=next(v for kind,name,v in classes[0][3]+classes[0][5] if kind=='method' and name=='execute')
                assert current.A['cls']==original.A['cls'] and current.A['sig'][:len(original.A['sig'])]==original.A['sig']
                assert len(current.A['meth'])==len(original.A['meth'])+1
                for i,row in original.A['body_records'].items():
                    if i!=mid:assert current.A['body_records'][i]['raw']==row['raw']
                code=original.A['body'][mid]
                assert code[25]==0x5d and code[64]==0x5d and code[94]==0x5d
                # Jump over the backend-type selection into the original, shipped HTTP path.
                # Four inserted bytes shift the target from 64 to 68; relative delta is 39.
                original.modify(mid,{25:b'\x10'+s24(39)})
                updated=original.output();check=ABC(updated);newcode=check.A['body'][mid]
                decoded=list(instructions(newcode));jump=next(x for x in decoded if x[0]==25)
                assert jump[2]==0x10 and jump[3]==[68]
                assert newcode[68:98]==code[64:94]
                assert check.A['cls']==original.A['cls'] and check.A['sig']==original.A['sig']
                assert len(check.A['meth'])==len(original.A['meth'])
                for i,row in original.A['body_records'].items():
                    if i!=mid:assert row['raw']==check.A['body_records'][i]['raw']
                raw=tag(k,b[:head]+updated)
                proof=dict(method=mid,added_methods=0,failed_wrapper_removed=True,dispatch_jump=jump,
                    shipped_http_instructions_unchanged=True,shipped_response_callback_unchanged=True,
                    signatures_and_traits_preserved=True,disassembly=dis(check.A,newcode))
        parts.append(raw)
    assert proof
    new=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new));gfx=b'CFX'+new[3:8]+zlib.compress(new[8:],9)
    out=ROOT/'sql-http-Module.big';out.write_bytes(source.read_bytes());bigdir.patch(out,{member:gfx})
    assert bigdir.read(out,member)==gfx
    oldtags=list(tags(d,start));newtags=list(tags(new,start));assert len(oldtags)==len(newtags)
    assert sum(a[2]!=b[2] for a,b in zip(oldtags,newtags))==1
    report=dict(status='PREPARED_ORIGINAL_HTTP_SQL_PATH',target=str(source),before_sha256=sha(source.read_bytes()),payload=str(out),after_sha256=sha(out.read_bytes()),proof=proof,server_checks=verify_server(),formal_written=False,native_verified=False)
    (ROOT/'sql-http-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(status=report['status'],added_callbacks=0,old_http_callback_retained=True)))
    return report
if __name__=='__main__':build()
