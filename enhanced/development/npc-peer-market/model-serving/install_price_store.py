"""Direct official install: one-time neural seed and independent NPC warehouse."""
from pathlib import Path
from contextlib import closing
import copy,datetime,hashlib,importlib.util,json,os,re,shutil,sqlite3,subprocess,sys,time,urllib.request
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def body(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(args):
 r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
def stop():
 run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')])
 run(['powershell.exe','-NoProfile','-Command',r"Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match '(?i)D:\\FO3ID\\server\\start_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }"])
 time.sleep(.5)
def start():
 env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
 with (P/'service.stdout.log').open('ab') as out,(P/'service.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
 return p.pid
def api(name,timeout=5):
 with urllib.request.urlopen('http://127.0.0.1:8088/api/'+name,timeout=timeout) as r:return json.load(r)
def assets(s):return {k:v for k,v in s.items() if k!='market_simulation'}
def profile_digest(fields):
 with closing(sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  rows=[list(r) for r in db.execute('select spid,'+','.join(fields)+' from players order by spid')]
 return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
owned=[];written=[];baseline={};after_hash={};stopped=False;backup=None;db_created=False
try:
 for name in ('.shop-release.lock','.fo3-publish.lock'):
  path=S/name;fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_BINARY);value=body(dict(owner='one-time-market-prices-independent-npcs',pid=os.getpid(),scope='market_price_store.py,npc_exchange.py,market_simulation.py,seed,mutable price DB,new child guards,play',handoff=str(P/'installed-handback.json')));os.write(fd,value);os.fsync(fd);owned.append((path,fd,value))
 print('LOCKED',flush=True)
 launcher=(S/'play-local.bat').read_bytes();match=re.search(rb'patches\\([A-Za-z_]+_preflight\.py)',launcher);assert match
 parent_rel='patches/'+match[1].decode();parent=module(S/parent_rel,'_price_parent');parent_check=parent.preflight(S,C);composed=parent.compose_manifest(S,C)
 print('PARENT_PASS',parent_rel,parent_check['files'],flush=True)
 expected=json.loads((P/'source-baseline.json').read_text('utf8'))
 for rel,digest in expected.items():assert sha(S/rel)==digest,'Source changed; rebase '+rel
 regression=json.loads((P/'regression.json').read_text());npc_regression=json.loads((P/'independent-npc-regression.json').read_text());assert regression['status']==npc_regression['status']=='PASS'
 seed_report=json.loads((P/'seed-report.json').read_text('utf8'))
 if profile_digest(seed_report['profile_fields'])!=seed_report['profile_sha256']:
  print('REFRESHING_CHANGED_CARD_INITIALS',flush=True)
  r=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-X','utf8','-u',str(P/'build_initial_prices.py')],cwd=W,stdout=sys.stdout,stderr=sys.stderr,creationflags=subprocess.CREATE_NO_WINDOW);assert r.returncode==0
  seed_report=json.loads((P/'seed-report.json').read_text('utf8'))
 assert profile_digest(seed_report['profile_fields'])==seed_report['profile_sha256']
 guards={(g['root'],g['relative'].replace('\\','/').casefold()):copy.deepcopy(g) for g in composed['guards']};assert len(guards)==len(composed['guards'])
 oldkeys=set(guards);stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');revision='market-price-store-'+stamp;backup=S/'backups'/revision;backup.mkdir()
 targets={name:(P/name).read_bytes() for name in ('market_price_store.py','npc_exchange.py','market_simulation.py','market_price_store_preflight.py')};targets['patches/market_price_store_preflight.py']=targets.pop('market_price_store_preflight.py')
 targets['gamedata/npc-market-seed.json.gz']=(P/'initial-price-seed.json.gz').read_bytes()
 targets['play-local.bat']=launcher.replace(match[0],b'patches\\market_price_store_preflight.py')
 M='patches/market-price-store-installed.json';R='patches/market-price-store-receipt.json';assert not (S/M).exists() and not (S/R).exists()
 for rel,data in targets.items():
  path=S/rel;key=('server',rel.casefold())
  if path.exists():
   assert key in guards and sha(path)==guards[key]['sha256'],rel;baseline[rel]=path.read_bytes();dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(baseline[rel])
  else:assert key not in guards;baseline[rel]=None
  if rel.endswith('.py'):compile(data.decode('utf-8-sig'),rel,'exec')
 # A running match is a timing constraint, never a reason to close the client.
 live_state=json.loads((S/'gamedata/state.json').read_text('utf8'))
 game_open=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],creationflags=subprocess.CREATE_NO_WINDOW).returncode==9
 if game_open and live_state.get('match',{}).get('stage') not in (None,'closed','finished'):raise RuntimeError('MATCH_ACTIVE_RESTART_DEFERRED: all install inputs prepared, wait for match completion')
 # The current parent is still physical here; stop once, then fresh asset snapshot.
 stop();stopped=True
 for rel in ('gamedata/state.json','gamedata/shop.json'):shutil.copyfile(S/rel,backup/Path(rel).name)
 before=json.loads((backup/'state.json').read_text('utf8'));dbpath=S/'gamedata/npc-market-prices.sqlite'
 if dbpath.exists():
  with closing(sqlite3.connect(dbpath)) as src,closing(sqlite3.connect(backup/'npc-market-prices.sqlite')) as dest:src.backup(dest)
 for rel,data in targets.items():
  path=S/rel;assert (path.read_bytes() if path.exists() else None)==baseline[rel],rel
  temp=path.with_name(path.name+'.market-install');temp.write_bytes(data);os.replace(temp,path);written.append(rel);after_hash[rel]=sha(path);guards[('server',rel.casefold())]=dict(root='server',relative=rel,sha256=after_hash[rel])
 storemod=module(S/'market_price_store.py','_price_store_install');db_created=storemod.initialize(dbpath,S/'gamedata/npc-market-seed.json.gz',revision)
 composition=copy.deepcopy(composed);composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='one-time-market-seed-independent-npcs',revision=revision,native_status='PENDING',runtime_model_loaded=False))
 composition['mutable_market_store']=dict(database='gamedata/npc-market-prices.sqlite',policy='Never hash current prices or reseed on startup. Verify immutable seeds against gamedata/npc-market-seed.json.gz.',model_sha256=seed_report['model_sha256'])
 parent_receipt=getattr(parent,'RECEIPT',None)
 if parent_receipt:
  old_receipt=json.loads((S/parent_receipt).read_text('utf-8-sig'));pol=dict(root='server',relative=parent_receipt,installation_fields={k:v for k,v in old_receipt.items() if k!='native_status'})
  if not any(p['root']==pol['root'] and p['relative'].casefold()==pol['relative'].casefold() for p in composition.setdefault('receipt_policies',[])):composition['receipt_policies'].append(pol)
 assert oldkeys<=set(guards)
 manifest=dict(schema=1,revision=revision,client=str(C),parent=parent_rel,guards=list(guards.values()),composition=composition,state_shop_replaced=False,backup=str(backup),mutable_files=['gamedata/npc-market-prices.sqlite'],source_hashes=after_hash,seed_rows=seed_report['rows'],model_sha256=seed_report['model_sha256'])
 manifest_bytes=body(manifest);receipt=body(dict(status='INSTALLED_MARKET_PRICE_STORE',revision=revision,manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),native_status='PENDING',state_shop_replaced=False))
 for rel,data in ((M,manifest_bytes),(R,receipt)):
  baseline[rel]=None;(S/rel).write_bytes(data);written.append(rel);after_hash[rel]=sha(S/rel)
 checker=module(S/'patches/market_price_store_preflight.py','_price_store_final');checked=checker.preflight(S,C)
 print('INSTALLED_PREFLIGHT_PASS',checked['files'],flush=True)
 parent_pid=start();stopped=False;deadline=time.monotonic()+50;status=None;prices=None
 while time.monotonic()<deadline:
  try:
   status=api('market_status');prices=api('market_price_store?spid=30238380&grade=1')
   npc=status.get('npc_exchange',{})
   if status['background']['running'] and status['background']['errors']==0 and npc.get('inventory_cap','old') is None and prices.get('runtime_model_loaded') is False and prices.get('last_error') is None:break
  except Exception as exc:last_error=str(exc)
  time.sleep(.5)
 else:raise RuntimeError('Live new market startup failed: '+str(status or locals().get('last_error')))
 live=json.loads((S/'gamedata/state.json').read_text('utf8'));asset_equal=assets(before)==assets(live);shop_equal=sha(S/'gamedata/shop.json')==sha(backup/'shop.json')
 assert shop_equal,'Shop file changed during install; investigate rather than restore'
 if not asset_equal:
  print('CONCURRENT_ASSET_PROGRESS_PRESERVED',flush=True)
  (P/'concurrent-asset-progress.json').write_bytes(body(dict(before=assets(before),after=assets(live),policy='Never restore old state; preserve any user progress')))
 report=dict(status='INSTALLED_AND_LIVE',revision=revision,parent=parent_rel,top='patches/market_price_store_preflight.py',compose_api='compose_manifest(server=None,client=None)',preflight=checked,backup=str(backup),services_parent_pid=parent_pid,initial_price_rows=seed_report['rows'],price_database=str(dbpath),runtime_model_loaded=False,model_use='one-time initialization only',model_sha256=seed_report['model_sha256'],inventory_policy='unbounded internal warehouse; player-visible inventory is reserved; no public-pool buys; simulated consumption',asset_projection_equal=asset_equal,shop_equal=shop_equal,real_state_replaced=False,native_verified=False,live_price_probe=prices,live_npc=status['npc_exchange'],background=status['background'],hashes={rel:sha(S/rel) for rel in ('patches/market_price_store_preflight.py',M,R)},writer_released_on_exit=True,coordinator_delivery='Coordinator archived; attempted pre-install notification could not be delivered. Shared file handback and latest-root descriptor written.')
 (P/'installed-handback.json').write_bytes(body(report))
 descriptor=dict(status='INSTALLED_MARKET_PRICE_STORE_API_PASS_NATIVE_PENDING',observed_at=datetime.datetime.now().isoformat(),top_preflight=str(S/'patches/market_price_store_preflight.py'),top_manifest=str(S/M),top_receipt=str(S/R),files={str(S/rel):sha(S/rel) for rel in ('patches/market_price_store_preflight.py',M,R,'play-local.bat')},composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),mutable_market_store=str(dbpath),handoff=str(P/'installed-handback.json'),services_restored=True,state_shop_replaced=False,native_verified=False,preflight=checked)
 (W/'root-current-top.json').write_bytes(body(descriptor))
 print(json.dumps(dict(status=report['status'],top=report['top'],parent=parent_rel,seed_rows=seed_report['rows'],assets_unchanged=asset_equal,price_probe=prices,npc_policy={k:status['npc_exchange'].get(k) for k in ('owned_cards','inventory_cap','listed_cards','public_listing_cap','public_pool_purchases_since_v2','internal_source_buys','consumed_cards')}),ensure_ascii=False),flush=True)
except Exception:
 if written:
  try:stop();stopped=True
  except Exception as e:print('Rollback stop failed',repr(e),file=sys.stderr)
  for rel in reversed(written):
   path=S/rel
   if path.exists() and sha(path)==after_hash[rel]:
    if baseline[rel] is None:path.unlink()
    else:path.write_bytes(baseline[rel])
  # Mutable prices, state and shop are never restored or deleted on rollback.
  if stopped:start();stopped=False
 elif stopped:start();stopped=False
 raise
finally:
 for path,fd,value in reversed(owned):
  os.close(fd)
  if path.exists() and path.read_bytes()==value:path.unlink()
