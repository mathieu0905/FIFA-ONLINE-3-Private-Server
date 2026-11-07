from pathlib import Path
import sqlite3,json
db=sqlite3.connect(Path('D:/FO3ID/server/gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
for word in ('Givanildo','Ibrahimovic','Benzema','Lukaku','Benteke','Dzeko','Adebayor','Lavezzi','Benatia','Alaba','Clichy','Sissoko','Remy'):
    print(word,db.execute('SELECT playerid,full_eng FROM nameseng WHERE full_eng LIKE ?',('%'+word+'%',)).fetchall())
