import datetime,json,pathlib,sqlite3,sys,xml.etree.ElementTree as ET,collections,email.utils
sys.path.insert(0,'D:/FO3ID/server/tools/re')
import eadb
R=pathlib.Path(__file__).resolve().parent
db=(R/'current-ea-db.db').read_bytes();meta=(R/'current-ea-db-meta.xml').read_text('utf8');node=next(t for t in ET.fromstring(meta).iter('table') if t.get('name')=='players')
fields={f.get('name'):f.attrib for f in node.iter('field')};_,names,raws=eadb.db_tables(db);t=eadb.Table(raws[names.index(node.get('shortname').encode())])
c=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);c.row_factory=sqlite3.Row
sql={r['playerid']:dict(r) for r in c.execute('SELECT * FROM players ORDER BY spid DESC')}
dates=collections.Counter();samples=[]
for row in t.rows:
    pid=t.get(row,fields['playerid']['shortname']);s=sql.get(pid)
    if not s:continue
    try:birth=datetime.datetime.strptime(s['birthdate'],'%m/%d/%Y %I:%M:%S %p').date()
    except (ValueError,TypeError):continue
    raw=t.get(row,fields['birthdate']['shortname']);offset=birth.toordinal()-(raw-2**31);dates[offset]+=1
    if len(samples)<8:samples.append((pid,str(birth),raw,offset))
print('date offsets',dates,'samples',samples)
bell=sql[252371];print('native-only',set(fields)-set(bell));print('nonconvertible')
for name,f in fields.items():
    if name not in bell:continue
    v=bell[name]
    if f['type'] not in ['DBOFIELDTYPE_INTEGER','DBOFIELDTYPE_REAL']:continue
    low=int(f.get('rangelow',0));high=int(f.get('rangehigh',2**32-1));depth=t.fields[f['shortname']][2]
    if isinstance(v,(int,float)) and (v<low or v>high or v-low>=2**depth):print(name,v,low,high,depth)
print('missing source IDs',[p for p in [252371,243715,251854,256790,256630,238794,246669,277643,257534] if p not in {t.get(r,fields['playerid']['shortname']) for r in t.rows}])
