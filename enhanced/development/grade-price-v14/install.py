"""Official fair-value publication. No client operation or active-game restart."""
from pathlib import Path
from contextlib import closing,contextmanager
import copy,datetime,gzip,hashlib,importlib.util,json,os,re,sqlite3,subprocess,sys,time,urllib.request
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3')
SELF='patches/grade_price_v14_preflight.py';MANIFEST='patches/grade-price-v14-installed.json';RECEIPT='patches/grade-price-v14-receipt.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def data(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def read(p):return json.loads(Path(p).read_text('utf8'))
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(args):
 r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
def game_running():
 r=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode not in (0,9):raise RuntimeError('Cannot determine game state')
 return r.returncode==9
def closed():
 if game_running():raise RuntimeError('更新已延后，当前游戏继续运行')
def atomic(p,body):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.grade-v14.tmp');tmp.write_bytes(body);os.replace(tmp,p)
def api(path):
 with urllib.request.urlopen('http://127.0.0.1:8088/api/'+path,timeout=5) as r:return json.load(r)
def assets(st):return {k:v for k,v in st.items() if k!='market_simulation'}
def start():
 env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 with (P/'service.stdout.log').open('ab') as out,(P/'service.stderr.log').open('ab') as err:return subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW).pid
@contextmanager
def locks():
 own=[]
 try:
  for n in ['.shop-release.lock','.fo3-publish.lock']:
   p=S/n;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);b=data(dict(owner='grade-price-v14',pid=os.getpid(),scope='fair curve/catalogue, price store and market exact adapters, child metadata/docs/play',handoff=str(P/'installed-handback.json')));own.append((p,fd,b));os.write(fd,b);os.fsync(fd)
  yield
 finally:
  for p,fd,b in reversed(own):
   os.close(fd)
   if p.exists() and p.read_bytes()==b:p.unlink()
def sqlite_rows(path,sql):
 with closing(sqlite3.connect(path)) as db:return db.execute(sql).fetchall()

def protected_market(state):
 m=copy.deepcopy(state['market_simulation'])
 for key in ['fair_revision','fair_revision_history','identity_quotes','price_events','system_quote_price_revision','system_quote_repricing_receipts']:m.pop(key,None)
 def clean(row):
  row.pop('price',None);row.pop('_market_price_revision',None)
 for book in list(m.get('books',{}).values())+list(m.get('rare_books',{}).values()):
  for row in book.get('rows',[]):clean(row)
 for row in m.get('legacy_supply',[]):clean(row)
 for a in m.get('npc_exchange',{}).get('assets',{}).values():
  if isinstance(a.get('listing'),dict):clean(a['listing'])
 return m

