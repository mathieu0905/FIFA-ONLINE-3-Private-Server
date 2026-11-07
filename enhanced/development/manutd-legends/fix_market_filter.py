"""Align native market permissions and Man United season labels, preserving all cards."""
from pathlib import Path
import copy,datetime,hashlib,json,re,shutil,sqlite3,sys
import install as common
from prepare import S,C,R as BASE,sha,write
sys.dont_write_bytecode=True
R=BASE/'market-filter-fix';R.mkdir(exist_ok=True)
SELF='patches/manutd_filter_preflight.py';MANIFEST='patches/manutd-filter-installed.json';RECEIPT='patches/manutd-filter-receipt.json'
sys.path[:0]=[str(S/'tools/re'),str(S/'player_editor'),str(S)]
import bigdir,extract_fifadb
from ordered_big import replace_member
from refpack import refpack
from cryptography.hazmat.primitives.ciphers import Cipher,modes
try:from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish
def read(p):return json.loads(Path(p).read_text('utf8'))
def build():
 out=R/('build-'+datetime.datetime.now().strftime('%H%M%S-%f'));out.mkdir()
 sources={'database':S/'gamedata/fifadb.sqlite','data0':C/'data/data_0.big','language':S/'patches/language_chi.big','language_check':S/'patches/验证结果.json','roster':S/'responses/static_roster.json'}
 baseline={str(p):sha(p) for p in sources.values()};member='data/db2/fifadb.db.db2'
 decoded=bytes(extract_fifadb.decrypt(bigdir.read(sources['data0'],member)));assert b'SQLite format 3\0'+decoded[16:]==sources['database'].read_bytes()
 target=out/'fifadb.sqlite';shutil.copyfile(sources['database'],target);permissions=('permid','permcn','permkr','permth','permvn','permsg');changes={};before_counts={};after_counts={}
 with sqlite3.connect(target) as db:
  db.execute('attach database ? as old',(str(sources['database']),))
  for table in permissions:
   rows=db.execute('select spid,licensed,transferable from '+table+' where spid/1000000 in (48,49,55) and (licensed<>1 or transferable<>1)').fetchall();changes[table]=rows
   for spid,_,_ in rows:db.execute('update '+table+' set licensed=1,transferable=1 where spid=?',(spid,))
  db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  for sid in (48,49,55):
   before_counts[sid]=db.execute('select count(*) from old.players p join old.nameschi n using(playerid) join old.permid m using(spid) where p.spid/1000000=? and m.transferable=1 and m.licensed=1',(sid,)).fetchone()[0]
   after_counts[sid]=db.execute('select count(*) from players p join nameschi n using(playerid) join permid m using(spid) where p.spid/1000000=? and m.transferable=1 and m.licensed=1',(sid,)).fetchone()[0]
  assert after_counts=={48:41,49:5,55:7}
  for table, in db.execute("select name from main.sqlite_master where type='table'").fetchall():
   where=' where spid/1000000 not in (48,49,55)' if table in permissions else ''
   assert not db.execute('select * from main.'+table+where+' except select * from old.'+table+where+' limit 1').fetchone(),table
   assert not db.execute('select * from old.'+table+where+' except select * from main.'+table+where+' limit 1').fetchone(),table
   assert db.execute('select count(*) from main.'+table).fetchone()==db.execute('select count(*) from old.'+table).fetchone(),table
  fa=read(S/'gamedata/fa_prices.json');old_market={row[0] for row in db.execute('select p.spid from old.players p join old.permid m using(spid) join old.namesind n using(playerid) where p.spid>=1000000 and m.transferable=1')}|set(map(int,fa))
  new_market={row[0] for row in db.execute('select p.spid from players p join permid m using(spid) join namesind n using(playerid) where p.spid>=1000000 and m.transferable=1')}|set(map(int,fa))
  assert old_market==new_market,'Global server market set changed'
 raw=target.read_bytes();encryptor=Cipher(Blowfish(extract_fifadb.KEY),modes.ECB()).encryptor();encoded=extract_fifadb.swap32(encryptor.update(extract_fifadb.swap32(decoded[:16]+raw[16:]))+encryptor.finalize());assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(encoded))[16:]==raw
 packed=refpack(encoded);big=out/'data_0.big';shutil.copyfile(sources['data0'],big);replace_member(big,member,packed,len(encoded));assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(bigdir.read(big,member)))[16:]==raw
 a=sources['data0'].read_bytes();b=big.read_bytes();oldentries=bigdir.entries(sources['data0']);newentries=bigdir.entries(big);assert len(oldentries)==len(newentries)==271
 assert all(x[1]+x[2]<=y[1] for x,y in zip(newentries,newentries[1:]))
 for x,y in zip(oldentries,newentries):
  assert x[0]==y[0]
  if x[0]!=member:assert a[x[1]:x[1]+x[2]]==b[y[1]:y[1]+y[2]],x[0]
 assert bigdir.read(big,'data/db/fifa_ng_db.db')==bigdir.read(sources['data0'],'data/db/fifa_ng_db.db'),'Newest native Bellingham fix lost'
 language_member='data/ui/external/LANGUAGESTRING_CHI.json';language=read_language=json.loads(bigdir.read(sources['language'],language_member));language=copy.deepcopy(language);labels={48:'曼联传奇',49:'曼联传奇',55:'曼联传奇'};delta={}
 for sid,label in labels.items():
  for prefix in ('TRANSFERMARKET_SEASON_','LEAGUE_MISSION_SEASON_PREFIX_','CHATTING_SEASON_HEADER_'):
   key=prefix+str(sid);delta[key]=dict(before=language.get(key),after=label);language[key]=label
 for code,label in [('MUL','曼联传奇'),('TCO92','曼联传奇')]:
  key='TRANSFERMARKET_SEASON_'+code;delta[key]=dict(before=language.get(key),after=label);language[key]=label
 for key,value in read_language.items():
  if key not in delta:assert language[key]==value
 lang=out/'language_chi.big';shutil.copyfile(sources['language'],lang);payload=json.dumps(language,ensure_ascii=False,separators=(',',':')).encode();replace_member(lang,language_member,payload,0);assert json.loads(bigdir.read(lang,language_member))==language
 roster=read(sources['roster']);old_roster=copy.deepcopy(roster)
 for entry in roster['seasons']:
  if entry['value'] in ([48],[49],[55]):entry['season']='$TRANSFERMARKET_SEASON_'+str(entry['value'][0])
 assert [x['value'] for x in roster['seasons']]==[x['value'] for x in old_roster['seasons']]
 write(out/'static_roster.json',roster)
 check=read(sources['language_check']);check.update(result_keys=len(language),package_bytes=lang.stat().st_size,sha256=sha(lang),manutd_market_labels='48 / 49 / 55 uniformly Manchester United Legends; native pending');write(out/'language-check.json',check)
 for path,digest in baseline.items():assert sha(path)==digest,'Concurrent build input changed'
 report=dict(status='BUILT_NOT_INSTALLED',baseline=baseline,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()},permission_changes=changes,before_counts=before_counts,after_counts=after_counts,other_database_rows_exact=True,server_market_set_exact=True,non_target_big_members_exact=270,native_roster_exact=True,language_delta=delta,season_groups_preserved=True,native_verified=False,state_shop_written=False)
 write(out/'build.json',report);write(R/'latest-build.json',dict(path=str(out)));print(json.dumps(dict(build=str(out),before=before_counts,after=after_counts,changes={t:len(v) for t,v in changes.items()})))
