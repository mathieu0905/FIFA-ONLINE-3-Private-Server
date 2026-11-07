import sys,json,pathlib,re,sqlite3,xml.etree.ElementTree as ET
sys.path.insert(0,'D:/FO3ID/server/tools/re')
import bigdir,eadb
R=pathlib.Path(__file__).resolve().parent
archive='D:/FO3ID/32795/data/data_0.big'
db=bigdir.read(archive,'data/db/fifa_ng_db.db');meta=bigdir.read(archive,'data/db/fifa_ng_db-meta.xml').decode('utf8')
(R/'current-ea-db.db').write_bytes(db);(R/'current-ea-db-meta.xml').write_text(meta,encoding='utf8')
root=ET.fromstring(meta);node=next(t for t in root.iter('table') if t.get('name')=='players')
_,names,raws=eadb.db_tables(db);t=eadb.Table(raws[names.index(node.get('shortname').encode())]);fields={f.get('name'):f.attrib for f in node.iter('field')};idkey=fields['playerid']['shortname'];ids={t.get(r,idkey) for r in t.rows}
print('EA players',len(t.rows),'Bell present',252371 in ids,'native existing Mbappe',231747 in ids)
print('fields',json.dumps(fields,indent=2))
print('mbappe',json.dumps(next(r for r in eadb.rows(db,meta,'players') if r['playerid']==231747),indent=2))
c=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);c.row_factory=sqlite3.Row
print('sql mbappe',json.dumps(dict(c.execute('SELECT * FROM players WHERE playerid=231747 LIMIT 1').fetchone()),indent=2))
