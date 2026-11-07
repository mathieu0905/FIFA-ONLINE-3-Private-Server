import json,pathlib,sqlite3
R=pathlib.Path(__file__).resolve().parent;S=pathlib.Path('D:/FO3ID/server');reg=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'))
c=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);c.row_factory=sqlite3.Row
for card in reg['cards']:
    row=c.execute('SELECT * FROM players WHERE spid=?',(card['fo3_spid'],)).fetchone()
    if row['skillmoves']>4 or card['base_playerid'] in [245,249]:print(json.dumps(card,ensure_ascii=True))
print('all sql skill5 rows',[(r['spid'],r['playerid']) for r in c.execute('SELECT * FROM players WHERE skillmoves>4')])
