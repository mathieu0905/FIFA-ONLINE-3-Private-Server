from pathlib import Path
import sys,json,sqlite3,hashlib,struct,re,zlib,importlib.util
sys.dont_write_bytecode=True
ROOT=Path(__file__).parent;OUT=ROOT/'evidence';OUT.mkdir(exist_ok=True)
db=Path(r'D:\FO3ID\server\gamedata\fifadb.sqlite')
c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
statepath=Path(r'D:\FO3ID\server\gamedata\state.json');raw=statepath.read_bytes();s=json.loads(raw)
names=[dict(r) for r in c.execute("SELECT * FROM nameseng WHERE lower(full_eng) LIKE '%basten%'")]
pids={r['playerid'] for r in names}
rows=[dict(r) for r in c.execute('SELECT spid,playerid,acceleration,sprintspeed,agility,balance,dribbling,ballcontrol,stamina FROM players') if r['playerid'] in pids]
cards=[dict(slot=slot,card=p) for slot,t in s['teams'].items() for p in t.get('players',[]) if int(p.get('spid',0)) in {r['spid'] for r in rows}]
report=dict(state_sha256=hashlib.sha256(raw).hexdigest(),names=names,base_attributes=rows,owned_cards=cards,read_only=True)
(OUT/'van-basten-data.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
spec=importlib.util.spec_from_file_location('fo3abc',r'D:\FO3ID\server\tools\re\abc.py');abc=importlib.util.module_from_spec(spec);spec.loader.exec_module(abc)
path=Path(r'D:\FO3ID\32795\data\ui\libs\Module.big');gfx=bigdir.read(path,'data/ui/libs/Module.gfx')
data=b'FWS'+gfx[3:8]+zlib.decompress(gfx[8:]) if gfx[:3]==b'CFX' else gfx
found=[]
for match in re.finditer(bytes.fromhex('10002e00'),data):
 try:A=abc.parse(data,match.start())
 except Exception:continue
 methods={}
 for cls,sup,ii,it,ci,ct in A['cls']:
  methods[ii]=cls+'.<init>';methods[ci]=cls+'.<cinit>'
  for kind,tn,m in it+ct:
   if kind in ('method','get','set'):methods[m]=cls+'.'+tn
 for mi,code in A['body'].items():
  label=methods.get(mi,'closure '+str(mi))
  if any(k in label for k in ('fillPlayerStaticData','totalBonus','applyPlayerGrade','getBoostStatPoint')) or (mi==53 and any('fillPlayerStaticData' in v for v in methods.values())):
   found.append(f'### {label} ABC {match.start():#x} method {mi}\n'+ '\n'.join(abc.dis(A,code)))
(OUT/'current-ui-attribute-chain.txt').write_text('Module SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest()+'\n\n'+'\n\n'.join(found),encoding='utf8')
print('UI methods:',len(found))
