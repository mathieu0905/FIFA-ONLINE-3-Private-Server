"""Append genuine missing players to the engine EA database, preserving all old rows.

Only workspace artifacts are written. The UI SQLite, cards and state are untouched.
"""
import datetime,email.utils,hashlib,json,pathlib,re,sqlite3,struct,sys,xml.etree.ElementTree as ET
sys.path[:0]=['D:/FO3ID/server/tools/re','D:/FO3ID/server/tools']
import bigdir,eadb,refpack,check_data0_layout
R=pathlib.Path(__file__).resolve().parent;O=R/'native-roster';O.mkdir(exist_ok=True)
P=pathlib.Path('D:/FO3ID/32795/data/data_0.big');MEMBER='data/db/fifa_ng_db.db'
def sha(b):return hashlib.sha256(b).hexdigest()
def filehash(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    before=filehash(P);db=bigdir.read(P,MEMBER);meta=bigdir.read(P,'data/db/fifa_ng_db-meta.xml').decode('utf8')
    node=next(t for t in ET.fromstring(meta).iter('table') if t.get('name')=='players')
    fields={f.get('name'):f.attrib for f in node.iter('field')};base,names,raws=eadb.db_tables(db);index=names.index(node.get('shortname').encode());t=eadb.Table(raws[index]);oldrows=list(t.rows)
    c=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);c.row_factory=sqlite3.Row
    audit=json.loads((R.parent/'audit/audit.json').read_text('utf8'));new=[]
    existing={t.get(row,fields['playerid']['shortname']) for row in t.rows}
    template=t.find(fields['playerid']['shortname'],231747)
    for player in audit['players']:
        # First repair the reproduced Bellingham path. Other imports require their
        # own semantic conversion (e.g. source skillmoves=5 exceeds native 0..4).
        if player['playerid']!=252371:continue
        pid=player['playerid'];assert pid not in existing
        source=dict(c.execute('SELECT * FROM players WHERE spid=?',(player['spid'],)).fetchone())
        assert source['playerid']==pid and set(fields)-set(source)=={'headassetid'}
        actual={**source,'headassetid':pid,'headclasscode':0,'headtypecode':1023}
        row=template;values={}
        for name,f in fields.items():
            sn=f['shortname'];ty,bo,depth=t.fields[sn];v=actual[name]
            if f['type']=='DBOFIELDTYPE_DATE':
                date=datetime.datetime.strptime(v,'%m/%d/%Y %I:%M:%S %p').date() if name=='birthdate' else email.utils.parsedate_to_datetime(v).date()
                # EA Gregorian day zero = ordinal 577735. Verified against 32,483
                # matching native/SQLite birthdays; 43 differing source birthdays retained.
                semantic=date.toordinal()-577735;encoded=semantic-int(f['rangelow'])
            elif ty==4:
                semantic=float(v);encoded=struct.unpack('<I',struct.pack('<f',semantic))[0]
            else:
                assert ty==3 and isinstance(v,(int,float)) and int(v)==v,(name,v,ty)
                semantic=int(v);low=int(f['rangelow']);high=int(f['rangehigh']);assert low<=semantic<=high,(pid,name,v,low,high)
                encoded=semantic-low
            assert 0<=encoded<2**depth,(pid,name,encoded,depth)
            row=t.set(row,sn,encoded);values[name]=semantic
        for name,f in fields.items():
            raw=t.get(row,f['shortname'])
            if f['type']=='DBOFIELDTYPE_DATE':assert raw+int(f['rangelow'])==values[name]
            elif t.fields[f['shortname']][0]==4:assert raw==values[name]
            else:assert raw+int(f['rangelow'])==values[name]
        t.rows.append(row);new.append(dict(playerid=pid,spid=source['spid'],values=values,raw_sha256=sha(row)))
    assert t.rows[:len(oldrows)]==oldrows and len(t.rows)<65536
    raws[index]=t.raw();out=bytearray(db[:base]);offset=0
    for i,raw in enumerate(raws):struct.pack_into('<I',out,0x1c+i*8,offset);offset+=len(raw)
    struct.pack_into('<I',out,base-4,eadb.crc(out[0x18:base-4]));struct.pack_into('<I',out,8,base+offset);struct.pack_into('<I',out,0x14,eadb.crc(out[:0x14]))
    rebuilt=bytes(out)+b''.join(raws);assert len(rebuilt)==base+offset
    _,newnames,newraws=eadb.db_tables(rebuilt);assert names==newnames
    for i,(a,b) in enumerate(zip(eadb.db_tables(db)[2],newraws)):
        if i!=index:assert a==b
    parsed=eadb.Table(newraws[index]);assert parsed.rows[:len(oldrows)]==oldrows
    for p in new:assert sha(parsed.find(fields['playerid']['shortname'],p['playerid']))==p['raw_sha256']
    assert eadb.u32(rebuilt,0x14)==eadb.crc(rebuilt[:0x14]) and eadb.u32(rebuilt,base-4)==eadb.crc(rebuilt[0x18:base-4])
    playerraw=newraws[index];assert eadb.u32(playerraw,0x20)==eadb.crc(playerraw[:0x20]) and eadb.u32(playerraw,len(playerraw)-4)==eadb.crc(playerraw[0x24:-4])
    (O/'fifa_ng_db.db').write_bytes(rebuilt);packed=refpack.refpack(rebuilt);assert refpack.unrefpack(packed)==rebuilt and len(packed)<len(rebuilt)
    (O/'fifa_ng_db.refpack').write_bytes(packed)
    table=bytearray(bigdir.table(P));directory=list(bigdir._walk(table));target=O/'data_0.big'
    with P.open('rb') as inp,target.open('wb') as f:
        f.write(table)
        for tablepos,name,oldoff,oldsize,oldusize in directory:
            offset=(f.tell()+127)&~127;f.write(bytes(offset-f.tell()))
            if name==MEMBER:payload=packed;usize=len(rebuilt)
            else:inp.seek(oldoff);payload=inp.read(oldsize);usize=oldusize
            f.write(payload);size=len(payload)
            struct.pack_into('>III',table,tablepos,bigdir.enc(offset),bigdir.enc(size),bigdir.enc(usize))
            key=size&255
            for j,ch in enumerate(name.encode('latin1')):
                b=ch^key;table[tablepos+16+j]=((b<<4)|(b>>4))&255;key=((b or size&255)-0x66)&255
        end=f.tell();struct.pack_into('<I',table,4,end);f.seek(0);f.write(table)
    layout=check_data0_layout.inspect(target,P,{MEMBER},len(directory));assert layout['status']=='PASS',layout
    assert bigdir.read(target,MEMBER)==rebuilt and filehash(P)==before
    report=dict(status='READY_NATIVE_ROSTER_NOT_INSTALLED',target=str(P),payload=str(target),before_sha256=before,after_sha256=filehash(target),member=MEMBER,old_player_rows=len(oldrows),new_player_rows=len(parsed.rows),added=new,
      original_rows_byte_identical=True,other_tables_byte_identical=True,layout=layout,state_shop_written=False,native_verified=False)
    (O/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['added','layout']},ensure_ascii=True));print('layout',layout['status'],'old rows preserved',len(oldrows),'added',[p['playerid'] for p in new])
if __name__=='__main__':main()
