"""Publish the roster and its bound valuation together after natural game exit."""
from pathlib import Path
from contextlib import closing
import copy,datetime,importlib.util,json,re,shutil,sqlite3,subprocess,sys,time
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('nostalgia_mean87_builder',P/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
S,C=b.S,b.C;t=b.resource.common;read=b.read;save=b.save;sha=b.sha;load=b.load
SELF='patches/nostalgia_mean87_preflight.py';MANIFEST='patches/nostalgia-mean87-installed.json';RECEIPT='patches/nostalgia-mean87-receipt.json'
MODEL='gamedata/fair-value-nostalgia87-model.json';CATALOGUE='gamedata/fair-value-nostalgia87-catalogue.json.gz'
def game_running():return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9};exit 0'],env=t.env(),creationflags=subprocess.CREATE_NO_WINDOW).returncode!=0
def defer(reason):
 result=dict(status='DEFERRED',reason=reason,message='更新已延后，当前游戏继续运行' if reason=='GAME_RUNNING' else '更新已准备，等待发布窗口',formal_written=False,services_restarted=False);save(P/'pending-handback.json',result);print(json.dumps(result,ensure_ascii=True));return result
def fresh_report(out):
 report=read(out/'report.json');assert report['status']=='PREPARED_AND_REGRESSION_PASS'
 for path,h in report['baseline'].items():assert sha(path)==h,('Refresh baseline; rerun prepare.py',path)
 for name,h in report['outputs'].items():assert sha(out/name)==h
 return report
