import json,pathlib,sqlite3,struct,sys
from minidump_read import Dump
R=pathlib.Path(__file__).resolve().parent
d=Dump(R/'official-game-85916-20261107-012032.dmp')
parser=0x13773b10;symbols=d.u32(parser+0x10);meta=d.u32(symbols+4);entries=d.u32(meta+4);count=d.u32(meta+8)
print('database',hex(symbols),'metadata',hex(meta),'entries',hex(entries),'count',count)
rows=[]
for i in range(min(count,1000)):
    raw=d.read(entries+i*24,24);nameptr=struct.unpack_from('<I',raw,20)[0]
    try:
        text=d.read(nameptr,256).split(b'\0')[0].decode('latin1');prefix=d.read(nameptr-8,8).hex()
    except KeyError:text='unreadable';prefix=''
    rows.append(dict(index=i,raw=raw.hex(),name=text,name_prefix=prefix))
print(json.dumps(rows[:30],indent=2))
c=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True)
tables=c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('sqlite relevant',[n for n, in tables if 'train' in n or 'player' in n])
for table in ['trainingteamplayers','players','teamplayerlinks']:
    if (table,) in tables:
        print(table,c.execute('SELECT * FROM '+table+' WHERE playerid=252371 LIMIT 2').fetchall())
(R/'fault-database-symbols.json').write_text(json.dumps(dict(parser=hex(parser),symbols=hex(symbols),metadata=hex(meta),count=count,tables=rows),indent=2),encoding='utf8')
