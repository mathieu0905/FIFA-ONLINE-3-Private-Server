"""Combined official valuation and proven MUL fixes, single writer, idle only."""
from pathlib import Path
from contextlib import contextmanager,closing
import copy,datetime,gzip,hashlib,importlib.util,json,os,re,shutil,sqlite3,subprocess,sys,time,urllib.request
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3');V=W/'npc-peer-market/identity-anchor-v11'
SELF='patches/value_identity_mul_preflight.py';MANIFEST='patches/value-identity-mul-installed.json';RECEIPT='patches/value-identity-mul-receipt.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
def data(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(args):
 r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
def closed():
 run(['powershell.exe','-NoProfile','-Command',"if(Get-Process fifazf -ErrorAction SilentlyContinue){Write-Output '更新已延后，当前游戏继续运行';exit 9}"])
def atomic(p,body):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.value-v11.tmp');tmp.write_bytes(body);os.replace(tmp,p)
def assets(state):return {k:v for k,v in state.items() if k!='market_simulation'}
def api(name):
 with urllib.request.urlopen('http://127.0.0.1:8088/api/'+name,timeout=4) as r:return json.load(r)
def start():
 env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 with (P/'service.stdout.log').open('ab') as out,(P/'service.stderr.log').open('ab') as err:
  return subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW).pid
@contextmanager
def locks():
 owned=[]
 try:
  for name in ['.shop-release.lock','.fo3-publish.lock']:
   p=S/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);body=data(dict(pid=os.getpid(),owner='identity-v11-mul63-combined',scope='valuation prices, MUL63 UI/BIG/registry/certificate and append-only child',handoff=str(P/'installed-handback.json')));owned.append((p,fd,body));os.write(fd,body);os.fsync(fd)
  yield
 finally:
  for p,fd,body in reversed(owned):
   os.close(fd)
   if p.exists() and p.read_bytes()==body:p.unlink()

def plan():
 prepared=read(P/'prepared.json');assert read(P/'migration-regression.json')['status']=='PASS'
 for name,h in prepared['baseline'].items():assert sha(name)==h,'Source changed; refresh '+name
 build=Path(prepared['build']);play=(S/'play-local.bat').read_bytes();match=re.search(rb'patches\\(\w+_preflight\.py)',play);assert match
 parent_rel='patches/'+match[1].decode();assert parent_rel!=SELF
 parent=load(S/parent_rel,'value_parent');prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C)
 validator=load(S/'patches/startup_market_preflight.py','value_guard');validator.verify_manifest(composition,S,C);guards=validator.table(composition['guards'])
 revision='identity-v11-mul63-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 source=(S/parent_rel).read_text('utf8')
 for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_VALUE_IDENTITY_MUL'),(prior['status'],'VALUE_IDENTITY_MUL_PREFLIGHT_PASS')]:source=source.replace(old,new)
 required=[('server','gamedata/valuation-v11.json.gz'),('server','tools/value_v11/selected-model.json.gz'),('server','tools/value_v11/predict.py'),('server','tools/value_v11/features.py')]
 b=source.index('\n if not required<=seen:');source=source[:b]+'\n required.update('+repr(set(required))+')'+source[b:]
 marker=" seed=store.verify_seed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/npc-market-seed.json.gz')"
 assert source.count(marker)==1
 source=source.replace(marker,marker+"\n valuation=store.verify_calibration(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/valuation-v11.json.gz')")
 source=source.replace('seed=seed,runtime_model_loaded=False','seed=seed,valuation=valuation,runtime_model_loaded=False')
 note=(W/'value-diagnosis/manutd-full-audit/工程经验待安装追加.txt').read_text('utf8')
 note=note.replace('正式激活延后','正式联合安装').replace('真实state/shop/市场历史未读写，未操作游戏GUI，未停服或重启。','仅市场行情基准和报价游标按新模型显式校准；经理资产、余额、库存、阵容及原成交/种子记录保留。无GUI操作。')
 note+='\n联合估值 v11：身份先验来自17842条真实历史记录，10880人，跨赛季共享因子2/3至1.5；未知1。GPU及独立验证通过。显式一次性校准后继续成交驱动，不在后台重新推理/重新播种。旧种子、历史回执及成交不改，校准另记追加事件。既有挂单合同价保留至自然到期。未作实机/比赛验收。\n'
 payloads={('server','market_price_store.py'):(P/'market_price_store.py').read_bytes(),('server','gamedata/valuation-v11.json.gz'):(P/'valuation-calibration.json.gz').read_bytes(),
  ('server','gamedata/fifadb.sqlite'):(build/'fifadb.sqlite').read_bytes(),('client','data/data_0.big'):(build/'data_0.big').read_bytes(),
  ('server','gamedata/custom_rosters.json'):(build/'custom_rosters.json').read_bytes(),('server','gamedata/player-import-validation.json'):(build/'player-import-validation.json').read_bytes(),
  ('server','docs/工程经验与修改边界.txt'):(S/'docs/工程经验与修改边界.txt').read_bytes()+('\n'+note).encode('utf8'),
  ('server',SELF):source.encode('utf8'),('server','play-local.bat'):play.replace(match[0],SELF.replace('/','\\').encode())}
 for name in ['selected-model.json.gz','predict.py','features.py']:payloads[('server','tools/value_v11/'+name)]=(V/name).read_bytes()
 before={};roots=dict(server=S,client=C)
 for (root,rel),body in payloads.items():
  p=roots[root]/rel;key=(root,rel.casefold())
  if p.exists():assert key in guards and sha(p)==guards[key]['sha256'],'Unregistered/concurrent target '+str(key)
  else:assert key not in guards
  before[(root,rel)]=p.read_bytes() if p.exists() else None
  if rel.endswith('.py'):compile(body.decode('utf8'),rel,'exec')
  guards[key]=dict(root=root,relative=rel,sha256=hashlib.sha256(body).hexdigest())
 # Preserve every previous guard and informational/stable receipt policy.
 previous_receipt=read(S/parent.RECEIPT);policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in previous_receipt.items() if k!='native_status'})
 if not any(x['root']==policy['root'] and x['relative'].casefold()==policy['relative'].casefold() for x in composition.setdefault('receipt_policies',[])):composition['receipt_policies'].append(policy)
 composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='identity-v11-mul63',revision=revision,native_status='PENDING',one_time_explicit_valuation=True))
 composition['active_valuation']=dict(model_sha256=prepared['model_sha256'],packet='gamedata/valuation-v11.json.gz',policy='append-only calibration events; original seeds/history unchanged')
 manifest=dict(schema=1,revision=revision,client=str(C),parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),guards=composition['guards'],composition=composition,state_shop_replaced=False,model_sha256=prepared['model_sha256'],calibration_revision='identity-anchor-v11-mul63',attribute_repairs=63)
 for rel,body in [(MANIFEST,data(manifest)),(RECEIPT,data(dict(status='INSTALLED_VALUE_IDENTITY_MUL',revision=revision,manifest_sha256=hashlib.sha256(data(manifest)).hexdigest(),state_shop_replaced=False,native_status='PENDING')))]:
  assert not (S/rel).exists();payloads[('server',rel)]=body;before[('server',rel)]=None
 return dict(payloads=payloads,before=before,revision=revision,parent=parent_rel,parent_hash=sha(S/parent_rel),prior=prior)

