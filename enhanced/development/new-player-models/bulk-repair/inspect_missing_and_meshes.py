import ast,collections,json,pathlib,sqlite3,struct,sys,zlib,hashlib,xml.etree.ElementTree as ET
R=pathlib.Path(__file__).resolve().parent;W=R.parent/'home-black-screen'
sys.path[:0]=['D:/FO3ID/server/tools/re']
import bigdir,eadb
C=pathlib.Path('D:/FO3ID/32795');a=json.loads((R/'current-audit.json').read_text('utf8'));catalog=json.loads(pathlib.Path('D:/FO3QA/modern_player_integration_v2/model19-v4/model_catalog24.json').read_text('utf8'))
db=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db');meta=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8');node=next(n for n in ET.fromstring(meta).iter('table') if n.get('name')=='players');fields={f.get('name'):f.attrib for f in node.iter('field')};_,names,raws=eadb.db_tables(db);t=eadb.Table(raws[names.index(node.get('shortname').encode())])
con=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);con.row_factory=sqlite3.Row
missing=[]
for pid in sorted({p['playerid'] for p in a['missing_native']}):
    sources=[dict(r) for r in con.execute('SELECT * FROM players WHERE playerid=? ORDER BY spid',(pid,))]
    matched=[]
    for r in t.rows:
        if t.get(r,fields['headassetid']['shortname'])==pid:matched.append({n:t.get(r,fields[n]['shortname']) for n in ['playerid','spid','headassetid','headclasscode','headtypecode','overallrating','skillmoves']})
    missing.append(dict(playerid=pid,source_rows=[{k:s[k] for k in ['spid','overallrating','skillmoves','headtypecode','headclasscode','height','weight','birthdate']} for s in sources],same_headasset_native=matched))
scope={'struct':struct,'zlib':zlib,'hashlib':hashlib}
audit=json.loads((R.parent/'audit/audit.json').read_text('utf8'))
for n in ast.parse(pathlib.Path(audit['decoder_source']).read_text('utf8')).body:
    if isinstance(n,ast.FunctionDef) and n.name=='unpack':exec(compile(ast.Module(body=[n],type_ignores=[]),'unpack','exec'),scope)
meshes=[]
for p in catalog['players']:
    if not p.get('reserved_head_selector'):continue
    pid=p['playerid'];files=[]
    for folder,file,archive in [('heads',f'head_{pid}_0.rx3',4),('hair',f'hair_{pid}_0_0.rx3',4),('hairlod',f'hairlod_{pid}_0_0.rx3',6)]:
        member=f'data/sceneassets/{folder}/{file}'
        try:
            raw=bigdir.read(C/f'data/data_{archive}.big',member);d,_=scope['unpack'](raw);counts=[]
            for i in range(struct.unpack_from('<I',d,12)[0]):
                kind,off,size,_=struct.unpack_from('<IIII',d,16+i*16)
                if kind==0xdf9aec1e:counts.append(struct.unpack_from('<I',d,off+4)[0])
            files.append(dict(member=member,archive=archive,raw_bytes=len(raw),rx3_bytes=len(d),skin_counts=counts,raw_sha256=hashlib.sha256(raw).hexdigest()))
        except Exception as e:files.append(dict(member=member,error=repr(e)))
    meshes.append(dict(playerid=pid,name=p['name_zh'],files=files))
out=dict(missing=missing,meshes=meshes);(R/'missing-and-meshes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(missing,ensure_ascii=True,indent=2));print('meshes',[(r['playerid'],[(f.get('skin_counts'),f.get('error')) for f in r['files']]) for r in meshes])
