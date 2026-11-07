"""Exact -3 for the 67 season48 cards only; retain season49/55 and live assets."""
from pathlib import Path
import copy,datetime,json,shutil,sqlite3,sys
sys.dont_write_bytecode=True
import expand_service_legends as tx
from prepare import S,C,R as BASE,sha,write,STATS
common=tx.common;codec=tx.codec;util=tx.util
R=BASE/'main-minus3';R.mkdir(exist_ok=True)
SELF='patches/manutd_main_minus3_preflight.py';MANIFEST='patches/manutd-main-minus3-installed.json';RECEIPT='patches/manutd-main-minus3-receipt.json'
read=tx.read
def build():
 out=R/('build-'+datetime.datetime.now().strftime('%H%M%S-%f'));out.mkdir()
 sources=[S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/custom_rosters.json',S/'responses/static_roster.json'];baseline={str(p):sha(p) for p in sources}
 member='data/db2/fifadb.db.db2';decoded=bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(sources[1],member)));assert b'SQLite format 3\0'+decoded[16:]==sources[0].read_bytes()
 shutil.copyfile(sources[0],out/'fifadb.sqlite');weights=util.weights();ratings=[]
 with sqlite3.connect(out/'fifadb.sqlite') as db:
  db.row_factory=sqlite3.Row;oldrows=[dict(p) for p in db.execute('select * from players where spid/1000000=48')];assert len(oldrows)==67
  for row in oldrows:
   before=util.primary(row,weights);target=before-3;choices=[]
   for shift in range(-8,0):
    stats={k:max(1,row[k]+shift) for k in STATS};value=util.primary({**row,**stats},weights);choices.append(((abs(value-target),abs(shift+3)),stats,value,shift))
   _,stats,value,shift=min(choices,key=lambda c:c[0]);assert value==target
   changes={**stats,'overallrating':row['overallrating']-3,'potential':max(value,row['potential']-3)}
   db.execute('update players set '+','.join(k+'=?' for k in changes)+' where spid=?',list(changes.values())+[row['spid']])
   current=dict(db.execute('select * from players where spid=?',(row['spid'],)).fetchone());assert all(current[k]==v for k,v in row.items() if k not in changes)
   ratings.append(dict(spid=row['spid'],before=before+5,after=value+5,shift=shift,base_after=value))
  db.commit();db.execute('attach database ? as old',(str(sources[0]),))
  for table, in db.execute("select name from main.sqlite_master where type='table'").fetchall():
   where=' where spid/1000000<>48' if table=='players' else ''
   assert not db.execute('select * from main.'+table+where+' except select * from old.'+table+where+' limit 1').fetchone(),table
   assert not db.execute('select * from old.'+table+where+' except select * from main.'+table+where+' limit 1').fetchone(),table
   assert db.execute('select count(*) from main.'+table).fetchone()==db.execute('select count(*) from old.'+table).fetchone()
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  registry=read(sources[2]);lookup={r['spid']:r for r in ratings};count=0
  for card in registry['cards']:
   if card['fo3_spid'] in lookup:
    rating=lookup[card['fo3_spid']];card.update(display_plus1_ovr=rating['after'],base_ovr=rating['base_after']);count+=1
  assert count==67;write(out/'custom_rosters.json',registry)
  roster=read(sources[3]);original=copy.deepcopy(roster['seasons']);rankings=[]
  for i,e in enumerate(roster['seasons']):
   vals=[util.primary(dict(p),weights)+5 for p in db.execute('select * from players where spid/1000000 in ('+','.join('?' for _ in e['value'])+')',e['value'])];assert vals
   rankings.append((sum(vals)/len(vals),max(vals),i,e))
  rankings.sort(key=lambda r:(-r[0],-r[1],r[2]));roster['seasons']=[r[3] for r in rankings]
  assert sorted(json.dumps(e,sort_keys=True) for e in original)==sorted(json.dumps(e,sort_keys=True) for e in roster['seasons']);write(out/'static_roster.json',roster)
 big=out/'data_0.big';shutil.copyfile(sources[1],big);encoded=util.encrypted_sqlite(decoded,(out/'fifadb.sqlite').read_bytes());codec.replace_member(big,member,codec.refpack(encoded),len(encoded))
 assert b'SQLite format 3\0'+bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(big,member)))[16:]==(out/'fifadb.sqlite').read_bytes()
 oldentries=codec.bigdir.entries(sources[1]);entries=codec.bigdir.entries(big);a=sources[1].read_bytes();b=big.read_bytes();assert len(entries)==len(oldentries)
 for p,q in zip(oldentries,entries):
  assert p[0]==q[0]
  if p[0]!=member:assert a[p[1]:p[1]+p[2]]==b[q[1]:q[1]+q[2]],p[0]
 checker=common.load(S/'tools/player_import/check.py','main_minus3_semantics');certificate=checker.validate(S,C,database=out/'fifadb.sqlite',data0=big,registry=out/'custom_rosters.json',full=True);assert certificate['status']=='PLAYER_IMPORT_FULL_PASS';write(out/'player-import-validation.json',certificate)
 for p,h in baseline.items():assert sha(p)==h,('Concurrent source changed',p)
 report=dict(status='BUILT_SEMANTICS_PASS',baseline=baseline,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()},ratings=ratings,changed=67,main_season=48,legacy_seasons_49_55_exact=True,all_non_target_rows_exact=True,other_big_members_exact=True,rating_range=[min(r['after'] for r in ratings),max(r['after'] for r in ratings)],state_shop_written=False,native_ui_verified=False)
 write(out/'build.json',report);write(R/'latest-build.json',dict(path=str(out)));print(json.dumps(dict(status=report['status'],changed=67,range=report['rating_range'],build=str(out))),flush=True)
 return out
