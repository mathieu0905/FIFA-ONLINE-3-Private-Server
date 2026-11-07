"""Strengthen only season 84 native trait/badge fields in offline work products."""
from pathlib import Path
import sys,sqlite3,collections,json,shutil,hashlib,importlib.util
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load(R.parent/'im-balance30/build.py','prior_im_codec')
VISIBLE=set(range(30))-{2,8,17}
NEGATIVE={0,3,4,6,9,11}
GK={20,21,23};OUTFIELD=set(range(30))-GK-{19}
POSITIVE=set(range(30))-NEGATIVE
GOLD={14,15,16}
NAMES=['INFLEXIBILITY','LONG_THROW_IN','TAKES_POWERFUL_DRIVEN_FREE_KICKS','DIVER','INJURY_PRONE','SOLID_PLAYER','AVOIDS_USING_WEAKER_FOOT','DIVES_INTO_TACKLES','TRIES_TO_BEAT_OFFSIDE_TRAP','SELFISH','LEADERSHIP','ARGUES_WITH_OFFICIALS','EARLY_CROSSER','FINESSE_SHOT','FLAIR','LONG_PASSER','LONG_SHOT_TAKER','SPEED_DRIBBLER','PLAY_MAKER','PUSHES_UP_FOR_CORNERS','PUNCHER','GK_LONG_THROWER','POWER_HEADER','GK_ONE_ON_ONES','GIANT_THROW_IN','OUTSIDE_FOOT_SHOT','CROWD_FAVOURITE','SWERVE','SECOND_WIND','ACROBATIC_CLEARANCE']
def bits(n):return {i for i in range(30) if n&(1<<i)}
def mask(v):return sum(1<<i for i in v)
def role(p):
 pos=p['preferredposition1']
 return 'gk' if pos==0 else 'df' if pos<=8 else 'mf' if pos<=18 else 'fw'
PREFERRED={'gk':[23,21,20,5,10,28,26],
 'df':[29,22,5,10,28,15,12,18,27,25,13,16,14,26],
 'mf':[18,15,14,27,28,13,16,25,12,5,10,22,29,26],
 'fw':[13,25,14,22,27,28,16,5,10,18,15,12,29,26]}
ROLE_BADGES={'df':[14,9,10,12,2,7,5], 'mf':[15,4,5,6,3,7,8,11,12], 'fw':[16,13,0,1,3,2,6,11,12]}
def enhance(p,others):
 r=role(p);allowed=POSITIVE&({20,21,23,5,10,28,26} if r=='gk' else OUTFIELD)
 before=bits(p['trait1']);other_good=[bits(o['trait1'])&allowed for o in others]
 original_good=before&allowed
 new=before|set().union(*other_good)
 target=max(len(original_good&VISIBLE)+1,max((len(v&VISIBLE) for v in other_good),default=0)+1)
 # Each goalkeeper gets all three supported keeper traits, plus stamina/solid
 # player leadership as needed; never invent a gold goalkeeper badge.
 required={20,21,23} if r=='gk' else set(PREFERRED[r][:3])
 new|=required
 for i in PREFERRED[r]:
  if len(new&allowed&VISIBLE)>=target:break
  new.add(i)
 if len(new&allowed&VISIBLE)<target:raise RuntimeError('No safe supported extra trait for '+str(p['spid']))
 badges=p['badges']
 if r!='gk':
  badges|=mask(set().union(*(bits(o['badges']) for o in others)))
  badges|=1<<ROLE_BADGES[r][0]
  target_badges=max(o['badges'].bit_count() for o in others)+1
  for i in ROLE_BADGES[r][1:]:
   if badges.bit_count()>=target_badges:break
   badges|=1<<i
 after={**p,'trait1':mask(new),'badges':badges}
 assert after['trait1']|p['trait1']==after['trait1']
 assert after['badges']|p['badges']==after['badges']
 return after,dict(role=r,added_traits=[NAMES[i] for i in sorted(new-before)],
  strongest_other_visible_positive=max((len(v&VISIBLE) for v in other_good),default=0),
  visible_positive_before=len(original_good&VISIBLE),visible_positive_after=len(new&allowed&VISIBLE),
  gold_before=sorted(bits(p['badges'])&GOLD),gold_after=sorted(bits(badges)&GOLD),
  added_badges=sorted(bits(badges)-bits(p['badges'])),keeper_gold_invented=False)
