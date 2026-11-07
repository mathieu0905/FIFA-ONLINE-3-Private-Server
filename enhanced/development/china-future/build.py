"""Additive, sourced China Future cards; no writes to formal files or assets."""
from pathlib import Path
from contextlib import closing
import ast,datetime,hashlib,json,shutil,sqlite3,sys,unicodedata
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');SID=327
sys.path[:0]=[str(R.parent/'upstream-review/deps'),str(S/'tools/player_import'),str(S/'tools/re'),str(S)]
from PIL import Image,ImageDraw,ImageFont
import bigdir,native_db,ordered_big,extract_fifadb as codec,refpack
from cryptography.hazmat.primitives.ciphers import Cipher,modes
try:from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def seal(data):
 enc=Cipher(Blowfish(codec.KEY),modes.ECB()).encryptor();raw=codec.swap32(enc.update(codec.swap32(data))+enc.finalize())
 return refpack.refpack(raw),len(raw)

# Ratings are explicit user-requested fantasy potential, not official EA ratings.
# Body dimensions are gameplay profiles, not assertions about the real athletes.
SQUAD=[
 ('王钰栋','Yudong Wang','2006-11-23',27,92,180,75),
 ('李昊炎','Haoyan Li','2012-01-28',27,92,176,62),
 ('李昊','Hao Li','2004-03-06',0,90,185,75),
 ('向余望','Yuwang Xiang','2003-12-18',21,90,177,72),
 ('蒯纪闻','Jiwen Kuai','2006-02-28',18,90,174,68),
 ('刘诚宇','Chengyu Liu','2006-07-02',25,89,183,76),
 ('毛伟杰','Weijie Mao','2005-05-28',16,89,176,69),
 ('李新翔','Xinxiang Li','2005-11-30',23,88,181,73),
 ('依木兰·买买提','Imran Memet','2005-05-03',10,88,179,72),
 ('杨皓宇','Haoyu Yang','2006-05-25',14,87,180,72),
 ('胡荷韬','Hetao Hu','2003-10-05',7,89,175,70),
 ('吾米提江·玉苏普','Umidjan Yusup','2004-02-28',5,88,182,78),
 ('彭啸','Xiao Peng','2005-07-28',5,88,189,80),
 ('刘浩帆','Haofan Liu','2003-10-23',5,87,187,78),
 ('汪士钦','Shiqin Wang','2003-06-24',3,86,182,73),
 ('姚浩洋','Haoyang Yao','2006-10-28',0,85,195,82),
 ('邝兆镭','Zhaolei Kuang','2009-03-13',23,91,178,69),
 ('万项','Xiang Wan','2009-04-21',18,91,178,68),
 ('谢晋','Jin Xie','2009-08-21',16,90,175,66),
 ('周雨诺','Yunuo Zhou','2009-02-26',14,90,178,69),
 ('帅惟浩','Weihao Shuai','2009-01-05',25,90,184,76),
 ('吕孟洋','Mengyang Lyu','2009-08-01',23,89,176,68),
 ('金昱成','Yucheng Jin','2009-06-15',5,88,187,78),
 ('南子勋','Zixun Nan','2009-03-23',5,87,185,77),
 ('李钧鹏','Junpeng Li','2009-02-19',7,87,178,70),
 ('张旭尧','Xuyao Zhang','2009-03-22',3,87,179,71),
 ('秦子牛','Ziniu Qin','2009-07-10',0,87,190,78),
 ('江承恩','Chengen Jiang','2010-05-02',0,86,190,76),
 ('潘朝伟','Chaowei Pan','2010-02-25',10,88,177,68),
 ('徐正鹏','Zhengpeng Xu','2009-03-15',14,86,178,69),
 ('赵松源','Songyuan Zhao','2009-04-07',25,87,184,75),
 ('顾博宇','Boyu Gu','2009-04-27',7,86,178,70),
]
SOURCES={
 '李昊炎':'https://www.cfdamm.cat/ca/equip/persona/haoyan-li',
 '依木兰·买买提':'https://tyj.xinjiang.gov.cn/xjtyj/xjtt/202507/612fbe8232734c2793284030a6435b67.shtml',
 '汪士钦':'https://www.thecfa.cn/thecfa/upload/20210312/20210312144717515.pdf',
 '王钰栋':'https://eaff.com/competitions/eaff2025/china_m_k.html',
 '李昊':'https://assets.the-afc.com/2024_AFC_U23_Asian_Cup/Downloads/Squad_List/AFC-U23-Asian-Cup-Qatar-2024%E2%84%A2---Squad-Lists-(Completed-April-9).pdf',
 '胡荷韬':'https://assets.the-afc.com/2024_AFC_U23_Asian_Cup/Downloads/Squad_List/AFC-U23-Asian-Cup-Qatar-2024%E2%84%A2---Squad-Lists-(Completed-April-9).pdf',
 '刘浩帆':'https://assets.the-afc.com/2024_AFC_U23_Asian_Cup/Downloads/Squad_List/AFC-U23-Asian-Cup-Qatar-2024%E2%84%A2---Squad-Lists-(Completed-April-9).pdf',
}

