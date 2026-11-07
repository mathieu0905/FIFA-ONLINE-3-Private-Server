"""Prepare the requested MUL roster; read-only against official files."""
from pathlib import Path
import ast,hashlib,json,sqlite3,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent; S=Path('D:/FO3ID/server'); C=Path('D:/FO3ID/32795')
DATA='''190053|舒梅切尔|92|0
51539|范德萨|91|0
193080|德赫亚|91|0
244|加里·内维尔|90|3
53019|丹尼斯·欧文|90|7
5740|斯塔姆|91|5
7289|费迪南德|92|5
140601|维迪奇|92|5
52091|埃弗拉|90|7
3484|奥谢|88|3
13130|韦斯·布朗|88|5
167905|瓦伦西亚|89|3
205988|卢克·肖|89|7
249|菲尔·内维尔|88|3
246|斯科尔斯|91|14
241|吉格斯|92|16
240|罗伊·基恩|91|10
250|贝克汉姆|91|12
230025|博比·查尔顿|92|21
230024|布莱恩·罗布森|91|14
21146|卡里克|90|10
245|尼基·巴特|88|10
39943|朴智星|89|14
195864|博格巴|90|14
212198|布鲁诺·费尔南德斯|91|18
138782|弗莱彻|88|14
191740|埃雷拉|88|14
54050|鲁尼|92|21
167198|坎通纳|92|21
226764|乔治·贝斯特|92|23
230026|丹尼斯·劳|92|25
36|约克|90|25
239|安迪·科尔|90|25
10264|范尼斯特鲁伊|91|25
20801|C罗|92|27
1845|索尔斯克亚|89|25
393|谢林汉姆|89|21
7826|范佩西|91|25
30110|贝尔巴托夫|89|25
231677|拉什福德|89|27
139068|纳尼|89|27'''
STATS='strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf8')
def prepare():
 db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 tree=ast.parse((S/'http_config.py').read_text('utf8'));w=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLE_WEIGHTS' for t in n.targets))
 roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
 cards=[]
 for line in DATA.splitlines():
  pid,zh,target,pos=line.split('|');pid=int(pid);target=int(target);pos=int(pos);spid=48000000+pid
  existing=db.execute('select * from players where spid=?',(spid,)).fetchone()
  # Retain all existing MUL identities/models. For newcomers prefer authentic
  # historical rows, excluding high-stat imported/custom and engine-only cards.
  rows=list(db.execute('select * from players where playerid=? and spid>=1000000 and spid%1000000=? and spid/1000000 not in (12,13,19,84)',(pid,pid)))
  if existing:row=dict(existing)
  elif rows:row=dict(max(rows,key=lambda r:(r['overallrating'],r['spid'])))
  else:
   row=dict(db.execute('select * from players where playerid=? and spid=?',(pid,pid)).fetchone())
  name=db.execute('select full_eng from nameseng where playerid=?',(pid,)).fetchone()[0]
  assert db.execute('select 1 from namesind where playerid=?',(pid,)).fetchone(),(pid,name)
  original=dict(row);role=roles[pos];relevant=set(STATS if pos else ['gkdiving','gkhandling','gkkicking','gkpositioning','gkreflexes','reactions'])
  best=None
  for shift in range(-80,81):
   stats={k:min(99,max(1,row[k]+shift)) if k in relevant else row[k] for k in STATS}
   base=sum(stats[k]*n for k,n in w[role].items())//100
   rank=(abs(base+5-target),sum(v==99 or v==1 for v in stats.values()),abs(shift))
   if best is None or rank<best[0]:best=(rank,stats,base,shift)
  _,stats,base,shift=best;assert base+5==target
  positions=list(dict.fromkeys([pos]+[row['preferredposition'+str(i)] for i in range(1,5) if row['preferredposition'+str(i)]>=0]))[:4]
  row.update(stats,spid=spid,overallrating=base,potential=max(base,row['potential']),teamid=11,leagueid=13,historyopen=1)
  row.update({'preferredposition'+str(i):positions[i-1] if len(positions)>=i else -1 for i in range(1,5)})
  # Keep an existing card's non-stat metadata and original position set untouched.
  if existing:
   for k in original:
    if k not in STATS+['overallrating','potential']:row[k]=original[k]
   actual=sum(row[k]*n for k,n in w[roles[row['preferredposition1']]].items())//100
   assert actual+5==target,(pid,actual,target)
  cards.append(dict(fo3_spid=spid,base_playerid=pid,name_zh=zh,name_en=name,season_id=48,template_spid=original['spid'],source_row_sha256=digest(original),existing=bool(existing),display_plus1_ovr=base+5,base_ovr=base,stat_shift=shift,row=row))
 assert len(cards)==41 and len({r['fo3_spid'] for r in cards})==41
 result=dict(schema=1,season=48,label='MUL',count=len(cards),existing=sum(c['existing'] for c in cards),added=sum(not c['existing'] for c in cards),rating_basis='level1 grade1 primary-position OVR; +5 enhancement; excludes team-color and coach boosts',cards=cards)
 write(R/'roster.json',result);print(json.dumps({k:v for k,v in result.items() if k!='cards'}))
 return result
if __name__=='__main__':prepare()