def install():
 closed()
 with locks():
  closed();p=plan();roots=dict(server=S,client=C)
  print('FRESH_PARENT_PASS',p['parent'],flush=True)
  backup=S/'backups'/p['revision'];backup.mkdir()
  # No formal payload is touched before the protected stop succeeds.
  closed();run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')])
  stopped=True;committed=[];activated=False;state_changed=False;calibrated=False
  try:
   closed();time.sleep(1)
   assert sha(S/p['parent'])==p['parent_hash']
   state_path=S/'gamedata/state.json';state_raw=state_path.read_bytes();state=json.loads(state_raw);shop_hash=sha(S/'gamedata/shop.json')
   (backup/'state-fresh.json').write_bytes(state_raw);shutil.copyfile(S/'gamedata/shop.json',backup/'shop-fresh.json')
   database=S/'gamedata/npc-market-prices.sqlite'
   with closing(sqlite3.connect(database)) as src,closing(sqlite3.connect(backup/'market-prices-fresh.sqlite')) as dst:src.backup(dst)
   with closing(sqlite3.connect(database)) as db:
    seeds_before=db.execute('select * from seeds order by spid').fetchall();events_before=db.execute('select * from price_events order by event_id').fetchall()
   for index,((root,rel),body) in enumerate(p['before'].items()):
    if body is not None:(backup/(str(index)+'-'+Path(rel).name)).write_bytes(body)
   (backup/'transaction.json').write_bytes(data(dict(revision=p['revision'],parent=p['parent'],files=[dict(root=root,relative=rel,before=None if body is None else hashlib.sha256(body).hexdigest(),after=hashlib.sha256(p['payloads'][(root,rel)]).hexdigest()) for (root,rel),body in p['before'].items()])))
   # Commit payloads while services are stopped; launcher is the last activation pointer.
   for key,body in p['payloads'].items():
    if key==('server','play-local.bat'):continue
    closed();root,rel=key;target=roots[root]/rel
    assert (target.read_bytes() if target.exists() else None)==p['before'][key],'CAS failed '+rel
    atomic(target,body);committed.append(key)
   checker=load(S/'tools/player_import/check.py','value_official_player_check');full=checker.validate(S,C,full=True)
   assert full['status']=='PLAYER_IMPORT_FULL_PASS'
   certificate=read(S/'gamedata/player-import-validation.json');assert full==certificate,'Formal full certificate differs from validated artifact'
   store=load(S/'market_price_store.py','value_official_store')
   live=store.MarketPriceStore(database);live.flush(state.get('market_simulation',{}).get('price_events',[]));live.close()
   with closing(sqlite3.connect(database)) as src,closing(sqlite3.connect(backup/'market-before-calibration.sqlite')) as dst:src.backup(dst)
   calibration=store.apply_calibration(database,S/'gamedata/valuation-v11.json.gz');calibrated=True
   packet=store.calibration_packet(S/'gamedata/valuation-v11.json.gz');after=store.migrate_quote_state(state,packet)
   after.get('market_simulation',{})['price_events']=[]
   assert assets(after)==assets(state)
   for k,v in state.get('market_simulation',{}).items():
    if k not in ('quotes','price_events','valuation_revision'):assert after['market_simulation'][k]==v,k
   assert state_path.read_bytes()==state_raw,'State changed while stopped'
   state_after=data(after);atomic(state_path,state_after);state_changed=True
   with closing(sqlite3.connect(database)) as db:
    assert db.execute('select * from seeds order by spid').fetchall()==seeds_before
    assert all(db.execute('select * from price_events where event_id=?',(row[0],)).fetchone()==row for row in events_before)
   closed();key=('server','play-local.bat');assert (S/key[1]).read_bytes()==p['before'][key];atomic(S/key[1],p['payloads'][key]);committed.append(key)
   checked=load(S/SELF,'value_final_gate').preflight(S,C)
   independent=run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py')])
   assert sha(S/'gamedata/shop.json')==shop_hash
   print('OFFICIAL_FULL_PREFLIGHT_PASS',checked['files'],flush=True)
   closed();launcher=start();activated=True;stopped=False
   deadline=time.monotonic()+55
   while time.monotonic()<deadline:
    try:
     probe=api('market_price_store?spid=48167905&grade=1');market=api('market_status')
     if probe.get('active_valuation_model_sha256')==packet['model_sha256'] and market['background']['running'] and market['background']['errors']==0:break
    except Exception as e:last_error=str(e)
    time.sleep(.5)
   else:raise RuntimeError('Activation not verified: '+str(locals().get('last_error')))
   current=read(state_path);assert assets(current)==assets(state),'Asset differences; preserve new progress and investigate'
   assert sha(S/'gamedata/shop.json')==shop_hash
   assert probe['initial_price']!=0 and probe['current_price']==dict(packet['rows'])[48167905]
   hashes={rel:sha(S/rel) for rel in [SELF,MANIFEST,RECEIPT,'play-local.bat']}
   result=dict(status='INSTALLED_AND_LIVE_PASS',revision=p['revision'],backup=str(backup),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',hashes=hashes,preflight=checked,calibration=calibration,attribute_repairs=63,reviewed=67,original_seeds_and_trade_events_preserved=True,asset_projection_equal=True,shop_equal=True,existing_offers_books_preserved=True,only_market_quote_state_changed=True,state_shop_replaced=False,service_restart=True,launcher_pid=launcher,live_price_probe=probe,background=market['background'],official_player_import_full=full['status'],native_game_verified=False,match_verified=False,model_use='explicit one-time calibration, then funded-trade driven; model not reloaded per request')
   (P/'installed-handback.json').write_bytes(data(result));(W/'root-current-top.json').write_bytes(data(dict(result,handoff=str(P/'installed-handback.json'))));print(json.dumps(result,ensure_ascii=False),flush=True)
  except BaseException:
   # Rollback only our own unchanged versions while offline. Never replace a
   # live database/state after restart, or discard newly committed game progress.
   if stopped and not activated:
    closed()
    if state_changed:
     assert (S/'gamedata/state.json').read_bytes()==state_after
     live_state=read(S/'gamedata/state.json');live_state['market_simulation']=state.get('market_simulation',{})
     assert assets(live_state)==assets(state);atomic(S/'gamedata/state.json',data(live_state))
    if calibrated:
     # No process has used the migrated DB yet; restore only this transaction's
     # new price cursors/events, preserving all previous and replayed events.
     with sqlite3.connect(database) as db,sqlite3.connect(backup/'market-before-calibration.sqlite') as old:
      before=dict(old.execute('select spid,basis_price from prices'))
      for sid,price in before.items():
       r=old.execute('select current_price,updated_at,last_event from prices where spid=?',(sid,)).fetchone()
       db.execute('update prices set basis_price=?,current_price=?,updated_at=?,last_event=? where spid=?',(price,*r,sid))
      db.execute("delete from price_events where event_id like 'valuation:identity-anchor-v11-mul63:%'")
      for key in ['valuation_revision','valuation_model_sha256','valuation_prices_sha256']:
       r=old.execute('select value from metadata where key=?',(key,)).fetchone()
       if r:db.execute('insert or replace into metadata values(?,?)',(key,r[0]))
       else:db.execute('delete from metadata where key=?',(key,))
    for key in reversed(committed):
     root,rel=key;target=roots[root]/rel
     if target.read_bytes()!=p['payloads'][key]:raise RuntimeError('Later legitimate change retained; rollback blocked: '+rel)
     old=p['before'][key]
     if old is None:target.unlink()
     else:atomic(target,old)
    start()
   raise

if __name__=='__main__':install()
