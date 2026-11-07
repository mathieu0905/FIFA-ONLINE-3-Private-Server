"""One Man United filter, exact +2 primary ratings, true short names and strength order."""
from pathlib import Path
import ast,copy,datetime,json,re,shutil,sqlite3,sys
import install as common
import fix_market_filter as codec
from prepare import S,C,R as BASE,sha,write,STATS
sys.dont_write_bytecode=True
R=BASE/'season-organize';R.mkdir(exist_ok=True)
SELF='patches/season_strength_preflight.py';MANIFEST='patches/season-strength-installed.json';RECEIPT='patches/season-strength-receipt.json'
ROLES='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
NAMES={36:'约克',239:'安迪·科尔'}
def read(p):return json.loads(Path(p).read_text('utf8'))
def weights():
 tree=ast.parse((S/'http_config.py').read_text('utf8'));return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLE_WEIGHTS' for t in n.targets))
def primary(row,w):return sum(row[k]*v for k,v in w[ROLES[row['preferredposition1']]].items())//100
def encrypted_sqlite(decoded,plain):
 e=codec.Cipher(codec.Blowfish(codec.extract_fifadb.KEY),codec.modes.ECB()).encryptor();return codec.extract_fifadb.swap32(e.update(codec.extract_fifadb.swap32(decoded[:16]+plain[16:]))+e.finalize())
