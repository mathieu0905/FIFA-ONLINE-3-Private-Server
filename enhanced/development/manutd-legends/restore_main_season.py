"""Restore only the 67 main-season cards' prior three-point attribute change."""
from pathlib import Path
import copy,datetime,json,shutil,sqlite3,sys
sys.dont_write_bytecode=True
import reduce_main_season as previous
from prepare import S,C,R as BASE,sha,write,STATS
tx=previous.tx;common=previous.common;codec=previous.codec;util=previous.util;read=previous.read
R=BASE/'main-restore-three';R.mkdir(exist_ok=True)
SELF='patches/manutd_main_restored_preflight.py';MANIFEST='patches/manutd-main-restored-installed.json';RECEIPT='patches/manutd-main-restored-receipt.json'
def build():
 out=R/('build-'+datetime.datetime.now().strftime('%H%M%S-%f'));out.mkdir()
 sources=[S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/custom_rosters.json',S/'responses/static_roster.json'];baseline={str(p):sha(p) for p in sources}
 prior=read(previous.R/'installed.json');journal=read(Path(prior['backup'])/'transaction.json');original=Path(prior['backup'])/str(next(i for i,r in enumerate(journal['files']) if r['relative']=='gamedata/fifadb.sqlite'))
 previous_output=Path(prior['build'])/'fifadb.sqlite';member='data/db2/fifadb.db.db2';decoded=bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(sources[1],member)));assert b'SQLite format 3\0'+decoded[16:]==sources[0].read_bytes()
 shutil.copyfile(sources[0],out/'fifadb.sqlite');weights=util.weights();ratings=[];allowed=STATS+['overallrating','potential']
 with sqlite3.connect(out/'fifadb.sqlite') as db:
  db.row_factory=sqlite3.Row;db.execute('attach database ? as before_reduction',(str(original),));db.execute('attach database ? as reduced',(str(previous_output),));db.execute('attach database ? as live',(str(sources[0]),))
  rows=[dict(p) for p in db.execute('select * from players where spid/1000000=48')];assert len(rows)==67
  for row in rows:
   spid=row['spid'];saved=dict(db.execute('select * from before_reduction.players where spid=?',(spid,)).fetchone());reduced=dict(db.execute('select * from reduced.players where spid=?',(spid,)).fetchone())
   assert all(row[k]==reduced[k] for k in allowed),('Intervening card attribute edit; re-evaluate before restoring',spid)
   before=util.primary(row,weights);changes={k:saved[k] for k in allowed};current={**row,**changes};after=util.primary(current,weights);assert after==before+3 and current['overallrating']==row['overallrating']+3
   db.execute('update players set '+','.join(k+'=?' for k in allowed)+' where spid=?',list(changes.values())+[spid]);assert all(current[k]==v for k,v in row.items() if k not in allowed)
   ratings.append(dict(spid=spid,before_base=before,after_base=after,overallrating=current['overallrating']))
  db.commit()
  for table, in db.execute("select name from main.sqlite_master where type='table'").fetchall():
   where=' where spid/1000000<>48' if table=='players' else ''
   assert not db.execute('select * from main.'+table+where+' except select * from live.'+table+where+' limit 1').fetchone(),table
   assert not db.execute('select * from live.'+table+where+' except select * from main.'+table+where+' limit 1').fetchone(),table
   assert db.execute('select count(*) from main.'+table).fetchone()==db.execute('select count(*) from live.'+table).fetchone()
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  registry=read(sources[2]);lookup={r['spid']:r for r in ratings};count=0
  for card in registry['cards']:
   if card['fo3_spid'] in lookup:
    value=lookup[card['fo3_spid']]['after_base'];card.update(base_ovr=value,display_plus1_ovr=value+5);count+=1
  assert count==67;write(out/'custom_rosters.json',registry)
  roster=read(sources[3]);original_entries=copy.deepcopy(roster['seasons']);scores=[]
  for i,e in enumerate(roster['seasons']):
   values=[util.primary(dict(p),weights) for p in db.execute('select * from players where spid/1000000 in ('+','.join('?' for _ in e['value'])+')',e['value'])];assert values;scores.append((sum(values)/len(values),max(values),i,e))
  scores.sort(key=lambda r:(-r[0],-r[1],r[2]));roster['seasons']=[r[3] for r in scores];assert sorted(json.dumps(e,sort_keys=True) for e in original_entries)==sorted(json.dumps(e,sort_keys=True) for e in roster['seasons']);write(out/'static_roster.json',roster)
 big=out/'data_0.big';shutil.copyfile(sources[1],big);encoded=util.encrypted_sqlite(decoded,(out/'fifadb.sqlite').read_bytes());codec.replace_member(big,member,codec.refpack(encoded),len(encoded));assert b'SQLite format 3\0'+bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(big,member)))[16:]==(out/'fifadb.sqlite').read_bytes()
 a=sources[1].read_bytes();b=big.read_bytes();oldentries=codec.bigdir.entries(sources[1]);entries=codec.bigdir.entries(big);assert len(oldentries)==len(entries)
 for p,q in zip(oldentries,entries):
  assert p[0]==q[0]
  if p[0]!=member:assert a[p[1]:p[1]+p[2]]==b[q[1]:q[1]+q[2]],p[0]
 certificate=common.load(S/'tools/player_import/check.py','restore_three_semantics').validate(S,C,database=out/'fifadb.sqlite',data0=big,registry=out/'custom_rosters.json',full=True);assert certificate['status']=='PLAYER_IMPORT_FULL_PASS';write(out/'player-import-validation.json',certificate)
 for p,h in baseline.items():assert sha(p)==h,('Concurrent source changed',p)
 report=dict(status='BUILT_SEMANTICS_PASS',baseline=baseline,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()},ratings=ratings,changed=67,main_season=48,legacy_seasons_49_55_exact=True,other_rows_exact=True,other_big_members_exact=True,base_rating_range=[min(r['after_base'] for r in ratings),max(r['after_base'] for r in ratings)],prior_adjustment_attributes_exactly_reversed=True,state_shop_written=False,native_ui_verified=False)
 write(out/'build.json',report);write(R/'latest-build.json',dict(path=str(out)));print(json.dumps(dict(status=report['status'],changed=67,base_range=report['base_rating_range'],build=str(out))),flush=True)
 return out
