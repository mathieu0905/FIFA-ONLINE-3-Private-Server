from pathlib import Path
import ast,json,sqlite3,statistics,collections
root=Path('D:/fifaol3/npc-peer-market');tree=ast.parse(Path('D:/FO3ID/server/http_config.py').read_text('utf8'))
assign={t.id:n.value for n in tree.body if isinstance(n,ast.Assign) for t in n.targets if isinstance(t,ast.Name)}
w=ast.literal_eval(assign['ROLE_WEIGHTS']);roles=assign['POS_ROLE'].func.value.value.split();seasons={s:label for label,ss,_ in ast.literal_eval(assign['FA_SEASONS']) for s in ss}
raw=json.loads(Path('D:/FO3ID/server/gamedata/fa_prices.json').read_text('utf8'))
c=sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True);c.row_factory=sqlite3.Row
names={r['playerid']:r['full_eng'] or r['full'] or r['short_eng'] for r in c.execute('select * from nameseng')}
rows=[]
for r in c.execute('select * from players'):
 r=dict(r);price=raw.get(str(r['spid']),0)
 if price<=0:continue
 r.update(price=int(price),season=r['spid']//1000000,name=names.get(r['playerid'],str(r['playerid'])))
 r['ovr']=sum(r[k]*v for k,v in w[roles[r['preferredposition1']]].items())//100
 rows.append(r)
(root/'historical-data.json').write_text(json.dumps(rows,ensure_ascii=False),'utf8')
(root/'schema.json').write_text(json.dumps(dict(role_weights=w,position_roles=roles,season_labels=seasons),ensure_ascii=False,indent=2),'utf8')
print('LISTED',len(raw),'POSITIVE',sum(p>0 for p in raw.values()),'JOINED',len(rows),'PLAYERS',len({r['playerid'] for r in rows}))
print('TOP',[(r['spid'],r['name'],seasons.get(r['season']),r['ovr'],r['price']) for r in sorted(rows,key=lambda r:-r['price'])[:12]])
