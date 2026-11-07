from pathlib import Path
import sqlite3,json
c=sqlite3.connect(Path('D:/FO3ID/server/gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
for word in ('Bodmer','Wanyama','Gustavo'):
    rows=c.execute('SELECT playerid,full_eng FROM nameseng WHERE full_eng LIKE ? AND playerid<1000000',('%'+word+'%',)).fetchall()
    for n in rows:
        if word!='Gustavo' or n['full_eng'].startswith('Luiz Gustavo'):
            print(json.dumps(dict(n),ensure_ascii=True),[tuple(r) for r in c.execute('SELECT spid,height,weight FROM players WHERE playerid=? AND spid>=1000000',(n['playerid'],))])
