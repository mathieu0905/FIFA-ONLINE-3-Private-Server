from pathlib import Path
import hashlib,json,shutil,struct,sys,zlib
sys.dont_write_bytecode=True
from build_compact_label import ABC,Code,tags,tag,parse,bigdir
import test_native as tests
R=Path(__file__).resolve().parent;O=R/'screen-currency';(O/'payload').mkdir(parents=True,exist_ok=True)
inventory=json.loads((R/'native/comma-inventory.json').read_text(encoding='utf-8'));assert not inventory['errors'] and len(inventory['definitions'])==3
records=[]
for entry in inventory['definitions']:
    source=Path(entry['file']);assert hashlib.sha256(source.read_bytes()).hexdigest()==entry['source_sha256']
    member=entry['member'];gfx=bigdir.read(source,member);swf=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:])
    parts=[];first=None;matched=False
    for at,pos,end,k in tags(swf):
        if first is None:first=at
        raw=swf[at:end]
        if k==82:
            payload=swf[pos:end];off=payload.index(b'\0',4)+1;a=ABC(payload[off:])
            if any(c[0]==entry['class_name'] for c in a.A['cls']):
                mi=entry['method'];old=a.A['body'][mi];assert old[:2]==b'\xd0\x30'
                local=a.A['body_records'][mi]['fields'][1]
                c=Code(a).op(0x5d,a.name('Number')).local(1).call('Number',1).store(local)
                c.lex('Math').local(local).call('abs',1).number(10000).op(0xb0).jump(0x12,'small')
                c.lex('StringUtil','fok.utils').local(local).call('formatToCurrency',1).op(0x48).label('small')
                a.modify(mi,{2:c.done()},locals_extra=1);abc=a.output();raw=tag(k,payload[:off]+abc);new=ABC(abc)
                stack=tests.namespace['check'](new,mi)
                for n,expected in [(0,'0'),(9999,'9,999'),(10000,'1万'),(10**8,'1亿'),(10**12,'1兆'),(10**16,'1京'),(10**18,'100京')]:
                    assert tests.run(str(n),currency=True,program=(new,mi))==expected,(source,n)
                matched=True
        parts.append(raw)
    assert matched
    out=bytearray(swf[:first]+b''.join(parts));struct.pack_into('<I',out,4,len(out))
    target=O/'payload'/source.name;shutil.copyfile(source,target)
    bigdir.patch(target,{member:b'CFX'+gfx[3:4]+struct.pack('<I',len(out))+zlib.compress(out[8:],9)})
    assert zlib.decompress(bigdir.read(target,member)[8:])==out[8:]
    original=source.read_bytes();updated=target.read_bytes();table={n:(o,s,u) for n,o,s,u in bigdir.entries(target)}
    for n,o,s,u in bigdir.entries(source):
        if n==member:continue
        no,ns,nu=table[n];assert original[o:o+s]==updated[no:no+ns] and u==nu
    records.append(dict(source=str(source),source_sha256=entry['source_sha256'],sha256=hashlib.sha256(updated).hexdigest(),
        class_name=entry['class_name'],method=mi,stack=stack,small_number_behavior_preserved=True,other_methods_identical=True,other_archive_members_identical=True))
report=dict(status='PASS_NATIVE_PENDING',inventory_gfx=inventory['scanned_gfx'],records=records)
(O/'build-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True,indent=2))
