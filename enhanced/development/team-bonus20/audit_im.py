"""Read-only IM comparison at equal development and current lineup diagnostics."""
from pathlib import Path
import ast, collections, json, sqlite3, ssl, urllib.request
S=Path(r'D:\FO3ID\server');R=Path(__file__).resolve().parent
ns={}
tree=ast.parse((S/'http_config.py').read_text('utf8'))
for name in ('ROLE_WEIGHTS','POS_ROLE','POSOVR'):
    n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
    exec(compile(ast.Module(body=[n],type_ignores=[]),'rating-constants','exec'),ns)
db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
rows=[dict(r) for r in db.execute('SELECT p.*, '+ns['POSOVR']+' AS primary_ovr FROM players p WHERE p.spid>=1000000')]
by_pid=collections.defaultdict(list)
for p in rows: by_pid[p['playerid']].append(p)
names={p:n for p,n in db.execute('SELECT playerid,full FROM nameschi')}
def rate(p,pos):
    return sum(p[k]*v for k,v in ns['ROLE_WEIGHTS'][ns['POS_ROLE'][pos]].items())/100
comparisons=[]
for im in rows:
    if im['spid']//1000000!=84:continue
    others=[p for p in by_pid[im['playerid']] if p['spid']//1000000!=84]
    if not others:continue
    best=max(others,key=lambda p:rate(p,im['preferredposition1']))
    a=rate(im,im['preferredposition1']);b=rate(best,im['preferredposition1'])
    comparisons.append(dict(playerid=im['playerid'],name=names.get(im['playerid'],str(im['playerid'])),im_spid=im['spid'],im_primary_ovr=im['primary_ovr'],im_slot_ovr=a,best_other_spid=best['spid'],best_other_primary_ovr=best['primary_ovr'],best_other_at_im_position=b,delta=round(a-b,2)))
imrows=[p for p in rows if p['spid']//1000000==84]
def get(path):
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    with op.open('https://127.0.0.1'+path,timeout=20) as f:return json.load(f)
coach=get('/coach/me');colors=get('/static/info/teamcolor')
team=coach.get('team',{});players={str(p.get('id',p.get('_id',''))):p for p in team.get('players',[])}
inventory={p['spid']:p for p in rows};active=team.get('teamcolors',[]);definitions={c['teamcolorid']:c for c in colors['teamColors']}
lineup=[]
for p in team.get('squad',{}).get('positions',[]):
    if p.get('pos',28)>=28:continue
    card=players.get(str(p.get('id',p.get('_id',''))),{})
    spid=int(p.get('spid',card.get('spid',0)));static=inventory.get(spid,{})
    lineup.append(dict(spid=spid,name=names.get(static.get('playerid'),'unknown'),grade=card.get('grade'),levelinfo=card.get('levelinfo'),base_primary_ovr=static.get('primary_ovr'),is_im=spid//1000000==84))
active_details=[dict(entry=e,definition=definitions.get(e['teamcolorid'])) for e in active]
report=dict(status='READONLY_ANALYSIS',im_cards=len(imrows),im_base_ovr=dict(min=min(p['primary_ovr'] for p in imrows),max=max(p['primary_ovr'] for p in imrows),mean=sum(p['primary_ovr'] for p in imrows)/len(imrows)),
            comparisons_count=len(comparisons),delta_vs_best_same_player_at_im_position=dict(min=min(p['delta'] for p in comparisons),max=max(p['delta'] for p in comparisons),mean=sum(p['delta'] for p in comparisons)/len(comparisons),wins=sum(p['delta']>0 for p in comparisons),ties=sum(p['delta']==0 for p in comparisons),losses=sum(p['delta']<0 for p in comparisons)),
            comparisons=sorted(comparisons,key=lambda p:p['delta']),lineup=lineup,active_teamcolors=active_details,grade_bonus={1:5,5:10,8:17,9:20,10:24},native_verified=False)
(R/'im-readonly-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps({k:v for k,v in report.items() if k!='comparisons'},ensure_ascii=True))
print(json.dumps(sorted(comparisons,key=lambda p:p['im_primary_ovr'],reverse=True)[:12],ensure_ascii=True))
