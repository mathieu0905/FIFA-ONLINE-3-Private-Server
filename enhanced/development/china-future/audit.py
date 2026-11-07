from pathlib import Path
import sqlite3,json,ast,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
con=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
names=['王钰栋','李昊炎','李昊','向余望','蒯纪闻','刘诚宇','毛伟杰','李新翔','依木兰','杨皓宇','胡荷韬','吾米提江','彭啸','刘浩帆','汪士钦','姚浩洋']
found={n:[dict(r) for r in con.execute('select p.playerid,p.spid,n.full,n.full_eng,p.birthdate from players p join nameschi n on n.playerid=p.playerid where n.full like ? or n.short like ? group by p.playerid',(f'%{n}%',f'%{n}%'))] for n in names}
print(json.dumps(found,ensure_ascii=True))
registry=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'))
print('seasons',[(s['id'],s['label'].encode('unicode_escape').decode()) for s in registry['seasons']])
print('sample',json.dumps(dict(con.execute('select * from players where nationality=155 and headclasscode=1 and preferredposition1=0 limit 1').fetchone()),ensure_ascii=True))
print('names',dict(con.execute('select * from nameseng limit 1').fetchone()))
print('max_pid',con.execute('select max(playerid) from players').fetchone()[0])
print('roster84',[(c['name_zh'],c['fo3_spid']) for c in registry['cards'] if c['fo3_spid']//1000000==84][:1])