def build():
 out=R/('build-'+datetime.datetime.now().strftime('%H%M%S-%f'));out.mkdir()
 sources=[S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'responses/static_roster.json'];baseline={str(p):sha(p) for p in sources};w=weights()
 main_member='data/db2/fifadb.db.db2';chi_member='data/db2/chi.db.db2';decoded={}
 for member,name in ((main_member,'fifadb.sqlite'),(chi_member,'chi.sqlite')):
  decoded[member]=bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(sources[1],member)));plain=b'SQLite format 3\0'+decoded[member][16:];(out/name).write_bytes(plain)
 assert (out/'fifadb.sqlite').read_bytes()==sources[0].read_bytes()
 ratings=[]
 with sqlite3.connect(out/'fifadb.sqlite') as db:
  db.row_factory=sqlite3.Row;db.execute('attach database ? as old',(str(sources[0]),))
  original=[dict(row) for row in db.execute('select * from players where spid/1000000 in (48,49,55)')];assert len(original)==53
  for row in original:
   before=primary(row,w);target=before+2;choices=[]
   for shift in range(1,8):
    stats={k:min(99,max(1,row[k]+shift)) for k in STATS};value=primary({**row,**stats},w);choices.append(((abs(value-target),abs(shift-2),sum(v==99 for v in stats.values())),stats,value,shift))
   _,stats,value,shift=min(choices,key=lambda x:x[0]);assert value==target,(row['spid'],before,value)
   changed={**stats,'overallrating':row['overallrating']+2,'potential':max(row['potential'],row['overallrating']+2)}
   db.execute('update players set '+','.join(k+'=?' for k in changed)+' where spid=?',list(changed.values())+[row['spid']])
   ratings.append(dict(spid=row['spid'],before_level1_plus1=before+5,after_level1_plus1=value+5,stat_shift=shift))
  for pid,name in NAMES.items():
   old=db.execute('select short from nameschi where playerid=?',(pid,)).fetchone()[0];assert old.casefold().startswith('shortname'),(pid,old)
   db.execute('update nameschi set short=? where playerid=?',(name,pid))
  db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  for table, in db.execute("select name from main.sqlite_master where type='table'").fetchall():
   where=' where spid/1000000 not in (48,49,55)' if table=='players' else ' where playerid not in (36,239)' if table=='nameschi' else ''
   assert not db.execute('select * from main.'+table+where+' except select * from old.'+table+where+' limit 1').fetchone(),table
   assert not db.execute('select * from old.'+table+where+' except select * from main.'+table+where+' limit 1').fetchone(),table
   assert db.execute('select count(*) from main.'+table).fetchone()==db.execute('select count(*) from old.'+table).fetchone()
  allowed=set(STATS)|{'overallrating','potential'}
  for old in original:
   row=dict(db.execute('select * from players where spid=?',(old['spid'],)).fetchone());assert all(row[k]==v for k,v in old.items() if k not in allowed)
 with sqlite3.connect(out/'chi.sqlite') as db:
  original_chi={r[0]:r for r in db.execute('select * from names')}
  for pid,name in NAMES.items():assert str(original_chi[pid][2]).casefold().startswith('shortname');db.execute('update names set short=? where playerid=?',(name,pid))
  db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  for row in db.execute('select * from names'):
   if row[0] not in NAMES:assert row==original_chi[row[0]]
   else:assert row[:2]+row[3:]==original_chi[row[0]][:2]+original_chi[row[0]][3:]
 big=out/'data_0.big';shutil.copyfile(sources[1],big)
 for member,name in ((main_member,'fifadb.sqlite'),(chi_member,'chi.sqlite')):
  plain=(out/name).read_bytes();encrypted=encrypted_sqlite(decoded[member],plain);assert b'SQLite format 3\0'+bytes(codec.extract_fifadb.decrypt(encrypted))[16:]==plain
  codec.replace_member(big,member,codec.refpack(encrypted),len(encrypted));assert b'SQLite format 3\0'+bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(big,member)))[16:]==plain
 old_entries=codec.bigdir.entries(sources[1]);entries=codec.bigdir.entries(big);a=sources[1].read_bytes();b=big.read_bytes();assert len(entries)==len(old_entries)==271
 assert all(x[1]+x[2]<=y[1] for x,y in zip(entries,entries[1:]))
 for x,y in zip(old_entries,entries):
  assert x[0]==y[0]
  if x[0] not in (main_member,chi_member):assert a[x[1]:x[1]+x[2]]==b[y[1]:y[1]+y[2]],x[0]
 roster=read(sources[2]);old_roster=copy.deepcopy(roster);merged=copy.deepcopy(next(x for x in roster['seasons'] if x['value']==[48]));merged['value']=[48,49,55]
 roster['seasons']=[x for x in roster['seasons'] if not set(x['value'])&{48,49,55}]+[merged]
 db=sqlite3.connect(out/'fifadb.sqlite');db.row_factory=sqlite3.Row;scores=[]
 for index,entry in enumerate(roster['seasons']):
  values=[primary(dict(row),w)+5 for row in db.execute('select * from players where spid/1000000 in ('+','.join('?' for _ in entry['value'])+')',entry['value'])]
  assert values
  scores.append(dict(entry=entry,mean=sum(values)/len(values),peak=max(values),count=len(values),old_index=index))
 scores.sort(key=lambda row:(-row['mean'],-row['peak'],row['old_index']));roster['seasons']=[s['entry'] for s in scores]
 old_codes=[i for e in old_roster['seasons'] for i in e['value']];new_codes=[i for e in roster['seasons'] for i in e['value']];assert sorted(old_codes)==sorted(new_codes) and len(new_codes)==len(set(new_codes))
 assert len(roster['seasons'])==len(old_roster['seasons'])-2 and sum(bool(set(e['value'])&{48,49,55}) for e in roster['seasons'])==1
 write(out/'static_roster.json',roster)
 for path,digest in baseline.items():assert sha(path)==digest,'Concurrent source changed'
 report=dict(status='BUILT_NOT_INSTALLED',baseline=baseline,weights=w,outputs={name:sha(out/name) for name in ('fifadb.sqlite','chi.sqlite','data_0.big','static_roster.json')},ratings=ratings,name_fixes=NAMES,rankings=[dict(mean=s['mean'],peak=s['peak'],count=s['count'],value=s['entry']['value'],season=s['entry']['season']) for s in scores],before_entries=len(old_roster['seasons']),after_entries=len(roster['seasons']),all_season_codes_retained=True,all_spids_retained=True,non_target_big_members_exact=269,native_ea_database_unchanged=True,unrelated_database_rows_exact=True,state_shop_written=False,native_verified=False)
 write(out/'build.json',report);write(R/'latest-build.json',dict(path=str(out)));print(json.dumps(dict(build=str(out),ratings=len(ratings),names=NAMES,season_entries=[len(old_roster['seasons']),len(roster['seasons'])],top=report['rankings'][:6]),ensure_ascii=True))
