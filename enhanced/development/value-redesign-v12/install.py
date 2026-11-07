"""Official fair-value publication. No client operation or active-game restart."""
from pathlib import Path
from contextlib import closing,contextmanager
import copy,datetime,gzip,hashlib,importlib.util,json,os,re,sqlite3,subprocess,sys,time,urllib.request
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3')
SELF='patches/fair_value_v12_preflight.py';MANIFEST='patches/fair-value-v12-installed.json';RECEIPT='patches/fair-value-v12-receipt.json'
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
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.fair-v12.tmp');tmp.write_bytes(body);os.replace(tmp,p)
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
   p=S/n;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);b=data(dict(owner='fair-value-v12',pid=os.getpid(),scope='fair curve/catalogue, price store and market exact adapters, child metadata/docs/play',handoff=str(P/'installed-handback.json')));own.append((p,fd,b));os.write(fd,b);os.fsync(fd)
  yield
 finally:
  for p,fd,b in reversed(own):
   os.close(fd)
   if p.exists() and p.read_bytes()==b:p.unlink()
def plan():
 audit=read(P/'audit.json');assert audit['status']=='PASS' and read(P/'engine-regression.json')['status']=='PASS'
 assert read(P/'grade-regression.json')['status']=='PASS'
 assert not audit['strict_failures'] and not audit['dominance_inversions']
 from fair_value_model import verify_profiles
 from fair_value_store import read_catalogue
 verify_profiles(S/'gamedata/fifadb.sqlite',read_catalogue(P/'catalogue.json.gz'),read(P/'model.json'))
 for f,h in read(P/'runtime-baseline.json').items():assert sha(f)==h,'Runtime changed; rebase adapter '+f
 play=(S/'play-local.bat').read_bytes();match=re.search(rb'patches\\(\w+_preflight\.py)',play);assert match;parent_rel='patches/'+match[1].decode()
 if parent_rel==SELF:raise RuntimeError('Already installed; inspect handback instead of replaying publication')
 parent=load(S/parent_rel,'fair_current_parent');prior=parent.preflight(S,C);comp=parent.compose_manifest(S,C)
 validator=load(S/'patches/startup_market_preflight.py','fair_guard_validator');validator.verify_manifest(comp,S,C);guards=validator.table(comp['guards']);oldkeys=set(guards)
 revision='fair-value-v12-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 source=(S/parent_rel).read_text('utf8')
 for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_FAIR_VALUE_V12'),(prior['status'],'FAIR_VALUE_V12_PREFLIGHT_PASS')]:source=source.replace(old,new)
 extra={('server','fair_value_model.py'),('server','fair_value_store.py'),('server','gamedata/fair-value-v12-model.json'),('server','gamedata/fair-value-v12-catalogue.json.gz')}
 i=source.index('\n if not required<=seen:');source=source[:i]+'\n required.update('+repr(extra)+')'+source[i:]
 i=source.index('\n return dict(',source.index('def preflight'))
 source=source[:i]+"\n import sys\n sys.path.insert(0,str(server))\n from fair_value_store import verify_installed\n fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-v12-catalogue.json.gz',server/'gamedata/fair-value-v12-model.json',server/'gamedata/fifadb.sqlite')"+source[i:]
 source=source.replace('return dict(china_future_prices=', 'return dict(fair_value=fair_value,china_future_prices=',1).replace('runtime_model_loaded=False','runtime_model_loaded=True')
 assert 'fair_value=fair_value' in source
 docs=(S/'docs/工程经验与修改边界.txt').read_bytes()+('\n\n'+(P/'设计与验收说明.txt').read_text('utf8')).encode('utf8')
 payloads={('server',n):(P/n).read_bytes() for n in ['fair_value_model.py','fair_value_store.py','market_price_store.py','npc_exchange.py','market_simulation.py']}
 payloads.update({('server','gamedata/fair-value-v12-model.json'):(P/'model.json').read_bytes(),('server','gamedata/fair-value-v12-catalogue.json.gz'):(P/'catalogue.json.gz').read_bytes(),('server','docs/工程经验与修改边界.txt'):docs,('server',SELF):source.encode('utf8'),('server','play-local.bat'):play.replace(match[0],SELF.replace('/','\\').encode())})
 before={}
 for (root,rel),body in payloads.items():
  p=S/rel;key=(root,rel.casefold());before[(root,rel)]=p.read_bytes() if p.exists() else None
  if p.exists():assert key in guards and sha(p)==guards[key]['sha256'],'Current target differs '+rel
  else:assert key not in guards
  if rel.endswith('.py'):compile(body.decode('utf8'),rel,'exec')
  guards[key]=dict(root=root,relative=rel,sha256=hashlib.sha256(body).hexdigest())
 assert oldkeys<=set(guards)
 pol=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(x['root']==pol['root'] and x['relative'].casefold()==pol['relative'].casefold() for x in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(pol)
 comp['guards']=list(guards.values());comp.setdefault('ancestry',[]).append(dict(layer='fair-value-v12',revision=revision,native_status='PENDING'))
 comp['active_fair_valuation']=dict(model_sha256=audit['model_sha256'],profile_sha256=audit['profile_sha256'],profile_binding='semantic all33+identity+native stars; attribute and catalogue must publish together',shared_market_factor=[.85,1.15])
 m=dict(schema=1,revision=revision,client=str(C),guards=comp['guards'],composition=comp,state_shop_replaced=False,parent=parent_rel,parent_sha256=sha(S/parent_rel))
 for rel,body in [(MANIFEST,data(m)),(RECEIPT,data(dict(status='INSTALLED_FAIR_VALUE_V12',revision=revision,manifest_sha256=hashlib.sha256(data(m)).hexdigest(),state_shop_replaced=False,native_status='PENDING')))]:assert not (S/rel).exists();payloads[('server',rel)]=body;before[('server',rel)]=None
 return dict(payloads=payloads,before=before,revision=revision,parent=parent_rel,parent_hash=sha(S/parent_rel),preflight=prior,audit=audit)
def offline_commit(p):
 closed();backup=S/'backups'/p['revision'];backup.mkdir();closed()
 run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')])
 committed=[];stopped=True;activated=False;migrated=False;state_written=False
 try:
  closed();time.sleep(1);assert sha(S/p['parent'])==p['parent_hash']
  statepath=S/'gamedata/state.json';state_raw=statepath.read_bytes();state=json.loads(state_raw);shopsha=sha(S/'gamedata/shop.json');(backup/'state-fresh.json').write_bytes(state_raw);(backup/'shop-fresh.json').write_bytes((S/'gamedata/shop.json').read_bytes())
  dbpath=S/'gamedata/npc-market-prices.sqlite'
  # Replay already committed asset transactions before taking the rollback cursor.
  oldstore=load(S/'market_price_store.py','fair_legacy_store');store=oldstore.MarketPriceStore(dbpath);store.flush(state.get('market_simulation',{}).get('price_events',[]));store.close()
  with closing(sqlite3.connect(dbpath)) as a,closing(sqlite3.connect(backup/'market-before-fair.sqlite')) as b:a.backup(b)
  with closing(sqlite3.connect(dbpath)) as db:seeds=db.execute('select * from seeds order by spid').fetchall();old_events=db.execute('select count(*) from price_events').fetchone()[0]
  for i,(key,body) in enumerate(p['before'].items()):
   if body is not None:(backup/(str(i)+'-'+Path(key[1]).name)).write_bytes(body)
  (backup/'transaction.json').write_bytes(data(dict(revision=p['revision'],files=[dict(root=k[0],relative=k[1],before=None if b is None else hashlib.sha256(b).hexdigest(),after=hashlib.sha256(p['payloads'][k]).hexdigest()) for k,b in p['before'].items()])))
  for key,body in p['payloads'].items():
   if key[1]=='play-local.bat':continue
   closed();target=S/key[1];assert (target.read_bytes() if target.exists() else None)==p['before'][key],'Target CAS failed '+key[1];atomic(target,body);committed.append(key)
  # Use the new pure helper in this installer; no runtime imports/reloads or hooks.
  from fair_value_store import install_catalogue,migrate_state
  closed()
  proof=install_catalogue(dbpath,S/'gamedata/fair-value-v12-catalogue.json.gz',S/'gamedata/fair-value-v12-model.json',S/'gamedata/fifadb.sqlite');migrated=True
  after=migrate_state(state,read(P/'model.json')['revision']);after['market_simulation']['price_events']=[]
  assert assets(after)==assets(state)
  for k,v in state.get('market_simulation',{}).items():
   if k not in ['price_events','fair_revision','identity_quotes']:assert after['market_simulation'][k]==v,k
  closed();assert statepath.read_bytes()==state_raw;state_after=data(after);atomic(statepath,state_after);state_written=True
  closed();key=('server','play-local.bat');assert (S/key[1]).read_bytes()==p['before'][key];atomic(S/key[1],p['payloads'][key]);committed.append(key)
  # New process resolves formal modules only (the installer's task directory is
  # never allowed to masquerade as the actual running server).
  checked=json.loads(run([str(S/'.venv/Scripts/python.exe'),'-X','utf8','-B',str(S/SELF)]))
  player_check=run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py')])
  with closing(sqlite3.connect(dbpath)) as db:
   assert db.execute('select * from seeds order by spid').fetchall()==seeds
   assert db.execute('select count(*) from price_events').fetchone()[0]==old_events+len(read(P/'preview-prices.json'))
  assert sha(S/'gamedata/shop.json')==shopsha
  closed();launcher=start();activated=True;stopped=False
  return dict(status='FILES_COMMITTED_SERVICE_STARTING',revision=p['revision'],backup=str(backup),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',preflight=checked,profile_binding=proof,launcher_pid=launcher,expected_shop_sha256=shopsha,asset_before=assets(state),old_event_count=old_events,seeds_unchanged=True,player_import=player_check,hashes={rel:sha(S/rel) for rel in [SELF,MANIFEST,RECEIPT,'play-local.bat']},native_verified=False,match_verified=False)
 except BaseException:
  if stopped and not activated:
   closed()
   if state_written:
    assert statepath.read_bytes()==state_after;current=read(statepath);current['market_simulation']=state.get('market_simulation',{});assert assets(current)==assets(state);atomic(statepath,data(current))
   if migrated:
    with closing(sqlite3.connect(dbpath)) as db,closing(sqlite3.connect(backup/'market-before-fair.sqlite')) as old,db:
     for row in read(P/'preview-prices.json'):
      sid=row['spid'];actual=db.execute('select current_price,last_event from prices where spid=?',(sid,)).fetchone()
      if actual!=(row['fair_price_ep'],'fair-calibration:fair-value-v12:'+str(sid)):raise RuntimeError('Later price progress retained; rollback refused')
     for row in old.execute('select spid,basis_price,current_price,updated_at,last_event from prices'):db.execute('update prices set basis_price=?,current_price=?,updated_at=?,last_event=? where spid=?',(*row[1:],row[0]))
     db.execute("delete from price_events where event_id like 'fair-calibration:fair-value-v12:%'");db.execute('drop table fair_values');db.execute('drop table player_market_factors');db.execute("delete from metadata where key like 'fair_%'")
   for key in reversed(committed):
    target=S/key[1]
    if target.read_bytes()!=p['payloads'][key]:raise RuntimeError('Later legitimate change retained; cannot rollback '+key[1])
    if p['before'][key] is None:target.unlink()
    else:atomic(target,p['before'][key])
   start()
  raise
def install():
 if game_running():
  result=dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_written=False);(P/'pending-handback.json').write_bytes(data(result));print(json.dumps(result,ensure_ascii=False));return False
 with locks():
  closed();p=plan();hot=api('hot_update_status');print('FRESH_PARENT_PASS',p['parent'],flush=True);report=offline_commit(p)
 # Hot watcher shares publication locks: release before waiting for restoration.
 (P/'commit-handback.json').write_bytes(data({k:v for k,v in report.items() if k!='asset_before'}));deadline=time.monotonic()+60
 while time.monotonic()<deadline:
  try:
   probe=api('market_price_store?spid=84000250&grade=1');status=api('market_status');active=api('hot_update_status')
   if probe.get('mode')=='bounded_same_player_curve' and probe.get('active_valuation_model_sha256')==p['audit']['model_sha256'] and status['background']['running'] and status['background']['errors']==0 and active['revision']==hot['revision'] and active['watcher_running'] and active['error'] is None and set(active['routes'])==set(hot['routes']):break
  except Exception as e:last_error=str(e)
  time.sleep(.5)
 else:raise RuntimeError('Service/hot readiness not confirmed; preserve new transactions: '+str(locals().get('last_error')))
 current=read(S/'gamedata/state.json');same=assets(current)==report.pop('asset_before');shop=sha(S/'gamedata/shop.json')==report.pop('expected_shop_sha256')
 report.update(status='INSTALLED_AND_LIVE_PASS',asset_projection_equal=same,shop_equal=shop,live_price_probe=probe,background=status['background'],hot_update_status=active,locks_released=True,state_shop_replaced=False,model_use='transparent fair curve with profile-bound compiled values and shared-player funded-trade factors')
 if not same or not shop:report['progress_policy']='New live differences preserved; inspect, never restore old assets'
 (P/'installed-handback.json').write_bytes(data(report));(W/'root-current-top.json').write_bytes(data(dict(report,handoff=str(P/'installed-handback.json'))));print(json.dumps(report,ensure_ascii=False),flush=True);return True
if __name__=='__main__':install()
