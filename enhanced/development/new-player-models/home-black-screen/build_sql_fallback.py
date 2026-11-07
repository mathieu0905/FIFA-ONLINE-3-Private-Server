"""Prepare and replay a native-error-only fallback using the shipped HTTP SQL callback."""
from pathlib import Path
import json, struct, sys, zlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from build_names_route import ABC,Code,R,tags,tag,bigdir,sha,C,S
from avm_patch import u30
from native_sql_fallback import Reader

def replay(a,code,database,query,data,error):
    requests=[];callbacks=[];stack=[];locals_={0:None,1:data,2:error};r=R(code,0)
    def post(*args):requests.append(args)
    def callback(*args):callbacks.append(args)
    env={'_database':database,'sql':query,'callback':callback,'ResourceController':{'instance':{'POST':post}}}
    def name(i):return a.values[3][a.values[6][i][2]]
    high=0
    while r.p<len(code):
        op=r.u8()
        if op==0x62:stack.append(locals_[r.u30()])
        elif op==0x12:
            off=r.s24()
            if not stack.pop():r.p+=off
        elif op==0x5d:r.u30();stack.append(env)
        elif op==0x66:stack.append(stack.pop()[name(r.u30())])
        elif op==0x2c:stack.append(a.values[3][r.u30()])
        elif op==0xa0:b=stack.pop();stack.append(stack.pop()+b)
        elif op==0x55:
            n=r.u30();obj={}
            for _ in range(n):v=stack.pop();obj[stack.pop()]=v
            stack.append(obj)
        elif op==0x40:stack.append(('shipped_callback',r.u30()))
        elif op in (0x46,0x4c):
            prop=name(r.u30());n=r.u30();args=stack[-n:];del stack[-n:];obj=stack.pop();stack.append(obj[prop](*args))
        elif op==0x29:stack.pop()
        elif op==0x47:break
        else:raise AssertionError(hex(op))
        high=max(high,len(stack))
    assert not stack
    return dict(requests=requests,callbacks=callbacks,max_stack=high)

def verify_server():
    reader=Reader(S,C);checks=[]
    for lang in ('kor','eng','chi','tha','vie','ind'):
        rows=reader.query(lang,'SELECT playerid,full,short FROM names WHERE playerid=252371')
        assert rows and rows[0]['playerid']==252371
        checks.append(dict(database=lang,rows=rows))
    for query in ['SELECT * FROM players WHERE spid IN (13252371,91005479)',
                  'SELECT * FROM nameschi WHERE playerid IN (252371,5740)',
                  'SELECT * FROM playerhistory WHERE playerid=252371 ORDER BY ordernum DESC']:
        rows=reader.query('fifadb',query);assert rows
        checks.append(dict(database='fifadb',query=query,rows=len(rows)))
    for query in ["DELETE FROM players", "UPDATE players SET overallrating=1", "ATTACH DATABASE ':memory:' AS x", 'PRAGMA writable_schema=ON', 'CREATE TABLE broken(x)', "SELECT load_extension('x')",'SELECT 1; SELECT 2']:
        try:reader.query('fifadb',query)
        except Exception as error:checks.append(dict(rejected=query,error=str(error)))
        else:raise AssertionError('Unsafe SQL accepted: '+query)
    assert reader.query('fifadb','SELECT count(*) AS n FROM players')[0]['n']>60000
    return checks