def plan():
 out=Path(read(R/'latest-build.json')['path']);data=read(out/'build.json')
 for path,digest in data['baseline'].items():assert sha(path)==digest,'Rebuild required: '+path
 for name,digest in data['outputs'].items():assert sha(out/name)==digest
 assert weights()==data['weights']
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',play);assert len(matches)==1;parent_rel=matches[0].decode().replace('\\','/');assert parent_rel!=SELF
 parent=common.load(S/parent_rel,'season_strength_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','season_strength_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 helper=(S/'patches/manutd_filter_preflight.py').read_text('utf8').replace('manutd-filter-installed.json',MANIFEST.split('/')[-1]).replace('manutd-filter-receipt.json',RECEIPT.split('/')[-1]).replace('manutd_filter_preflight.py',SELF.split('/')[-1]).replace('INSTALLED_MANUTD_FILTER','INSTALLED_SEASON_STRENGTH').replace('MANUTD_FILTER_PREFLIGHT_PASS','SEASON_STRENGTH_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 revision='season-strength-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');docrel='docs/工程经验与修改边界.txt';doc=S/docrel
 note='''\n\nFO3-MU-MERGE-ORDER（2026-11-07，'''+revision+'''，原生验收PENDING）
用户反馈同名“曼联传奇”重复，明确要求合并；随后补充shortname占位名和整体能力+2，最后明确不精简其它赛季，按卡种强度高低排序。
本次仅将static_roster的48/49/55三个筛选项合为一个value=[48,49,55]，共53张原卡；全部其它赛季原条目和value保留，只按本次更新后的1级/+1主位置加权OVR均值降序、同分最高值、再原序排序，58→56仅减少曼联重复2入口。原生TransferPurchaseFilterSmoothPanel回调51逐项push服务器顺序；TransferUtil25/26本就支持数组值OR多个季号，因此不改Module/页面BIG/进程内存。原始编号、SPID、存档、卡包和队套代码不变。
精确53张曼联卡每张主位置实际显示OVR+2；同位置原始数值按原技能分布增量，在99边界截断后选择最小平移保证主位置恰好+2，overallrating同步+2。其它球员所有字段、53张身体/模型/位置/特性/身份保持，强化/等级不改；48季41人主池从88～92到90～94，其余49/55旧卡各按原能力+2，不冒称53张全都90～94。
确认名字根因：主SQLite nameschi和客户端独立chi.db的names都保存Shortname_36/Shortname_239，故本次同时将两份真实short字段修为约克/安迪·科尔；两位身份的其它赛季共享显示名也同步纠正，不涉及经理/球队或其它球员名字。所有名字full、英文名与jersey字段保留。
data0仅两项SQLite成员（fifadb.db.db2、chi.db.db2）增量加密/压缩替换并完整解码验证，269其它成员原压缩字节保持，尤其EA原生fifa_ng_db.db和贝林最新修复完全保持，目录顺序/271项数量不变。主DB除53张属性与2条短名、chi库除2条short外均逐行保持。已有商品内容/概率/静态报价、市场供给代码、强化规则、真实state/shop均不改。
只能在用户正常退出游戏后按共同双锁/最新父层和fresh快照安装；不自动关游戏或操作GUI，play最后切换，账本本段也纳入新guard，不安装后裸追加。构建、SQL/原生数组回放、排序和资源证据在D:/fifaol3/manutd-legends/season-organize/{latest-build.json,native-order-proof.json,tests.json,installed.json,verification.json}；真实市场UI重进筛选/新短名与能力显示待用户验证，静态/协议检查不冒充native。
首轮准备曾遇另一聊天player_import合法更新DB/data0，基线检查在正式写前严格拒绝；随后完整事务锁内从最新player_import父层重建，全部新增球员/模型/名字和EA原生记录原字节保留，未用旧构建覆盖新结果。
'''
 payload=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('client','data/data_0.big',out/'data_0.big'),('server','responses/static_roster.json',out/'static_roster.json'),('server',docrel,doc.read_bytes()+note.encode('utf8')),('server',SELF,helper.encode()),('server','play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))];entries=[]
 for root,rel,source in payload:
  target=(S if root=='server' else C)/rel;before=sha(target) if target.exists() else None;key=(root,rel.casefold());after=common.digest(source) if isinstance(source,bytes) else sha(source)
  if key in table:assert table[key]['sha256']==before
  else:assert not target.exists()
  table[key]=dict(root=root,relative=rel,sha256=after);entries.append(dict(root=root,relative=rel,target=target,source=source,before=before,after=after))
 comp['guards']=list(table.values());comp['files_verified']=False;comp.setdefault('ancestry',[]).append(dict(layer='one-ManU-filter-primary2-strength-order',native_status='PENDING'));comp['receipt_policies'].append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'}))
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),build_sha256=sha(out/'build.json'))
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_SEASON_STRENGTH',revision=revision,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,body in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=body,before=None,after=common.digest(body)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=revision,prior=prior)
def apply():
 # Reuse the already-tested mixed server/client install and own-version rollback.
 codec.R=R;codec.SELF=SELF;codec.MANIFEST=MANIFEST;codec.RECEIPT=RECEIPT;codec.plan=plan;codec.apply()
if __name__=='__main__':
 if '--apply' in sys.argv:apply()
 else:build()