def plan():
 report=read(P/'prepared.json');audit=read(P/'regression.json');assert audit['status']=='PASS' and read(P/'generation-regression.json')['status']=='PASS'
 for file,h in report['baseline'].items():assert sha(file)==h,'Fresh baseline changed '+file
 for file,h in report['outputs'].items():assert sha(P/file)==h,'Prepared artifact changed '+file
 assert sha(P/'system_quotes.py')==read(P/'generation-regression.json')['quote_source_sha256']
 play=(S/'play-local.bat').read_bytes();match=re.search(rb'patches\\(\w+_preflight\.py)',play);parent_rel='patches/'+match[1].decode();assert parent_rel!=SELF
 parent=load(S/parent_rel,'v14_fresh_parent');prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C);validator=load(S/'patches/startup_market_preflight.py','v14_guard_validator');validator.verify_manifest(composition,S,C);guards=validator.table(composition['guards']);oldkeys=set(guards)
 source=(S/parent_rel).read_text('utf8')
 for a,b in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_GRADE_PRICE_V14'),(prior['status'],'GRADE_PRICE_V14_PREFLIGHT_PASS')]:source=source.replace(a,b)
 assert source.count('\n fair_value=verify_installed(')==1;source=source.replace('\n fair_value=verify_installed(','\n previous_fair_value=verify_installed(',1)
 i=source.index('\n return dict(',source.index('def preflight'))
 source=source[:i]+"\n fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-v14-catalogue.json.gz',server/'gamedata/fair-value-v14-model.json',server/'gamedata/fifadb.sqlite')"+source[i:]
 source=source.replace('return dict(','return dict(previous_fair_value=previous_fair_value,',1)
 extra={('server','gamedata/fair-value-v14-model.json'),('server','gamedata/fair-value-v14-catalogue.json.gz')};i=source.index('\n if not required<=seen:');source=source[:i]+'\n required.update('+repr(extra)+')'+source[i:]
 revision='grade-price-v14-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 docs='\n\n2026-11-07 强化单卡价格 v14：v13全部+1基价和球员属性不变；强化价由+1乘独立倍率。采用现有成功率/失败规则/材料选择归一化成本，+1至+5保留原倍率，+5以上对数压缩，+20倍率5000，避免原生数值上限；这不是原始制造期望成本。强化成功率、能力增幅、用户资产、玩家订单、已成交记录不变。新代际保留历史和共同市场因子，系统旧报价按新参考价撤换重挂，数量/期限/NPC钱包和成本不变。纯临时数据校验、正式接口校验不等于实机比赛通过；游玩期间禁止停服。\n'
 payloads={('server','fair_value_store.py'):(P/'fair_value_store.py').read_bytes(),('server','npc_exchange.py'):(P/'npc_exchange.py').read_bytes(),('server','gamedata/fair-value-v14-model.json'):(P/'model.json').read_bytes(),('server','gamedata/fair-value-v14-catalogue.json.gz'):(P/'catalogue.json.gz').read_bytes(),('server','docs/工程经验与修改边界.txt'):(S/'docs/工程经验与修改边界.txt').read_bytes()+docs.encode('utf8'),('server',SELF):source.encode('utf8'),('server','play-local.bat'):play.replace(match[0],SELF.replace('/','\\').encode())}
 before={}
 for (root,rel),body in payloads.items():
  target=S/rel;key=(root,rel.casefold());before[(root,rel)]=target.read_bytes() if target.exists() else None
  if target.exists():assert key in guards and sha(target)==guards[key]['sha256'],'Target outside fresh guard '+rel
  else:assert key not in guards
  if rel.endswith('.py'):compile(body.decode('utf8'),rel,'exec')
  guards[key]=dict(root=root,relative=rel,sha256=hashlib.sha256(body).hexdigest())
 assert oldkeys<=set(guards)
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(x['root']==policy['root'] and x['relative'].casefold()==policy['relative'].casefold() for x in composition.setdefault('receipt_policies',[])):composition['receipt_policies'].append(policy)
 composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='independent-enhancement-prices-v14',revision=revision,native_status='PENDING'));composition['active_fair_valuation']=dict(model_sha256=report['model_sha256'],profile_sha256=report['profile_sha256'],base_generation='nostalgia-utility-ep-v13',independent_enhancement=True,grade20_multiplier=5000)
 manifest=dict(schema=1,revision=revision,client=str(C),guards=composition['guards'],composition=composition,state_shop_replaced=False,parent=parent_rel,parent_sha256=sha(S/parent_rel),attributes_changed=False)
 for rel,body in [(MANIFEST,data(manifest)),(RECEIPT,data(dict(status='INSTALLED_GRADE_PRICE_V14',revision=revision,manifest_sha256=hashlib.sha256(data(manifest)).hexdigest(),state_shop_replaced=False,native_status='PENDING')))]:assert not (S/rel).exists();payloads[('server',rel)]=body;before[('server',rel)]=None
 audit.update(rows=report['rows'],model_sha256=report['model_sha256'])
 return dict(payloads=payloads,before=before,revision=revision,parent=parent_rel,parent_hash=sha(S/parent_rel),audit=audit,build=report)