def build():
    server_checks=verify_server()
    source=C/'data/ui/libs/Module.big';member=next(n for n,*_ in bigdir.entries(source) if n.endswith('.gfx'))
    g=bigdir.read(source,member);d=b'FWS'+g[3:8]+zlib.decompress(g[8:]);start=8+(5+4*(d[8]>>3)+7)//8+4
    parts=[];changes=[]
    for kind,b,raw in tags(d,start):
        if kind==82:
            head=b.index(b'\0',4)+1;a=ABC(b[head:]);cl=[x for x in a.A['cls'] if x[0]=='SQLConnection']
            if cl:
                assert len(cl)==1
                mid=next(v for kind_,name,v in cl[0][3]+cl[0][5] if kind_=='method' and name=='execute')
                original=a.A['body'][mid]
                assert original[111]==0x46 and original[107:111]==bytes([0x65,1,0x6c,2]),'Native callback layout changed'
                p=Code(a)
                p.local(2).jump(0x12,'native_ok')
                p.find('ResourceController').ownprop('ResourceController').prop('instance')
                p.string('/static/sql/').find('_database').ownprop('_database').op(0xa0)
                p.string('sql').find('sql').ownprop('sql').op(0x55,1).op(0x40,7).call('POST',3).op(0x29).op(0x47)
                p.label('native_ok').find('callback').local(1).local(2).op(0x4c,a.own('callback'),2).op(0x29).op(0x47)
                code=p.done();scope=a.A['body_records'][7]['fields'][2]
                newmid=a.add_method(code,scope,local_count=3)
                signature=u30(2)+u30(a.name('void'))+u30(a.name('Object'))+u30(a.name('String'))+b'\0\0'
                a.methods[-1]=(signature,a.methods[-1][1])
                # Keep the native query and original arguments; only wrap its callback.
                a.modify(mid,{111:bytes([0x29,0x40])+u30(newmid)})
                updated=a.output();check=ABC(updated)
                assert a.A['cls']==check.A['cls'] and a.A['sig']==check.A['sig'][:len(a.A['sig'])]
                for i,row in a.A['body_records'].items():
                    if i!=mid:assert row['raw']==check.A['body_records'][i]['raw']
                cases=[]
                for error in ('',None,'no such table: names','no such table: nameschi','no such table: players'):
                    result=replay(a,code,'fifadb','SELECT * FROM nameschi WHERE playerid=252371',[{'playerid':252371}],error)
                    if error:
                        assert not result['callbacks'] and len(result['requests'])==1
                        path,body,callback=result['requests'][0]
                        assert path=='/static/sql/fifadb' and callback==('shipped_callback',7)
                        assert Reader(S,C).query('fifadb',body['sql'])[0]['playerid']==252371
                    else:assert not result['requests'] and result['callbacks']==[([{'playerid':252371}],error)]
                    cases.append(dict(native_error=error,result=result))
                raw=tag(kind,b[:head]+updated)
                changes.append(dict(class_name='SQLConnection',method=mid,new_callback_method=newmid,inherited_scope=scope,
                    original_http_callback_preserved=True,all_other_methods_traits_and_signatures_preserved=True,
                    bytecode_replay=cases))
        parts.append(raw)
    assert len(changes)==1
    new=bytearray(d[:start]+b''.join(parts));struct.pack_into('<I',new,4,len(new));gfx=b'CFX'+new[3:8]+zlib.compress(new[8:],9)
    payload=ROOT/'sql-fallback-Module.big';payload.write_bytes(source.read_bytes());bigdir.patch(payload,{member:gfx})
    assert bigdir.read(payload,member)==gfx
    oldtags=list(tags(d,start));newtags=list(tags(new,start));assert len(oldtags)==len(newtags)
    assert sum(a[2]!=b[2] for a,b in zip(oldtags,newtags))==1
    for name,*_ in bigdir.entries(source):
        if name!=member:assert bigdir.read(source,name)==bigdir.read(payload,name)
    http=S/'http_config.py';old=http.read_bytes();needle=b'if __name__ == "__main__":'
    assert old.count(needle)==1 and b'import native_sql_fallback' not in old
    newhttp=old.replace(needle,b'import native_sql_fallback\nnative_sql_fallback.install(sys.modules[__name__])\n\n'+needle)
    compile(newhttp,str(http),'exec');(ROOT/'sql-fallback-http_config.py').write_bytes(newhttp)
    report=dict(status='PREPARED_NATIVE_ERROR_FALLBACK',target=str(source),payload=str(payload),before_sha256=sha(source.read_bytes()),after_sha256=sha(payload.read_bytes()),
        http_before_sha256=sha(old),http_after_sha256=sha(newhttp),changes=changes,server_checks=server_checks,formal_written=False,native_verified=False,model_crash_fixed=False)
    (ROOT/'sql-fallback-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(status=report['status'],server_checks=len(server_checks),native_error_replays=5,client_methods_changed=1)))
    return report
if __name__=='__main__':build()
