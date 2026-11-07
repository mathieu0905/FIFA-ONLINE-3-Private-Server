import pathlib,sqlite3,sys,xml.etree.ElementTree as ET
sys.path.insert(0,'D:/FO3ID/server/tools/re');import bigdir
meta=bigdir.read('D:/FO3ID/32795/data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8');node=next(n for n in ET.fromstring(meta).iter('table') if n.get('name')=='players');fields={f.get('name'):f.attrib for f in node.iter('field')}
c=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);c.row_factory=sqlite3.Row
for pid in [250,5467,167198]:
    for row in c.execute('SELECT * FROM players WHERE playerid=? ORDER BY overallrating,spid',(pid,)):
        invalid=[(n,row[n],int(f['rangelow']),int(f['rangehigh'])) for n,f in fields.items() if n in row.keys() and f['type']=='DBOFIELDTYPE_INTEGER' and not int(f['rangelow'])<=row[n]<=int(f['rangehigh'])]
        print(pid,row['spid'],invalid)