def norm(s):return ''.join(sorted(''.join(c for c in unicodedata.normalize('NFKD',s).lower() if c.isalnum() or c==' ').split()))
def birth(s):
 for fmt in ['%m/%d/%Y %I:%M:%S %p','%Y-%m-%d','%a, %d %b %Y %H:%M:%S GMT']:
  try:return datetime.datetime.strptime(s,fmt).date().isoformat()
  except ValueError:pass
 raise ValueError('Unknown birth format '+s)

def main():
 out=R/'input';out.mkdir(exist_ok=True);portraits=out/'portraits';portraits.mkdir(exist_ok=True)
 inputs=[S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',S/'gamedata/player-imports.json',S/'http_config.py',S/'responses/static_roster.json',C/'data/data_0.big',C/'data/ui/components/Label.big',S/'patches/Label.big']
 baseline={str(p):sha(p) for p in inputs}
 db=out/'fifadb.sqlite'
 with closing(sqlite3.connect(inputs[0].as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(db)) as dst:src.backup(dst)
 con=sqlite3.connect(db);con.row_factory=sqlite3.Row
 assert con.execute('select count(*) from players where spid/1000000=?',(SID,)).fetchone()[0]==0
 registry=json.loads(inputs[1].read_text('utf8'));policy=json.loads(inputs[2].read_text('utf8'))
 raw=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db');meta=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode()
 *_,table,fields=native_db.player_table(raw,meta)
 natives={table.get(r,fields['playerid']['shortname']):r for r in table.rows}
 candidates=con.execute('select * from players where nationality=155 and headclasscode=1 and headtypecode<30001 group by playerid').fetchall()
 def value(row,f):return table.get(row,fields[f]['shortname'])+int(fields[f]['rangelow'])
 templates=[p for p in candidates if p['playerid'] in natives and all(value(natives[p['playerid']],f)==p[f] for f in ('headclasscode','headtypecode','skintonecode'))]
 assert templates
 tree=ast.parse(inputs[3].read_text('utf8'))
 weights=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLE_WEIGHTS' for t in n.targets)))
 roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
 columns=[r[1] for r in con.execute('pragma table_info(players)')];stats=set().union(*weights.values())
 perms=[r[0] for r in con.execute("select name from sqlite_master where type='table' and name like 'perm%'")]
 names=list(con.execute('select p.playerid,p.birthdate,n.full,n.full_eng,n.short_eng,z.full as zh from players p join nameseng n on n.playerid=p.playerid left join nameschi z on z.playerid=p.playerid group by p.playerid'))
 langnames={lang:[] for lang in ('eng','chi','ind','kor','tha','vie')};cards=[];generic=[]
 font=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',17)
 for ix,(zh,en,dob,pos,target,height,weight) in enumerate(SQUAD):
  matches=[r['playerid'] for r in names if birth(r['birthdate'])==dob and (norm(en) in {norm(r['full']),norm(r['full_eng']),norm(r['short_eng'])} or r['zh']==zh)]
  if matches:raise ValueError('Existing same identity needs explicit reuse, do not duplicate: '+zh+str(matches))
  pid=710000+ix
  assert pid not in natives and not con.execute('select 1 from players where playerid=?',(pid,)).fetchone()
  template=next((t for t in templates if t['preferredposition1']==pos),templates[ix%len(templates)])
  row=dict(template);d=datetime.date.fromisoformat(dob)
  row.update(playerid=pid,spid=SID*1000000+pid,birthdate=f'{d.month}/{d.day}/{d.year} 12:00:00 AM',height=height,weight=weight,
    preferredposition1=pos,preferredposition2=-1,preferredposition3=-1,preferredposition4=-1,
    nationality=155,nationalteamid=155,teamid=241 if zh=='李昊炎' else -1,leagueid=-1,
    potential=99,internationalrep=1,skillmoves=native_db.stars_to_code(2 if pos==0 else 4),weakfootabilitytypecode=3,
    attackingworkrate=0 if pos==0 else 2,defensiveworkrate=2 if pos<=11 else 1,trait1=0,trait2=0,overallrating=target)
  for k in stats:row[k]=target-5 if pos!=0 else (target-5 if k.startswith('gk') or k=='reactions' else 35)
  if pos>19:
   for k,v in dict(acceleration=7,sprintspeed=7,dribbling=4,agility=4,finishing=2,strength=-8,marking=-32,slidingtackle=-32,standingtackle=-32,interceptions=-30).items():row[k]+=v
  elif pos<=8 and pos:
   for k,v in dict(marking=4,standingtackle=5,slidingtackle=3,interceptions=4,strength=3,finishing=-28,positioning=-15,dribbling=-5).items():row[k]+=v
  elif pos:
   for k,v in dict(shortpassing=5,longpassing=4,vision=4,ballcontrol=4,stamina=4,finishing=-8).items():row[k]+=v
  w=weights[roles[pos]];current=lambda:sum(row[k]*v for k,v in w.items())//100
  delta=target-5-current()
  for k in w:row[k]+=delta
  assert current()+5==target and all(1<=row[k]<=99 for k in stats)
  con.execute('insert into players('+','.join(columns)+') values('+','.join('?' for _ in columns)+')',[row[k] for k in columns])
  for p in perms:con.execute('insert into '+p+'(spid,licensed,transferable) values(?,1,1)',(row['spid'],))
  for lang in langnames:
   full=zh if lang=='chi' else en;values=(pid,full,full,en,en,en.split()[-1])
   con.execute('insert into names'+lang+'(playerid,full,short,full_eng,short_eng,jersey) values(?,?,?,?,?,?)',values);langnames[lang].append(values)
  img=Image.new('RGBA',(128,128),(0,0,0,0));draw=ImageDraw.Draw(img)
  draw.ellipse((44,8,84,48),fill='#c4a764');draw.rounded_rectangle((23,53,105,103),radius=27,fill='#a72732')
  draw.text((64,107),zh,fill='#f6de9c',font=font,anchor='mt');img.save(portraits/f'p{row["spid"]}.png')
  source=SOURCES.get(zh,('https://www.thecfa.cn/jxtz/20261028/38339.html' if ix>=16 and zh not in ('谢晋','吕孟洋') else 'https://zh.wikipedia.org/wiki/'+zh))
  card=dict(fo3_spid=row['spid'],base_playerid=pid,name_en=en,name_zh=zh,season_id=SID,
    season=dict(seasonId=SID,className='中国明日之星'),source_url=source,
    appearance_route='fo3_builtin_generic',portrait_kind='explicit_named_generic_silhouette',
    mapping_rule=dict(attributes='User-requested fantasy potential: +1 LV1 no colors = target; weighted position OVR +5, not raw overallrating alone',target_plus1_lv1=target,body_profile='custom gameplay dimensions; not official current measurements',birthdate=dob,source_skill_stars=2 if pos==0 else 4))
  registry['cards'].append(card);cards.append(dict(card,position=pos,template_playerid=template['playerid']))
  digest=hashlib.sha256(json.dumps(card,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  generic.append(dict(playerid=pid,spid=row['spid'],template_playerid=template['playerid'],skill_input='fo3-code',native_spid_mode='identity',appearance_route='fo3_builtin_generic',source_sha256=digest))
  policy['source_skill_semantics'].append(dict(spid=row['spid'],playerid=pid,skill_input='fo3-code',value=row['skillmoves']))
 con.commit();assert con.execute('pragma integrity_check').fetchone()[0]=='ok';con.close()
 registry['seasons'].append(dict(id=SID,label='中国明日之星',source='User fantasy potential edition; real identities with explicit generic appearance',cards=[c['fo3_spid'] for c in cards]))
 write(out/'custom_rosters.json',registry);write(out/'player-imports.json',policy);write(out/'cards.json',cards)
 write(out/'appearance-spec.json',dict(schema=1,players=[],generic_players=generic))
 changes={'data/db2/fifadb.db.db2':seal(db.read_bytes())}
 for lang,values in langnames.items():
  member=f'data/db2/{lang}.db.db2';raw=codec.decrypt(bigdir.read(C/'data/data_0.big',member))
  loc=sqlite3.connect(':memory:');loc.deserialize(b'SQLite format 3\0'+bytes(raw[16:]));loc.executemany('insert into names(playerid,full,short,full_eng,short_eng,jersey) values(?,?,?,?,?,?)',values);loc.commit()
  changes[member]=seal(loc.serialize());loc.close()
 ordered_big.rebuild(C/'data/data_0.big',out/'data_0.big',changes)
 assert baseline=={str(p):sha(p) for p in inputs};write(out/'baseline.json',baseline)
 source=inputs[3].read_text('utf8')
 assert source.count('TC_LEGENDS = (93, 30, 27, 71, 51, 61, 89, 48, 55, 49)')==1
 source=source.replace('TC_LEGENDS = (93, 30, 27, 71, 51, 61, 89, 48, 55, 49)','TC_LEGENDS = (93, 30, 27, 71, 51, 61, 89, 48, 55, 49, 327)')
 source=source.replace('s // 1000000 == 84]','s // 1000000 in (84, 327)]',1)
 source=source.replace('首发传奇时刻球员3–5人+4','首发传奇时刻/中国明日之星球员3–5人+4',1)
 source=source.replace('NOT IN (300,325) AND ovr','NOT IN (300,325,327) AND ovr',1)
 # Append a dedicated season color and allow a shared original moments-season base.
 source=source.replace('return (("07", (7,)),) + tuple((label, codes) for label, codes, _ in FA_SEASONS)', 'return (("07", (7,)), ("中国明日之星", (327,))) + tuple((label, codes) for label, codes, _ in FA_SEASONS)')
 compile(source,'http_config.py','exec');(R/'http_config.py').write_text(source,'utf8',newline='\n')
 roster=json.loads(inputs[4].read_text('utf8'));roster['seasons'].insert(0,dict(season='中国明日之星',value=[SID],open='2013-01-01T00:00:00.000Z',close='2099-12-31T00:00:00.000Z'));write(R/'static_roster.json',roster)
 write(R/'roster-review.json',dict(season=SID,label='中国明日之星',cards=cards,rating_semantics='+1 LV1 without team colors',legend_base_membership=True,moments_feature_membership=True,native_verified=False))
 print(json.dumps(dict(status='PREPARED_UI_ONLY',cards=len(cards),new_identities=len(generic),season=SID)))

if __name__=='__main__':main()