def offline_commit(p):
 closed();backup=S/'backups'/p['revision'];backup.mkdir();closed();run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')])
 committed=[];stopped=True;activated=False;migrated=False;state_written=False;roots=dict(server=S,client=C)
 try:
  closed();time.sleep(1);assert sha(S/p['parent'])==p['parent_hash'];statepath=S/'gamedata/state.json';state_raw=statepath.read_bytes();state=json.loads(state_raw);shopsha=sha(S/'gamedata/shop.json');(backup/'state-fresh.json').write_bytes(state_raw);(backup/'shop-fresh.json').write_bytes((S/'gamedata/shop.json').read_bytes());dbpath=S/'gamedata/npc-market-prices.sqlite'
  # Flush the old generation before replacing player attributes, or its profile
  # guard would correctly refuse to replay old committed price movements.
  oldstore=load(S/'market_price_store.py','v14_old_store');live=oldstore.MarketPriceStore(dbpath);live.flush(state.get('market_simulation',{}).get('price_events',[]));live.close()
  with closing(sqlite3.connect(dbpath)) as a,closing(sqlite3.connect(backup/'market-before-v14.sqlite')) as b:a.backup(b)
  with closing(sqlite3.connect(dbpath)) as db:seeds=db.execute('select * from seeds order by spid').fetchall();factors=db.execute('select * from player_market_factors order by playerid').fetchall();old_count=db.execute('select count(*) from price_events').fetchone()[0]
  for i,(key,body) in enumerate(p['before'].items()):
   if body is not None:(backup/(str(i)+'-'+Path(key[1]).name)).write_bytes(body)
  (backup/'transaction.json').write_bytes(data(dict(files=[dict(root=k[0],relative=k[1],before=None if v is None else hashlib.sha256(v).hexdigest(),after=hashlib.sha256(p['payloads'][k]).hexdigest()) for k,v in p['before'].items()])))
  for key,body in p['payloads'].items():
   if key[1]=='play-local.bat':continue
   closed();target=roots[key[0]]/key[1];assert (target.read_bytes() if target.exists() else None)==p['before'][key],'CAS failed '+key[1];atomic(target,body);committed.append(key)

  maintenance=load(P/'fair_value_store.py','v14_explicit_maintenance_helpers')
  closed();proof=maintenance.install_catalogue(dbpath,S/'gamedata/fair-value-v14-catalogue.json.gz',S/'gamedata/fair-value-v14-model.json',S/'gamedata/fifadb.sqlite');migrated=True
  before_prices={r[0]:r[1] for r in sqlite_rows(backup/'market-before-v14.sqlite','select spid,current_price from prices')}
  assert dict(sqlite_rows(dbpath,'select spid,current_price from prices'))==before_prices,'+1 changed'
  after=maintenance.migrate_state(state,'base-times-enhancement-v14');after['market_simulation']['price_events']=[]
  values={r[0]:tuple(r[1:]) for r in sqlite_rows(dbpath,'select * from fair_values')};factor_map=dict(sqlite_rows(dbpath,'select playerid,factor from player_market_factors'))
  quote=load(P/'system_quotes.py','v14_quote_transaction');boost=load(W/'value-redesign-v12/effective_boosts.py','v14_boost').grade_boosts();model=load(S/'fair_value_model.py','v14_curve')
  after,quote_receipt,quote_changes=quote.reissue(after,read(S/'gamedata/fair-value-v13-model.json'),read(S/'gamedata/fair-value-v14-model.json'),values,factor_map,boost,time.time(),model.economic_curve)
  assert assets(after)==assets(state);assert protected_market(after)==protected_market(state)
  (backup/'system-requoted-offers.json').write_bytes(data(dict(receipt=quote_receipt,changes=quote_changes)))
  closed();assert statepath.read_bytes()==state_raw;state_after=data(after);atomic(statepath,state_after);state_written=True
  closed();key=('server','play-local.bat');assert (S/key[1]).read_bytes()==p['before'][key];atomic(S/key[1],p['payloads'][key]);committed.append(key)
  checked=json.loads(run([str(S/'.venv/Scripts/python.exe'),'-X','utf8','-B',str(S/SELF)]));run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py')])
  with closing(sqlite3.connect(dbpath)) as db:
   assert db.execute('select * from seeds order by spid').fetchall()==seeds;assert db.execute('select * from player_market_factors order by playerid').fetchall()==factors;assert db.execute('select count(*) from price_events').fetchone()[0]==old_count+p['audit']['rows']
  assert sha(S/'gamedata/shop.json')==shopsha;closed();launcher=start();activated=True;stopped=False
  return dict(status='FILES_COMMITTED_SERVICE_STARTING',revision=p['revision'],backup=str(backup),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',preflight=checked,profile_binding=proof,launcher_pid=launcher,expected_shop_sha256=shopsha,asset_before=assets(state),seeds_and_earned_market_factors_preserved=True,old_event_count=old_count,plus1_prices_unchanged=True,system_quote_receipt=quote_receipt,official_import_check='PASS',enhancement_rates_unchanged=True,hashes={rel:sha(S/rel) for rel in [SELF,MANIFEST,RECEIPT,'play-local.bat']},native_verified=False,match_verified=False)
 except BaseException:
  if stopped and not activated:
   closed()
   if state_written:
    assert statepath.read_bytes()==state_after;now=read(statepath);now['market_simulation']=state.get('market_simulation',{});assert assets(now)==assets(state);atomic(statepath,data(now))
   if migrated:
    with closing(sqlite3.connect(dbpath,uri=True)) as db,db:
     db.execute('attach database ? as beforev14',((backup/'market-before-v14.sqlite').as_uri()+'?mode=ro',))
     for sid,event in db.execute('select spid,last_event from prices').fetchall():
      if event!='fair-calibration:base-times-enhancement-v14:'+str(sid):raise RuntimeError('Later price progress retained; rollback refused')
     db.execute('delete from fair_values');db.execute('insert into fair_values select * from beforev14.fair_values');db.execute('delete from player_market_factors');db.execute('insert into player_market_factors select * from beforev14.player_market_factors')
     for row in db.execute('select * from beforev14.prices').fetchall():db.execute('update prices set basis_price=?,current_price=?,updated_at=?,last_event=? where spid=?',(*row[1:],row[0]))
     db.execute("delete from price_events where event_id like 'fair-calibration:base-times-enhancement-v14:%'");db.execute("delete from metadata where key like 'fair_%'");db.execute("insert into metadata select * from beforev14.metadata where key like 'fair_%'")
     for table in ['fair_generation_history','fair_value_history']:
      if not db.execute('select name from beforev14.sqlite_master where name=?',(table,)).fetchone():db.execute('drop table '+table)
      else:db.execute('delete from '+table+" where revision='nostalgia-utility-ep-v13'")
   for key in reversed(committed):
    target=roots[key[0]]/key[1]
    if target.read_bytes()!=p['payloads'][key]:raise RuntimeError('Later legitimate file retained; rollback refused '+key[1])
    if p['before'][key] is None:target.unlink()
    else:atomic(target,p['before'][key])
   start()
  raise

def install():
 if game_running():
  result=dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_written=False);(P/'pending-handback.json').write_bytes(data(result));print(json.dumps(result,ensure_ascii=False));return False
 with locks():
  closed();p=plan();hot=api('hot_update_status');print('FRESH_PARENT_PASS',p['parent'],flush=True);report=offline_commit(p)
 # Release both locks before waiting for the hot watcher.
 (P/'commit-handback.json').write_bytes(data({k:v for k,v in report.items() if k!='asset_before'}));deadline=time.monotonic()+75
 while time.monotonic()<deadline:
  try:
   probe=api('market_price_store?spid=84037576&grade=20');status=api('market_status');active=api('hot_update_status')
   if probe.get('active_valuation_revision')=='base-times-enhancement-v14' and probe['active_valuation_model_sha256']==p['audit']['model_sha256'] and status['background']['running'] and status['background']['errors']==0 and active['revision']==hot['revision'] and active['watcher_running'] and active['error'] is None and set(active['routes'])==set(hot['routes']):break
  except Exception as exc:last_error=str(exc)
  time.sleep(.5)
 else:raise RuntimeError('Restore not verified; preserve all live progress: '+str(locals().get('last_error')))
 report.update(status='INSTALLED_AND_LIVE_PASS',asset_projection_equal=assets(read(S/'gamedata/state.json'))==report.pop('asset_before'),shop_equal=sha(S/'gamedata/shop.json')==report.pop('expected_shop_sha256'),live_price_probe=probe,background=status['background'],hot_update_status=active,locks_released=True,state_shop_replaced=False,native_match_validation=False,independent_grade_curve=True)
 (P/'installed-handback.json').write_bytes(data(report))
 # Another legitimate writer may already have inherited this layer.
 if SELF.replace('/','\\').encode() in (S/'play-local.bat').read_bytes():(W/'root-current-top.json').write_bytes(data(dict(report,handoff=str(P/'installed-handback.json'))))
 print(json.dumps(report,ensure_ascii=False),flush=True);return True
if __name__=='__main__':install()