def plan(out,market,state_bytes):
 report=fresh_report(out);play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1;rel=matches[0].decode().replace('\\','/');parent=load(S/rel,'nostalgia87_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=load(S/'patches/startup_market_preflight.py','nostalgia87_validator');validator.verify_manifest(comp,S,C);guards=validator.table(comp['guards'])
 helper=(S/rel).read_text('utf8').replace(parent.MANIFEST,MANIFEST).replace(parent.RECEIPT,RECEIPT).replace(parent.SELF,SELF).replace(read(S/parent.RECEIPT)['status'],'INSTALLED_NOSTALGIA_MEAN87').replace(prior['status'],'NOSTALGIA_MEAN87_PREFLIGHT_PASS')
 marker='\n return dict(';index=helper.index(marker,helper.index('def preflight'))
 extra="\n nostalgia_fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'"+CATALOGUE+"',server/'"+MODEL+"',server/'gamedata/fifadb.sqlite')"
 helper=helper[:index]+extra+helper[index:];helper=helper.replace('return dict(','return dict(nostalgia_fair_value=nostalgia_fair_value,',1);index=helper.index('\n if not required<=seen:');helper=helper[:index]+"\n required.update({('server','"+MODEL+"'),('server','"+CATALOGUE+"')})"+helper[index:];compile(helper,SELF,'exec')
 revision='nostalgia-mean87-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');doc='docs/工程经验与修改边界.txt'
 note='\n\nFO3-NOSTALGIA-ENHANCED-MEAN87（2026-11-07，'+revision+'，实机PENDING）\n用户澄清不是恢复历史原卡强度，而是强化卡种平均基础87，并允许顶级92～93。本次19季88张按原主位置基础强弱层次，最小85/最高93约束下求统一平移目标并最大余数分配，使总和7656、平均精确87；不是额外算强化+5。各卡原33技能分布按最小平移、99封顶校准到目标，overall同步，potential不低于目标；身体/身份/星数/特性/动作/位置/模型与其它赛季所有行保持。分布85x48、86x6、87x3、88x5、89x10、90x3、91x4、92x2、93x7。注册表保留旧纠正历史并记录本次卡种增强，筛选不增删，只按新实际强度排序。\n当前公平估值强制绑定属性，不能只改UI库后声称完成。本次复制最新v14模型参数，仅新建v15目录与属性摘要；只88张估值数据改变，保留其它61500余张现价、身份市场因子、原事件与强化价格曲线。停服先按旧属性flush已提交价格事件，再从当前市场库快照生成新一代；真实存档只迁移market_simulation代号/待报价与已flush事件队列，经理/卡/强化/等级/经验/余额/库存/球队/阵容逐字段保持。现行pack_base_prices热包及全部路由/低档定价规则不改，不从旧value_prices推断实收。\n客户端data0仅UI SQLite成员增量替换，其它成员原压缩字节/布局保持；完整player_import与新证书同步，原生身份/六语/模型不增删。安装器游戏运行时先延期，不提示退出、不停服、不写正式文件；仅自然退出后fresh最新父层、共同双锁、新资产快照、备份与CAS。所有guard/回执策略继承，历史模型/目录/回执不改。证据D:/fifaol3/nostalgia-mean87，静态/资源/完整导入/估值回归不能代替首页近远景、带球或比赛验收。\n'
 payload=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('client','data/data_0.big',out/'data_0.big'),('server','gamedata/custom_rosters.json',out/'custom_rosters.json'),('server','responses/static_roster.json',out/'static_roster.json'),('server','gamedata/player-import-validation.json',out/'player-import-validation.json'),('server',MODEL,out/'model.json'),('server',CATALOGUE,out/'catalogue.json.gz'),('server','gamedata/npc-market-prices.sqlite',market),('server','gamedata/state.json',state_bytes),('server',doc,(S/doc).read_bytes()+note.encode('utf8')),('server',SELF,helper.encode('utf8')),('server','play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))];entries=[]
 for root,path,source in payload:
  target=(S if root=='server' else C)/path;before=sha(target) if target.exists() else None;after=t.digest(source) if isinstance(source,bytes) else sha(source);key=(root,path.casefold());mutable=path in ('gamedata/npc-market-prices.sqlite','gamedata/state.json')
  if mutable:assert key not in guards
  elif key in guards:assert guards[key]['sha256']==before
  else:assert not target.exists()
  if not mutable:guards[key]=dict(root=root,relative=path,sha256=after)
  entries.append(dict(root=root,relative=path,target=target,source=source,before=before,after=after))
 comp.update(guards=list(guards.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='nostalgia-kind-mean87-elite93',native_status='PENDING'));comp['active_fair_valuation']=dict(revision=b.TAG,model_sha256=report['model_sha256'],profile_sha256=report['profile_sha256'])
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(r['relative']==policy['relative'] for r in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=rel,parent_preflight_sha256=sha(S/rel),build_sha256=sha(out/'report.json'),state_market_migration_only=True);mb=t.body(manifest);rb=t.body(dict(status='INSTALLED_NOSTALGIA_MEAN87',revision=revision,manifest_sha256=t.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for path,data in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/path).exists();entries.append(dict(root='server',relative=path,target=S/path,source=data,before=None,after=t.digest(data)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(revision=revision,entries=entries)
def main():
 if game_running():return defer('GAME_RUNNING')
 if (S/'.shop-release.lock').exists() or (S/'.fo3-publish.lock').exists():return defer('RELEASE_BUSY')
 out=Path(read(P/'latest-build.json')['path']);report=fresh_report(out)
 with t.locks():
  if game_running():return defer('GAME_RUNNING')
  coord=read(W/'coordination-current.json') if (W:=b.W) else {};assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer')
  rel=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',(S/'play-local.bat').read_bytes())[0].decode().replace('\\','/');load(S/rel,'before_stop').preflight(S,C)
  if game_running():return defer('GAME_RUNNING')
  running=bool(t.listening());stopped=False
  try:
   if running:
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=t.env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
    deadline=time.monotonic()+15
    while t.listening():
     if time.monotonic()>deadline:raise RuntimeError('Listeners remain')
     time.sleep(.2)
   t.closed();fresh_report(out);raw=(S/'gamedata/state.json').read_bytes();state=json.loads(raw);store=load(S/'market_price_store.py','nostalgia87_flush');old=store.MarketPriceStore(S/'gamedata/npc-market-prices.sqlite')
   try:old.flush(state.get('market_simulation',{}).get('price_events',[]))
   finally:old.close()
   market=P/('fresh-market-'+datetime.datetime.now().strftime('%H%M%S-%f')+'.sqlite')
   with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(market)) as dst:src.backup(dst)
   fair=load(S/'fair_value_store.py','nostalgia87_migration');fair.install_catalogue(market,out/'catalogue.json.gz',out/'model.json',out/'fifadb.sqlite')
   with closing(sqlite3.connect(market)) as db:db.execute('update metadata set value=? where key=?',(str(S/'gamedata/fifadb.sqlite'),'fair_source_database'));db.commit()
   after=fair.migrate_state(state,b.TAG);after['market_simulation']['price_events']=[];assert {k:v for k,v in state.items() if k!='market_simulation'}=={k:v for k,v in after.items() if k!='market_simulation'}
   assert (S/'gamedata/state.json').read_bytes()==raw;p=plan(out,market,t.body(after));snap=P/'fresh-stop-snapshot'/p['revision'];snap.mkdir(parents=True);(snap/'state.json').write_bytes(raw);shutil.copyfile(S/'gamedata/shop.json',snap/'shop.json')
   protected={str(path):sha(path) for path in (S/'gamedata').glob('*.json') if path.name not in ('state.json','custom_rosters.json','player-import-validation.json')};protected[str(S/'hot_updates/active.json')]=sha(S/'hot_updates/active.json');hot=read(S/'hot_updates/active.json')
   def verify():
    load(S/SELF,'nostalgia87_installed').preflight(S,C)
    certificate=load(S/'tools/player_import/check.py','nostalgia87_formal_import').validate(S,C,full=True);assert certificate==read(S/'gamedata/player-import-validation.json')
    current=read(S/'gamedata/state.json');assert {k:v for k,v in current.items() if k!='market_simulation'}=={k:v for k,v in state.items() if k!='market_simulation'}
    for path,h in protected.items():assert sha(path)==h
   backup=S/'backups'/p['revision'];t.closed();t.commit(p['entries'],backup,verify)
   result=dict(status='INSTALLED_NATIVE_PENDING',revision=p['revision'],backup=str(backup),build=str(out),protected=protected,expected_hot_revision=hot['revision'],top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',hashes={str(path):sha(path) for path in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat')},real_assets_preserved=True,state_market_migration_written=True,shop_written=False,native_ui_verified=False);save(P/'installed-handback.json',result)
  finally:
   if running and stopped and not game_running():t.restart()
  result['services_restored']=t.listening()==[443,8088,28002];save(P/'installed-handback.json',result);d=read(W/'root-current-top.json');d.update(status='INSTALLED_NOSTALGIA_MEAN87_NATIVE_PENDING',top_preflight=result['top_preflight'],top_manifest=result['top_manifest'],top_receipt=result['top_receipt'],files=result['hashes'],handoff=str(P/'installed-handback.json'),services_restored=result['services_restored'],composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),native_verified=False,match_verified=False);t.atomic(t.body(d),W/'root-current-top.json');print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
