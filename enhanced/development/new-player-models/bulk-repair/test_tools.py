"""Failure controls on real bounded formats and temporary archive I/O only."""
import json,pathlib,struct,sys,tempfile
R=pathlib.Path(__file__).resolve().parent;S=pathlib.Path('D:/FO3ID/server');C=pathlib.Path('D:/FO3ID/32795')
sys.path[:0]=[str(R/'tooling'),str(S/'tools/re')]
import bigdir,eadb,native_db,ordered_big,rx3
passed=[]
def rejects(fn,description):
    try:fn()
    except (ValueError,AssertionError,KeyError,struct.error):passed.append(description)
    else:raise AssertionError('Failure control did not reject: '+description)
assert [native_db.stars_to_code(i) for i in range(1,6)]==[0,1,2,3,4];passed.append('All five source star counts map to native 0..4')
rejects(lambda:native_db.stars_to_code(0),'Zero star input rejected');rejects(lambda:native_db.stars_to_code(6),'Six star input rejected')
db=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db');meta=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8');_,_,_,_,table,fields=native_db.player_table(db,meta)
rejects(lambda:native_db.encode(table,fields,table.rows[0],{'playerid':123}),'Incomplete native semantic records rejected')
broken=bytearray(db);broken[0x14]^=1;rejects(lambda:native_db.verify_crc(broken),'EA DB header CRC corruption rejected')
member='data/sceneassets/heads/head_252371_0.rx3';raw=bigdir.read(C/'data/data_4.big',member);good=rx3.validate(raw);assert all(m['skin_bones']==252 for m in good['meshes']);passed.append('Human-verified Bellingham mesh validates')
d=bytearray(rx3.unwrap(raw));sections=rx3.sections(d);_,vo,_=sections[rx3.VERTEX][0];fields_,n,stride,endian=rx3.vertex_fields(d,sections[rx3.FORMAT][0],sections[rx3.VERTEX][0]);at=vo+16;io=fields_['i0'][0];wo=fields_['w0'][0];slot=next(i for i,w in enumerate(d[at+wo:at+wo+4]) if w);d[at+io+slot]=253
rejects(lambda:rx3.validate(bytes(d)),'Positive-weight bone outside target rig rejected')
d=bytearray(rx3.unwrap(raw));_,ro,_=sections[rx3.REMAP][0];bone=d[ro+272];d[ro+16+bone]^=1;rejects(lambda:rx3.validate(bytes(d)),'Bone palette inverse corruption rejected')
d=bytearray(rx3.unwrap(raw));_,so,_=sections[rx3.SKIN][0];struct.pack_into('<I',d,so+4,255);rejects(lambda:rx3.validate(bytes(d)),'Unconverted 255-bone skin rejected')
with tempfile.TemporaryDirectory(prefix='fo3-import-io-',dir=R) as tmp:
    p=pathlib.Path(tmp);source=p/'before.big';target=p/'after.big'
    name='data/a.bin';body=b'original member';size=len(body);head=bytearray(128);head[:4]=b'BIg4';struct.pack_into('<I',head,4,128+size);struct.pack_into('>II',head,8,bigdir.enc(1),bigdir.enc(128));struct.pack_into('>IIII',head,17,bigdir.enc(128),bigdir.enc(size),bigdir.enc(0),bigdir.enc(len(name)))
    key=size&255
    for j,ch in enumerate(name.encode()):
        b=ch^key;head[33+j]=((b<<4)|(b>>4))&255;key=((b or size&255)-0x66)&255
    source.write_bytes(head+body);old=source.read_bytes();ordered_big.rebuild(source,target,{'data/new.bin':(b'new genuine payload',0)})
    assert bigdir.read(target,name)==body and bigdir.read(target,'data/new.bin')==b'new genuine payload' and source.read_bytes()==old
    passed.append('Adding a new archive member preserves existing raw payload and directory order')
    rejects(lambda:ordered_big.rebuild(source,source,{}),'In-place build target rejected')
(R/'tool-tests.json').write_text(json.dumps(dict(status='PASS',tests=passed,formal_written=False),indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',count=len(passed),tests=passed)))