def build():
 out=R/'trait-build';out.mkdir(exist_ok=True)
 paths=[S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/custom_rosters.json']
 baseline={str(p):base.sha(p) for p in paths}
 db=sqlite3.connect(paths[0].as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 rows=[dict(r) for r in db.execute('SELECT * FROM players WHERE spid>=1000000')]
 people=collections.defaultdict(list)
 for p in rows:people[p['playerid']].append(p)
 names={pid:n for pid,n in db.execute('SELECT playerid,short FROM nameschi')}
 target=out/'fifadb.sqlite'
 if target.exists():target.unlink()
 with sqlite3.connect(target,uri=True) as t:db.backup(t)
 db.close();registry=json.loads(paths[2].read_text('utf8'));entries={r['fo3_spid']:r for r in registry['cards']}
 changes=[]
 with sqlite3.connect(target,uri=True) as t:
  for p in rows:
   if p['spid']//1000000!=84:continue
   others=[o for o in people[p['playerid']] if o['spid']//1000000!=84]
   if not others:raise RuntimeError('No comparison season for '+str(p['spid']))
   after,evidence=enhance(p,others)
   t.execute('UPDATE players SET trait1=?,badges=? WHERE spid=?',(after['trait1'],after['badges'],p['spid']))
   change=dict(spid=p['spid'],playerid=p['playerid'],name=names.get(p['playerid']),before=p,after=after,**evidence)
   changes.append(change);entries[p['spid']]['native_trait_upgrade']=dict(revision='im-native-traits-v1',**evidence)
  t.commit();t.execute('ATTACH DATABASE ? AS baseline',(paths[0].as_uri()+'?mode=ro',))
  for table, in t.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
   q='"'+table.replace('"','""')+'"';cols=[x[1] for x in t.execute('PRAGMA table_info('+q+')')]
   if table=='players':
    selected=','.join('"'+v+'"' for v in cols if v not in ('trait1','badges'))
   else:selected='*'
   assert t.execute('SELECT count(*) FROM main.'+q).fetchone()==t.execute('SELECT count(*) FROM baseline.'+q).fetchone()
   assert not t.execute('SELECT '+selected+' FROM main.'+q+' EXCEPT SELECT '+selected+' FROM baseline.'+q+' LIMIT 1').fetchone(),table
   assert not t.execute('SELECT '+selected+' FROM baseline.'+q+' EXCEPT SELECT '+selected+' FROM main.'+q+' LIMIT 1').fetchone(),table
  assert not t.execute('SELECT * FROM main.players WHERE spid/1000000!=84 EXCEPT SELECT * FROM baseline.players WHERE spid/1000000!=84 LIMIT 1').fetchone()
  assert t.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 base.save(out/'custom_rosters.json',registry);base.save(out/'changes.json',changes)
 decoded=bytes(base.extract_fifadb.decrypt(base.bigdir.read(paths[1],base.MEMBER)))
 assert b'SQLite format 3\0'+decoded[16:]==paths[0].read_bytes()
 plain=target.read_bytes();enc=base.Cipher(base.Blowfish(base.extract_fifadb.KEY),base.modes.ECB()).encryptor()
 encrypted=base.extract_fifadb.swap32(enc.update(base.extract_fifadb.swap32(decoded[:16]+plain[16:]))+enc.finalize())
 big=out/'data_0.big';shutil.copyfile(paths[1],big);packed=base.refpack(encrypted)
 base.replace_member(big,base.MEMBER,packed,len(encrypted))
 assert b'SQLite format 3\0'+bytes(base.extract_fifadb.decrypt(base.bigdir.read(big,base.MEMBER)))[16:]==plain
 layout=load(S/'tools/check_data0_layout.py','trait_layout').inspect(big,baseline=paths[1],changed_members={base.MEMBER},expected_count=len(base.bigdir.entries(paths[1])))
 assert layout['status']=='PASS';base.save(out/'layout.json',layout)
 cert=load(S/'tools/player_import/check.py','trait_import_check').validate(S,C,database=target,data0=big,registry=out/'custom_rosters.json',full=True)
 base.save(out/'player-import-validation.json',cert)
 assert baseline=={str(p):base.sha(p) for p in paths},'Production baseline changed; rebuild'
 report=dict(status='OFFLINE_BUILD_PASS_INSTALL_DEFERRED',cards=len(changes),outfield=sum(r['role']!='gk' for r in changes),goalkeepers=sum(r['role']=='gk' for r in changes),
  outfield_with_native_gold=sum(bool(r['gold_after']) for r in changes if r['role']!='gk'),all_have_more_visible_positive_traits=True,
  only_fields=['trait1','badges'],all_non_IM_rows_exact=True,all_other_tables_exact=True,full_import=cert['status'],layout=layout['status'],
  baseline=baseline,outputs={n:base.sha(out/n) for n in ('fifadb.sqlite','data_0.big','custom_rosters.json','changes.json','player-import-validation.json')},
  formal_written=False,game_gui_used=False,native_verified=False,match_verified=False)
 base.save(out/'report.json',report);print(json.dumps(report,ensure_ascii=True));return report
if __name__=='__main__':build()