def plan(out,unused=None):
 data=read(out/'build.json')
 for p,h in data['baseline'].items():assert sha(p)==h,('Rebuild required',p)
 for name,h in data['outputs'].items():assert sha(out/name)==h
 play,match,parentrel,parent=tx.top();prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','minus3_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 helper=(S/parentrel).read_text('utf8').replace(Path(parent.MANIFEST).name,Path(MANIFEST).name).replace(Path(parent.RECEIPT).name,Path(RECEIPT).name).replace(Path(parentrel).stem,Path(SELF).stem).replace(read(S/parent.RECEIPT)['status'],'INSTALLED_MANUTD_MAIN_MINUS3').replace(prior['status'],'MANUTD_MAIN_MINUS3_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 revision='manutd-main-minus3-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');doc='docs/工程经验与修改边界.txt'
 note='\n\nFO3-MU-MAIN-MINUS3（2026-11-07，'+revision+'，实机PENDING）\n用户最终明确只将主赛季48的67张统一-3；合并筛选中49/55的另外12张原行精确保持。67张主位置1级+1实际OVR逐卡恰好-3，主池90～94变87～91；原技能分布平移校准，overallrating同步-3，potential下调并不低于主位置基础能力。除67行技能/overall/potential，其它全部SQLite行与表、球员身份/模型/身体/位置/特性保持；现有强化等级经验不写。注册表67条当前显示/base值同步，筛选仅按新平均强度排序，不增删赛季。data0只有UI SQLite成员替换，其它压缩成员保持；完整导入语义检查与新证书同步。\n市场已有初价/现价/成交事件、已售和现售卡包配置/概率/报价、真实state/shop不改。安装采用最新父层、共同双锁、正常退出客户端后停服新快照及逐文件CAS/备份，所有父guard和回执策略继承。资源/语义/API验证不冒充游戏内或比赛验收。证据D:/fifaol3/manutd-legends/main-minus3。\n'
 payload=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('client','data/data_0.big',out/'data_0.big'),('server','gamedata/custom_rosters.json',out/'custom_rosters.json'),('server','responses/static_roster.json',out/'static_roster.json'),('server','gamedata/player-import-validation.json',out/'player-import-validation.json'),('server',doc,(S/doc).read_bytes()+note.encode('utf8')),('server',SELF,helper.encode('utf8')),('server','play-local.bat',play.replace(match,SELF.replace('/','\\').encode()))];entries=[]
 for root,rel,source in payload:
  target=(S if root=='server' else C)/rel;before=sha(target) if target.exists() else None;after=common.digest(source) if isinstance(source,bytes) else sha(source);key=(root,rel.casefold())
  if key in table:assert table[key]['sha256']==before
  else:assert not target.exists()
  table[key]=dict(root=root,relative=rel,sha256=after);entries.append(dict(root=root,relative=rel,target=target,source=source,before=before,after=after))
 comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='manutd-main67-minus3',native_status='PENDING'))
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parentrel,parent_preflight_sha256=sha(S/parentrel),build_sha256=sha(out/'build.json'))
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_MANUTD_MAIN_MINUS3',revision=revision,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,body in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=body,before=None,after=common.digest(body)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=revision,prior=prior)
def install(out):
 tx.R=R;tx.SELF=SELF;tx.MANIFEST=MANIFEST;tx.RECEIPT=RECEIPT;tx.plan=plan;tx.fresh_market=lambda _:None;tx.install(out)
if __name__=='__main__':
 if '--install' in sys.argv:install(Path(read(R/'latest-build.json')['path']))
 else:build()
