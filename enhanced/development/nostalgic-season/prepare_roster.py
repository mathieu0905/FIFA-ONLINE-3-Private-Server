"""Identity audit and deterministic nostalgia-season specification; no formal writes."""
from pathlib import Path
import ast,hashlib,json,sqlite3,sys,unicodedata
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent; S=Path('D:/FO3ID/server')
def norm(t):return ''.join(c for c in unicodedata.normalize('NFKD',t.lower()) if not unicodedata.combining(c))
# zh | unambiguous English fragment | preferred season | nominal group | primary pos override (-1 preserves)
DATA='''德罗巴|Didier Drogba|69|ST|-1
伊布拉希莫维奇|Zlatan Ibrahimovic|11|ST|-1
本泽马|Karim Benzema|69|ST|-1
卢卡库|Romelu Lukaku|77|ST|-1
本特克|Christian Benteke|77|ST|-1
哲科|Edin Dzeko|10|ST|-1
阿德巴约|Emmanuel Adebayor|8|ST|-1
敦比亚|Seydou Doumbia|11|ST|-1
埃梅尼克|Emmanuel Emenike|14|ST|-1
伊巴尔博|Victor Ibarbo|77|ST|-1
雷米|Loic Remy|11|ST|-1
亨利|Thierry Henry|7|ST|-1
托雷斯|Fernando Jose Torres|67|ST|-1
埃托奥|Samuel Eto'o|69|ST|-1
C罗|C. Ronaldo dos Santos|63|WIDE|-1
罗纳尔迪尼奥|Ronaldo de Assis|7|WIDE|27
纳尼|Luís Carlos Almeida|11|WIDE|-1
瓦伦西亚|Antonio Valencia|69|WIDE|-1
贝尔|Gareth Bale|69|WIDE|-1
罗本|Arjen Robben|47|WIDE|-1
里贝里|Franck Ribery|11|WIDE|-1
迪马利亚|Angel Di Maria|77|WIDE|16
罗伊斯|Marco Reus|77|WIDE|-1
阿扎尔|Eden Hazard|53|WIDE|-1
内马尔|Neymar|77|WIDE|-1
沃尔科特|Theo Walcott|11|WIDE|-1
列农|Aaron Lennon|69|WIDE|-1
胡尔克|Givanildo Vieira|11|WIDE|-1
法尔范|Jefferson Farfan|69|WIDE|-1
拉维奇|Ezequiel Lavezzi|11|WIDE|-1
博格巴|Paul Pogba|77|MID|-1
亚亚·图雷|Yaya Toure|77|MID|-1
埃辛|Michael Essien|8|MID|-1
费莱尼|Marouane Fellaini|9|MID|-1
马蒂奇|Nemanja Matic|53|MID|-1
拉米雷斯|Ramires|77|MID|-1
迪亚比|Abou Diaby|10|MID|-1
博德梅尔|Mathieu Bodmer|10|MID|-1
古斯塔沃|Luiz Gustavo|77|MID|-1
杰拉德|Steven Gerrard|8|MID|-1
德罗西|Daniele De Rossi|67|MID|-1
比达尔|Arturo Vidal|77|MID|-1
赫迪拉|Sami Khedira|47|MID|-1
哈维·阿隆索|Xabier Alonso Olano|69|MID|-1
施魏因施泰格|Bastian Schweinsteiger|47|MID|-1
卡卡|Ricardo Izecson|65|MID|-1
鲁尼|Wayne Rooney|69|MID|18
托蒂|Francesco Totti|6|MID|-1
斯内德|Wesley Sneijder|47|MID|-1
巴拉克|Michael Ballack|27|MID|-1
斯塔姆|Jaap Stam|27|CB|-1
费迪南德|Rio Ferdinand|6|CB|-1
维迪奇|Nemanja Vidic|69|CB|-1
坎贝尔|Sol Campbell|93|CB|-1
马特拉齐|Marco Materazzi|27|CB|-1
拉莫斯|Sergio Ramos|8|CB|5
佩佩|Kepler Laveran|69|CB|-1
博阿滕|Jerome Boateng|53|CB|-1
瓦拉内|Raphael Varane|77|CB|-1
贝纳蒂亚|Medhi Benatia|77|CB|-1
大卫·路易斯|David Luiz|77|CB|-1
纳尔多|Ronaldo Aparecido|10|CB|-1
斯莫林|Chris Smalling|69|CB|-1
科斯切尔尼|Laurent Koscielny|77|CB|-1
胡梅尔斯|Mats Hummels|77|CB|-1
马蒂普|Joel Matip|69|CB|5
罗伯特·卡洛斯|Roberto Carlos Da Silva|93|FB|-1
阿什利·科尔|Ashley Cole|69|FB|-1
埃弗拉|Patrice Evra|69|FB|-1
阿比达尔|Eric Abidal|7|FB|-1
阿拉巴|David Alaba|77|FB|7
罗霍|Marcos Rojo|77|FB|7
克里希|Gael Clichy|8|FB|-1
马塞洛|Marcelo Vieira|53|FB|-1
麦孔|Maicon Douglas|10|FB|-1
博辛瓦|Jose Bosingwa|67|FB|-1
西西尼奥|Cicero Joao|65|FB|-1
拉姆|Philipp Lahm|77|FB|3
阿尔维斯|Daniel Alves|77|FB|-1
加里·内维尔|Gary Neville|49|FB|-1
卡福|Marcos De moraes|27|FB|-1
德马科斯|Oscar De Marcos|88|FB|3
范德萨|Edwin van der Sar|93|GK|-1
切赫|Petr Cech|7|GK|-1
诺伊尔|Manuel Neuer|77|GK|-1
库尔图瓦|Thibaut Courtois|77|GK|-1
德赫亚|David De Gea|53|GK|-1
布冯|Gianluigi Buffon|65|GK|-1'''
SEASONS={6:'06',7:'07',8:'08',9:'09',10:'10',11:'11',14:'14',27:'EL',49:'MUL',53:'14T',67:'08E',63:'06U',65:'06W',69:'10U',47:'10W',77:'14W',88:'17普卡',93:'WL'}
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def prepare():
 db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 names=[dict(r) for r in db.execute('SELECT playerid,full_eng FROM nameseng')]
 research=[]
 for file in ('roster36.json','attack-expanded.json','midfield-expanded.json','defense-expanded.json','fullbacks-expanded.json'):
  d=json.loads((R/'research-roster'/file).read_text('utf-8'))
  for key in ('cards','candidates','left_group','right_group','additional_candidates'):
   research.extend(d.get(key,[]))
 tree=ast.parse((S/'http_config.py').read_text('utf-8'));weights=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLE_WEIGHTS' for t in n.targets))
 roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
 stats='strength stamina acceleration sprintspeed jumping agility balance slidingtackle dribbling ballcontrol marking standingtackle crossing shortpassing finishing longpassing shotpower headingaccuracy longshots volleys curve freekickaccuracy penalties interceptions positioning vision reactions aggression gkkicking gkdiving gkhandling gkpositioning gkreflexes'.split()
 cards=[];issues=[]
 for line in DATA.splitlines():
  zh,pattern,sid,group,pos=line.split('|');sid=int(sid);pos=int(pos)
  found=[n for n in names if norm(pattern) in norm(n['full_eng'] or '') and db.execute('select 1 from players where playerid=? and spid>=1000000',(n['playerid'],)).fetchone()]
  if len(found)!=1:
   issues.append(dict(name=zh,pattern=pattern,matches=found));continue
  pid=found[0]['playerid'];spid=sid*1000000+pid;row=db.execute('select * from players where spid=?',(spid,)).fetchone()
  if row is None:
   issues.append(dict(name=zh,pid=pid,wanted=sid,available=[r[0]//1000000 for r in db.execute('select spid from players where playerid=? and spid>=1000000',(pid,))]));continue
  row=dict(row);primary=row['preferredposition1'] if pos<0 else pos;role=roles[primary]
  # Affine lift retains the ordering and spread of the donor's main-role skills.
  # All 33 stats use the same lift within outfield/GK domains; weak areas remain weak.
  target=89 if zh in ('博格巴','亚亚·图雷','埃辛','费莱尼','博德梅尔','德罗巴','斯塔姆','费迪南德','瓦拉内','罗霍') else 88
  if group=='GK':target=89
  relevant=stats[28:] if group=='GK' else stats[:28]
  base=sum(row[k]*v for k,v in weights[role].items())//100
  best=None
  for shift in range(0,71):
   new={k:(min(99,max(1,row[k]+shift)) if k in relevant else row[k]) for k in stats}
   value=sum(new[k]*v for k,v in weights[role].items())//100
   rank=(abs(value-target),sum(v==99 for v in new.values()),shift)
   if best is None or rank<best[0]:best=(rank,new,value,shift)
  _,new,value,shift=best;assert abs(value-target)<=1
  overrides={**new,'overallrating':value,'preferredposition1':primary}
  if primary!=row['preferredposition1']:
   secondary=[row['preferredposition1']]+[row['preferredposition'+str(i)] for i in range(2,5)]
   secondary=list(dict.fromkeys(p for p in secondary if p>=0 and p!=primary))[:3]
   overrides.update({'preferredposition'+str(i+2):secondary[i] if i<len(secondary) else -1 for i in range(3)})
  # Explicit requested Rojo identity: LB first, CB secondary.
  if zh=='罗霍':overrides.update(preferredposition2=5)
  evidence=[r for r in research if r.get('name_zh',r.get('name',''))==zh or (zh in r.get('name_zh',r.get('name','')) and len(zh)>=3)]
  cards.append(dict(name_zh=zh,name_en=found[0]['full_eng'],base_playerid=pid,template_spid=spid,template_season=sid,template_label=SEASONS[sid],group=group,source_row_sha256=digest(row),base_ovr=base,target_ovr=value,display_plus1_ovr=value+5,stat_lift=shift,fo3_overrides=overrides,model={k:row[k] for k in ('height','weight','headtypecode','headclasscode','bodytypecode','hashighqualityhead','skillmoves','weakfootabilitytypecode')},research=evidence))
 result=dict(schema=1,version='nostalgia-beasts-v1',season=dict(id=19,label='怀旧神兽',badge='OG'),cards=cards,count=len(cards),groups={g:sum(c['group']==g for c in cards) for g in ('ST','WIDE','MID','CB','FB','GK')},issues=issues,policy='one identity one new card; preserve every installed row, all user assets and sold pack contracts')
 (R/'roster-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps(dict(count=len(cards),groups=result['groups'],issues=issues),ensure_ascii=False,indent=2))
 return result
if __name__=='__main__':prepare()
