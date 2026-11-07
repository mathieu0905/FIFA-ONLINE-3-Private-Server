import sqlite3,json
c=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True)
rows=c.execute("""select n.playerid,n.full_eng,group_concat(distinct p.spid/1000000)
from nameseng n join players p on p.playerid=n.playerid where
(n.full_eng like '%Campbell%' or n.full_eng like '%Blanc%' or n.full_eng like '%Nesta%' or n.full_eng like '%Schmeichel%' or n.full_eng like '%Stam%')
and p.spid>=1000000 group by n.playerid,n.full_eng""").fetchall()
print(json.dumps(rows,ensure_ascii=True))
