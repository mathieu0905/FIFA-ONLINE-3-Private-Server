import sqlite3,json,sys
sys.path.insert(0,'D:/FO3ID/server/tools/re')
import bigdir
d=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True)
for word in ('Torres','Alonso','Ronaldo','Cafu','Marcos','Neville'):
 print(word,json.dumps(d.execute('select playerid,full_eng from nameseng where full_eng like ?',('%'+word+'%',)).fetchall()))
v=json.loads(bigdir.read('D:/FO3ID/server/patches/language_chi.big','data/ui/external/LANGUAGESTRING_CHI.json'))
print(json.dumps({k:x for k,x in v.items() if k.startswith('TRANSFERMARKET_SEASON_')},ensure_ascii=True))
print('columns',d.execute('pragma table_info(players)').fetchall())
print('occupied19',d.execute('select count(*) from players where spid/1000000=19').fetchone())
