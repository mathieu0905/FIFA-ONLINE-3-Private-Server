"""Read-only FO3 nostalgia roster and UL reference inspection."""
from pathlib import Path
import ast,json,sqlite3,statistics,unicodedata
ROOT=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
tree=ast.parse((S/'http_config.py').read_text('utf-8'))
weights=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLE_WEIGHTS' for t in n.targets))
roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
def ovr(r):return sum(r[k]*v for k,v in weights[roles[r['preferredposition1']]].items())//100
def norm(t):return ''.join(c for c in unicodedata.normalize('NFKD',t or '').lower() if not unicodedata.combining(c))
patterns='Pogba|Varane|Toure|Essien|Fellaini|Matic|Ramires|Diaby|Drogba|Ibrahimovic|Benzema|Lukaku|Benteke|Dzeko|Adebayor|Doumbia|Emenike|Ibarbo|Hulk|Farfan|Lavezzi|Rooney|Benatia|Boateng|Maicon|David Luiz|Mangala|Smalling|Koscielny|Cech|Neuer|Courtois|Alaba|Clichy|Sissoko|Remy'.split('|')
names=[dict(r) for r in db.execute('SELECT playerid,full_eng,full,short FROM nameseng')]
out={}
for pattern in patterns:
    matches=[n for n in names if norm(pattern) in norm(n['full_eng'] or n['full'] or n['short'])]
    out[pattern]=[]
    for n in matches:
        rows=[dict(r) for r in db.execute('SELECT * FROM players WHERE playerid=? AND spid>=1000000 ORDER BY spid',(n['playerid'],))]
        if not rows:continue
        out[pattern].append(dict(playerid=n['playerid'],name=n['full_eng'] or n['full'],cards=[dict(spid=r['spid'],season=r['spid']//1000000,ovr=ovr(r),pos=r['preferredposition1'],height=r['height'],weight=r['weight']) for r in rows]))
reference=[dict(r) for r in db.execute('SELECT * FROM players WHERE spid/1000000=30')]
summary={}
for role in ('GK','CB','FB','DM','CM','AM','W','ST','CF'):
    values=sorted(ovr(r) for r in reference if roles[r['preferredposition1']]==role)
    if values:summary[role]=dict(count=len(values),min=min(values),median=statistics.median(values),max=max(values))
result=dict(UL_reference=summary,matches=out)
(ROOT/'inspection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(UL_reference=summary,matches={k:[dict(playerid=x['playerid'],name=x['name'],cards=len(x['cards'])) for x in v] for k,v in out.items()}),ensure_ascii=True,indent=2))