def plan(out,unused=None):
 data=read(out/'build.json')
 for p,h in data['baseline'].items():assert sha(p)==h,('Rebuild required',p)
 for name,h in data['outputs'].items():assert sha(out/name)==h
 play,match,parentrel,parent=tx.top();prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','restore_three_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 helper=(S/parentrel).read_text('utf8').replace(Path(parent.MANIFEST).name,Path(MANIFEST).name).replace(Path(parent.RECEIPT).name,Path(RECEIPT).name).replace(Path(parentrel).stem,Path(SELF).stem).replace(read(S/parent.RECEIPT)['status'],'INSTALLED_MANUTD_MAIN_RESTORED').replace(prior['status'],'MANUTD_MAIN_RESTORED_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 revision='manutd-main-restored-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');doc='docs/工程经验与修改边界.txt'
 note='\n\nFO3-MU-MAIN-RESTORE-THREE（2026-11-07，'+revision+'，实机PENDING）\n用户反馈琼斯实际页面82，明确只把刚下调的三点加回主赛季67张。先核对最新67行目标属性仍等于本聊天-3后版本，再只恢复本次备份中的33项技能/overallrating/potential，非属性字段沿用当前最新。逐卡主位置基础OVR恰好+3，基础区间82～86→85～89，琼斯82→85；不再将额外+5计算值误报为当前页面显示。49/55另外12张历史卡、全部其它球员/名字/模型/表逐行相同；不修改重复卡的市场显示策略。\n注册表当前基础值同步；赛季条目仅按新平均强度重排。data0仅UI SQLite成员变化，其它原压缩成员保持；完整player_import语义检查后同步证书。正式服务停服新快照、共同双锁、最新父层继承全部guard/回执策略及逐文件备份/CAS安装。真实经理/强化/等级/经验/余额/阵容/库存及state/shop不写；现存市场价格/初价/成交事件和商品卡包配置不改。证据D:/fifaol3/manutd-legends/main-restore-three。资源与接口检查不冒充游戏内或比赛验收。\n'
 payload=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('client','data/data_0.big',out/'data_0.big'),('server','gamedata/custom_rosters.json',out/'custom_rosters.json'),('server','responses/static_roster.json',out/'static_roster.json'),('server','gamedata/player-import-validation.json',out/'player-import-validation.json'),('server',doc,(S/doc).read_bytes()+note.encode('utf8')),('server',SELF,helper.encode('utf8')),('server','play-local.bat',play.replace(match,SELF.replace('/','\\').encode()))];entries=[]
 for root,rel,source in payload:
  target=(S if root=='server' else C)/rel;before=sha(target) if target.exists() else None;after=common.digest(source) if isinstance(source,bytes) else sha(source);key=(root,rel.casefold())
  if key in table:assert table[key]['sha256']==before
  else:assert not target.exists()
  table[key]=dict(root=root,relative=rel,sha256=after);entries.append(dict(root=root,relative=rel,target=target,source=source,before=before,after=after))
 comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='manutd-main67-restore-three',native_status='PENDING'))
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parentrel,parent_preflight_sha256=sha(S/parentrel),build_sha256=sha(out/'build.json'))
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_MANUTD_MAIN_RESTORED',revision=revision,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,body in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=body,before=None,after=common.digest(body)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=revision,prior=prior)
def install(out):
 tx.R=R;tx.SELF=SELF;tx.MANIFEST=MANIFEST;tx.RECEIPT=RECEIPT;tx.plan=plan;tx.fresh_market=lambda _:None;tx.install(out)
if __name__=='__main__':
 if '--install' in sys.argv:install(Path(read(R/'latest-build.json')['path']))
 else:build()