def plan():
 out=Path(read(R/'latest-build.json')['path']);data=read(out/'build.json')
 for path,digest in data['baseline'].items():assert sha(path)==digest,'Rebuild required: '+path
 for name,digest in data['outputs'].items():assert sha(out/name)==digest
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',play);assert len(matches)==1;parent_rel=matches[0].decode().replace('\\','/');assert parent_rel!=SELF
 parent=common.load(S/parent_rel,'mulfilter_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','mulfilter_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 # Derive our scope from the current strict all-file guard; retain native-roster requirements.
 template='patches/native_roster_preflight.py';helper=(S/template).read_text('utf8').replace('native-roster-installed.json',MANIFEST.split('/')[-1]).replace('native-roster-receipt.json',RECEIPT.split('/')[-1]).replace('native_roster_preflight.py',SELF.split('/')[-1]).replace('INSTALLED_NATIVE_ROSTER','INSTALLED_MANUTD_FILTER').replace('NATIVE_ROSTER_PREFLIGHT_PASS','MANUTD_FILTER_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 payload=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('client','data/data_0.big',out/'data_0.big'),('server','responses/static_roster.json',out/'static_roster.json'),('server','patches/language_chi.big',out/'language_chi.big'),('server','patches/验证结果.json',out/'language-check.json'),('server',SELF,helper.encode()),('server','play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))]
 for prefix in ('_cache/games/fo3id','_cache/cdn'):payload.append(('client',prefix+'/externalAssets/language_chi.big',out/'language_chi.big'))
 entries=[]
 for root,rel,source in payload:
  target=(S if root=='server' else C)/rel;before=sha(target) if target.exists() else None;key=(root,rel.casefold());after=common.digest(source) if isinstance(source,bytes) else sha(source)
  if key in table:assert table[key]['sha256']==before
  else:assert not target.exists(),('Unregistered target',rel)
  table[key]=dict(root=root,relative=rel,sha256=after);entries.append(dict(root=root,relative=rel,target=target,source=source,before=before,after=after))
 comp['guards']=list(table.values());comp['files_verified']=False;comp.setdefault('ancestry',[]).append(dict(layer='manutd-native-market-filter',native_status='PENDING'));comp['receipt_policies'].append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'}))
 revision='manutd-filter-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 docrel='docs/工程经验与修改边界.txt';doc=S/docrel;doc_before=sha(doc)
 note='''\n\nFO3-MU-MARKET-FILTER（2026-11-07，'''+revision+'''，原生验收PENDING）
用户反馈转会市场选“曼联”无筛选结果。实证：语言包TRANSFERMARKET_SEASON_55=曼联、49=曼联传奇；static_roster中MUL=48，TCO92=49，55=原曼联。SQLite中55共7张，permid的transferable/ licensed全0，TransferUtil本地SQL明确要求transferable=1，并可能加licensed=1，故该季查询为空。此前扩充41人属于48季，其中新34张许可正确，原7张仍0；49季5张也未完整可见。REA SQLite证据ev_333a3326d11eaf57f35de0ecacf919d56a4dfc3ef65a2cee10f88efac0b36954确认正式SQLite许可表结构；具体分季计数来自只读SQL，语言来自当前资源解包。
修复范围：只将48/49/55既有卡的六地区许可表licensed与transferable置1，分别可筛选41/5/7；所有players/名字/履历/经验/身体等表和非目标许可行完全保持，无新增或重编号。已知53张全在既有server市场集合，FA补集前后集合严格相同，旧商品卡池/概率/报价保持。人类随后明确“统一一下命名，反正都叫曼联传奇”，故三组选项及相关赛季名全部统一“曼联传奇”；static_roster只改三条显示key，value及赛季分组原样，不混合或迁移已有卡。
客户端data0仅替换data/db2/fifadb.db.db2；双端解密回读一致，目录271条有序，270非目标成员原压缩字节保持。尤其最新data/db/fifa_ng_db.db（原生贝林追加）逐字节保持，绝不使用旧data0全包覆盖。中文只改/补相关11个赛季显示key，其它key值保持；同步server语言源、两缓存及语言校验元数据。无需修改Module/运行中的进程内存，不操作游戏GUI，不强制结束游戏。
按用户约定，仅在正常退出游戏后以共同双锁、实际最新父层及fresh目标hash安装，必要受管服务重载；备份本次正式目标并只回退本事务后版本。保护本次停服新state/shop及用户新增进度。因本账本已被最近原生修复层登记guard，此次将本段本身纳入正式delta/新guard，不安装后再裸追加，也不改历史manifest或receipt。
构建、目录/SQL回归、安装与只读接口结果位于D:/fifaol3/manutd-legends/market-filter-fix/{latest-build.json,tests.json,installed.json,verification.json}；native转会页实际筛选和比赛仍须用户手动重进确认，接口/静态SQL通过不等于实机通过。
'''
 docbody=doc.read_bytes()+note.encode('utf8');doc_key=('server',docrel.casefold())
 assert doc_key in table and table[doc_key]['sha256']==doc_before
 table[doc_key]=dict(root='server',relative=docrel,sha256=common.digest(docbody));entries.append(dict(root='server',relative=docrel,target=doc,source=docbody,before=doc_before,after=common.digest(docbody)));comp['guards']=list(table.values())
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),build_sha256=sha(out/'build.json'))
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_MANUTD_FILTER',revision=revision,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,body in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=body,before=None,after=common.digest(body)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=revision,prior=prior)
def apply():
 with common.locks():
  common.closed();p=plan();was_running=bool(common.listening());stopped=False
  try:
   if was_running:
    import subprocess,time
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=common.env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
    deadline=time.monotonic()+12
    while common.listening():
     if time.monotonic()>deadline:raise RuntimeError('Listeners remain')
     time.sleep(.2)
   common.closed();protected={str(S/'gamedata'/n):sha(S/'gamedata'/n) for n in ('state.json','shop.json','custom_rosters.json','pack_cadence.json','pack_catalogue.json','product_packs.json','reward_upgrade_products.json')}
   snap=R/'fresh-stop-snapshot'/p['revision'];snap.mkdir(parents=True)
   for n in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/n,snap/n)
   def verify():
    common.load(S/SELF,'mulfilter_installed').preflight(S,C)
    for path,digest in protected.items():assert sha(path)==digest,'Protected file changed'
   backup=S/'backups'/p['revision'];common.commit(p['entries'],backup,verify)
   result=dict(status='INSTALLED',revision=p['revision'],backup=str(backup),protected=protected,preflight=common.load(S/SELF,'mulfilter_final').preflight(S,C),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',state_shop_written=False,native_verified=False,hashes={str(p):sha(p) for p in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat',S/'gamedata/fifadb.sqlite',C/'data/data_0.big')});write(R/'installed.json',result)
  finally:
   if was_running and stopped:common.restart()
  result['services_restored']=common.listening()==[443,8088,28002] if was_running else 'previously_stopped';write(R/'installed.json',result)
  descriptor=BASE.parent/'root-current-top.json';d=read(descriptor);d.update(status='INSTALLED_MANUTD_FILTER_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),top_preflight=result['top_preflight'],top_manifest=result['top_manifest'],top_receipt=result['top_receipt'],files=result['hashes'],preflight=result['preflight'],handoff=str(R/'installed.json'),receipt_record=read(S/RECEIPT),services_restored=result['services_restored'],state_shop_written=False,GUI_status='No GUI. SQL/native resource checks PASS; actual market filtering pending');common.atomic(common.body(d),descriptor)
  print(json.dumps(result))
if __name__=='__main__':
 if '--apply' in sys.argv:apply()
 else:build()
