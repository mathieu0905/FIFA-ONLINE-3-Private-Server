"""Prepare one Module delta using the existing main DB's localized name tables."""
from pathlib import Path
import hashlib, importlib.util, json, sqlite3, struct, sys, zlib
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parent
S=Path('D:/FO3ID/server'); C=Path('D:/FO3ID/32795')
sys.path[:0]=['D:/FO3ID/server/tools/re', 'D:/FO3ID/server', 'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/bp_client']
import bigdir, extract_fifadb
from avm_patch import ABC, Code, instructions, R

def sha(b): return hashlib.sha256(b).hexdigest()
def tags(d,at):
    while at<len(d):
        start=at;h=struct.unpack_from('<H',d,at)[0];at+=2;k,n=h>>6,h&63
        if n==63:n=struct.unpack_from('<I',d,at)[0];at+=4
        yield k,d[at:at+n],d[start:at+n]
        at+=n
        if k==0:break
def tag(k,b):return struct.pack('<HI',(k<<6)|63,len(b))+b

def run_prefix(a,code,db,query):
    """Execute the produced AVM2 prefix, including its actual branch offsets."""
    r=R(code,0);stack=[];locals_={1:db,2:query};high=0
    while r.p<len(code):
        op=r.u8()
        if op==0x2c:stack.append(a.values[3][r.u30()])
        elif op==0x62:stack.append(locals_[r.u30()])
        elif op==0x63:locals_[r.u30()]=stack.pop()
        elif op==0x24:stack.append(r.u8())
        elif op==0x56:
            n=r.u30();vals=stack[-n:];del stack[-n:];stack.append(vals)
        elif op==0x46:
            name=a.values[3][a.values[6][r.u30()][2]];n=r.u30();args=stack[-n:];del stack[-n:];obj=stack.pop()
            if name=='indexOf':
                try:v=obj.index(args[0]) if isinstance(obj,list) else obj.find(args[0])
                except ValueError:v=-1
            elif name=='split':v=obj.split(args[0])
            elif name=='join':v=args[0].join(obj)
            else:raise AssertionError(name)
            stack.append(v)
        elif op==0xa0:b=stack.pop();stack.append(stack.pop()+b)
        elif op==0x15:
            delta=r.s24();b=stack.pop();v=stack.pop()
            if v<b:r.p+=delta
        else:raise AssertionError(hex(op))
        high=max(high,len(stack))
    assert not stack
    return locals_[1],locals_[2],high

def build():
    source=C/'data/ui/libs/Module.big';member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
    g=bigdir.read(source,member);d=b'FWS'+g[3:8]+zlib.decompress(g[8:])
    start=8+(5+4*(d[8]>>3)+7)//8+4
    proof=[];parts=[];changed=0
    for k,b,raw in tags(d,start):
        if k==82:
            head=b.index(b'\0',4)+1;a=ABC(b[head:])
            target=[x for x in a.A['cls'] if x[0]=='ConnectionPool']
            if target:
                assert len(target)==1
                _,_,_,it,_,ct=target[0]
                mid=next(v for kind,name,v in it+ct if kind=='method' and name=='execute')
                p=Code(a)
                for lang in ('eng','chi','tha','vie','ind'):p.string(lang)
                p.op(0x56,5).local(1).call('indexOf',1).raw(b'\x24\x00').jump(0x15,'done')
                p.local(2).string('FROM names ').call('indexOf',1).raw(b'\x24\x00').jump(0x15,'done')
                p.local(2).string('FROM names ').call('split',1)
                p.string('FROM names').local(1).op(0xa0).string(' ').op(0xa0).call('join',1).store(2)
                p.string('fifadb').store(1).label('done')
                prefix=p.done();a.modify(mid,{0:prefix});updated=a.output();check=ABC(updated)
                assert a.A['cls']==check.A['cls'] and a.A['sig']==check.A['sig']
                for i,row in a.A['body_records'].items():
                    if i!=mid:assert row['raw']==check.A['body_records'][i]['raw']
                assert a.A['body_records'][mid]['suffix']==check.A['body_records'][mid]['suffix']
                db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
                cases=[]
                for lang in ('eng','chi','tha','vie','ind'):
                    plain=bytes(extract_fifadb.decrypt(bigdir.read(C/'data/data_0.big',f'data/db2/{lang}.db.db2')))
                    loc=sqlite3.connect(':memory:');loc.deserialize(b'SQLite format 3\0'+plain[16:])
                    original=loc.execute('SELECT * FROM names ORDER BY playerid').fetchall()
                    rewritten=db.execute('SELECT * FROM names'+lang+' ORDER BY playerid').fetchall()
                    assert original==rewritten,(lang,'name table rows differ')
                    for query in ('SELECT * FROM names WHERE playerid IN (252371,231747,5740)', 'SELECT short FROM names WHERE playerid=252371'):
                        dest,q,maxstack=run_prefix(a,prefix,lang,query)
                        assert dest=='fifadb' and loc.execute(query).fetchall()==db.execute(q).fetchall()
                        cases.append(dict(language=lang,original=query,database=dest,query=q,max_stack=maxstack))
                    cases.append(dict(language=lang,all_rows_identical=len(original)))
                for name,query in [('fifadb','SELECT * FROM players WHERE spid=13252371'),('chi','SELECT * FROM team'),('kor','SELECT * FROM names WHERE playerid=1'),('unknown','SELECT * FROM names WHERE playerid=1')]:
                    dest,q,maximum=run_prefix(a,prefix,name,query);assert (dest,q)==(name,query)
                    cases.append(dict(unchanged_database=name,query=q,max_stack=maximum))
                # Keep the observed failure mode as a precise regression input.
                empty=sqlite3.connect(':memory:')
                try:empty.execute('SELECT * FROM names WHERE playerid=252371')
                except sqlite3.OperationalError as error:assert str(error)=='no such table: names'
                else:raise AssertionError('Missing-table control failed')
                raw=tag(k,b[:head]+updated);changed+=1
                proof.append(dict(class_name='ConnectionPool',method=mid,checks=cases,prefix=prefix.hex(),
                    signatures_traits_and_other_method_records_preserved=True,original_method_suffix_preserved=True))
        parts.append(raw)
    assert changed==1
    new=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new))
    gfx=b'CFX'+new[3:8]+zlib.compress(new[8:],9)
    # Local payload only. This archive has one gfx member; preserve all other raw members.
    output=ROOT/'names-route-Module.big';output.write_bytes(source.read_bytes());bigdir.patch(output,{member:gfx})
    assert bigdir.read(output,member)==gfx
    for name,off,size,usize in bigdir.entries(source):
        if name!=member:assert bigdir.read(output,name)==bigdir.read(source,name)
    oldtags=list(tags(d,start));newtags=list(tags(new,start));assert len(oldtags)==len(newtags)
    assert sum(x[2]!=y[2] for x,y in zip(oldtags,newtags))==1
    report=dict(status='PREPARED_NOT_INSTALLED',target=str(source),before_sha256=sha(source.read_bytes()),
        payload=str(output),after_sha256=sha(output.read_bytes()),proof=proof,
        scope='Route only known-language FROM names queries to equivalent localized tables in fifadb. Preserve other queries.',
        native_verified=False,model_crash_fixed=False,formal_written=False)
    (ROOT/'names-route-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='proof'}))
if __name__=='__main__':build()
