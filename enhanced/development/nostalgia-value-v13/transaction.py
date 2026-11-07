def build_folder():return Path(read(P/'latest-build.json')['path'])
def plan():
 out=build_folder();report=read(out/'report.json');audit=read(out/'audit.json')
 assert audit['status']=='PASS' and not audit['strict_failures'] and not audit['dominance_inversions'];assert read(out/'grade-regression.json')['status']=='PASS'
 assert read(P/'engine-regression.json')['status']==read(P/'generation-regression.json')['status']=='PASS'
 for file,h in report['baseline'].items():assert sha(file)==h,'Fresh baseline changed '+file
 for file,h in report['outputs'].items():assert sha(out/file)==h,'Prepared artifact changed '+file
 for file,h in read(P/'runtime-baseline.json').items():assert sha(file)==h,'Runtime changed '+file
 play=(S/'play-local.bat').read_bytes();match=re.search(rb'patches\\(\w+_preflight\.py)',play);parent_rel='patches/'+match[1].decode();assert parent_rel!=SELF
 parent=load(S/parent_rel,'v13_fresh_parent');prior=parent.preflight(S,C);composition=parent.compose_manifest(S,C);validator=load(S/'patches/startup_market_preflight.py','v13_guard_validator');validator.verify_manifest(composition,S,C);guards=validator.table(composition['guards']);oldkeys=set(guards)
 source=(S/parent_rel).read_text('utf8')
 for a,b in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(read(S/parent.RECEIPT)['status'],'INSTALLED_NOSTALGIA_VALUE_V13'),(prior['status'],'NOSTALGIA_VALUE_V13_PREFLIGHT_PASS')]:source=source.replace(a,b)
 assert source.count('fair_value=verify_installed(')==1;source=source.replace('fair_value=verify_installed(','historical_fair_value=verify_installed(',1)
 i=source.index('\n return dict(',source.index('def preflight'))
 source=source[:i]+"\n fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-v13-catalogue.json.gz',server/'gamedata/fair-value-v13-model.json',server/'gamedata/fifadb.sqlite')"+source[i:]
 source=source.replace('return dict(','return dict(historical_fair_value=historical_fair_value,',1)
 extra={('server','gamedata/fair-value-v13-model.json'),('server','gamedata/fair-value-v13-catalogue.json.gz'),('server','gamedata/fair-value-v13-utility-evidence.json.gz')};i=source.index('\n if not required<=seen:');source=source[:i]+'\n required.update('+repr(extra)+')'+source[i:]
 revision='nostalgia-value-v13-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 payloads={('server','fair_value_model.py'):(P/'fair_value_model.py').read_bytes(),('server','fair_value_store.py'):(P/'fair_value_store.py').read_bytes(),('server','gamedata/fair-value-v13-model.json'):(out/'model.json').read_bytes(),('server','gamedata/fair-value-v13-catalogue.json.gz'):(out/'catalogue.json.gz').read_bytes(),('server','gamedata/fair-value-v13-utility-evidence.json.gz'):gzip.compress((out/'utility-evidence.json').read_bytes(),mtime=0),('server','gamedata/fifadb.sqlite'):(out/'fifadb.sqlite').read_bytes(),('client','data/data_0.big'):(out/'data_0.big').read_bytes(),('server','gamedata/custom_rosters.json'):(out/'custom_rosters.json').read_bytes(),('server','gamedata/player-import-validation.json'):(out/'player-import-validation.json').read_bytes(),('server','docs/工程经验与修改边界.txt'):(S/'docs/工程经验与修改边界.txt').read_bytes()+('\n\n'+(P/'设计与安装说明.txt').read_text('utf8')).encode('utf8'),('server',SELF):source.encode('utf8'),('server','play-local.bat'):play.replace(match[0],SELF.replace('/','\\').encode())}
 roots=dict(server=S,client=C);before={}
 for (root,rel),body in payloads.items():
  target=roots[root]/rel;key=(root,rel.casefold());before[(root,rel)]=target.read_bytes() if target.exists() else None
  if target.exists():assert key in guards and sha(target)==guards[key]['sha256'],'Target outside fresh guard '+rel
  else:assert key not in guards
  if rel.endswith('.py'):compile(body.decode('utf8'),rel,'exec')
  guards[key]=dict(root=root,relative=rel,sha256=hashlib.sha256(body).hexdigest())
 assert oldkeys<=set(guards)
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(x['root']==policy['root'] and x['relative'].casefold()==policy['relative'].casefold() for x in composition.setdefault('receipt_policies',[])):composition['receipt_policies'].append(policy)
 composition['guards']=list(guards.values());composition.setdefault('ancestry',[]).append(dict(layer='nostalgia-authentic-attributes-ep-unit-v13',revision=revision,native_status='PENDING'));composition['active_fair_valuation']=dict(model_sha256=report['model_sha256'],profile_sha256=report['profile_sha256'],currency_unit_multiplier=1000,historical_preference='bounded1..1.5; not measured match performance')
 manifest=dict(schema=1,revision=revision,client=str(C),guards=composition['guards'],composition=composition,state_shop_replaced=False,parent=parent_rel,parent_sha256=sha(S/parent_rel),attributes_restored=88)
 for rel,body in [(MANIFEST,data(manifest)),(RECEIPT,data(dict(status='INSTALLED_NOSTALGIA_VALUE_V13',revision=revision,manifest_sha256=hashlib.sha256(data(manifest)).hexdigest(),state_shop_replaced=False,native_status='PENDING')))]:assert not (S/rel).exists();payloads[('server',rel)]=body;before[('server',rel)]=None
 return dict(payloads=payloads,before=before,revision=revision,parent=parent_rel,parent_hash=sha(S/parent_rel),audit=audit,build=report)

def offline_commit(p):
 closed();backup=S/'backups'/p['revision'];backup.mkdir();closed();run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')])
 committed=[];stopped=True;activated=False;migrated=False;state_written=False;roots=dict(server=S,client=C)
 try:
  closed();time.sleep(1);assert sha(S/p['parent'])==p['parent_hash'];statepath=S/'gamedata/state.json';state_raw=statepath.read_bytes();state=json.loads(state_raw);shopsha=sha(S/'gamedata/shop.json');(backup/'state-fresh.json').write_bytes(state_raw);(backup/'shop-fresh.json').write_bytes((S/'gamedata/shop.json').read_bytes());dbpath=S/'gamedata/npc-market-prices.sqlite'
  # Flush the old generation before replacing player attributes, or its profile
  # guard would correctly refuse to replay old committed price movements.
  oldstore=load(S/'market_price_store.py','v13_old_store');live=oldstore.MarketPriceStore(dbpath);live.flush(state.get('market_simulation',{}).get('price_events',[]));live.close()
  with closing(sqlite3.connect(dbpath)) as a,closing(sqlite3.connect(backup/'market-before-v13.sqlite')) as b:a.backup(b)
  with closing(sqlite3.connect(dbpath)) as db:seeds=db.execute('select * from seeds order by spid').fetchall();factors=db.execute('select * from player_market_factors order by playerid').fetchall();old_count=db.execute('select count(*) from price_events').fetchone()[0]
  for i,(key,body) in enumerate(p['before'].items()):
   if body is not None:(backup/(str(i)+'-'+Path(key[1]).name)).write_bytes(body)
  (backup/'transaction.json').write_bytes(data(dict(files=[dict(root=k[0],relative=k[1],before=None if v is None else hashlib.sha256(v).hexdigest(),after=hashlib.sha256(p['payloads'][k]).hexdigest()) for k,v in p['before'].items()])))
  for key,body in p['payloads'].items():
   if key[1]=='play-local.bat':continue
   closed();target=roots[key[0]]/key[1];assert (target.read_bytes() if target.exists() else None)==p['before'][key],'CAS failed '+key[1];atomic(target,body);committed.append(key)
  check=load(S/'tools/player_import/check.py','v13_formal_import');certificate=check.validate(S,C,full=True);assert certificate==read(S/'gamedata/player-import-validation.json')
  maintenance=load(P/'fair_value_store.py','v13_explicit_maintenance_helpers')
  closed();proof=maintenance.install_catalogue(dbpath,S/'gamedata/fair-value-v13-catalogue.json.gz',S/'gamedata/fair-value-v13-model.json',S/'gamedata/fifadb.sqlite');migrated=True
  after=maintenance.migrate_state(state,'nostalgia-utility-ep-v13');after['market_simulation']['price_events']=[];assert assets(after)==assets(state)
  for k,v in state.get('market_simulation',{}).items():
   if k not in ['fair_revision','fair_revision_history','identity_quotes','price_events']:assert after['market_simulation'][k]==v,k
  closed();assert statepath.read_bytes()==state_raw;state_after=data(after);atomic(statepath,state_after);state_written=True
  closed();key=('server','play-local.bat');assert (S/key[1]).read_bytes()==p['before'][key];atomic(S/key[1],p['payloads'][key]);committed.append(key)
  checked=json.loads(run([str(S/'.venv/Scripts/python.exe'),'-X','utf8','-B',str(S/SELF)]));run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py')])
  with closing(sqlite3.connect(dbpath)) as db:
   assert db.execute('select * from seeds order by spid').fetchall()==seeds;assert db.execute('select * from player_market_factors order by playerid').fetchall()==factors;assert db.execute('select count(*) from price_events').fetchone()[0]==old_count+p['audit']['rows']
  assert sha(S/'gamedata/shop.json')==shopsha;closed();launcher=start();activated=True;stopped=False
  return dict(status='FILES_COMMITTED_SERVICE_STARTING',revision=p['revision'],backup=str(backup),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',preflight=checked,profile_binding=proof,launcher_pid=launcher,expected_shop_sha256=shopsha,asset_before=assets(state),seeds_and_earned_market_factors_preserved=True,old_event_count=old_count,restored_cards=88,ep_unit_multiplier=1000,official_full_import=certificate['status'],hashes={rel:sha(S/rel) for rel in [SELF,MANIFEST,RECEIPT,'play-local.bat']},native_verified=False,match_verified=False)
 except BaseException:
  if stopped and not activated:
   closed()
   if state_written:
    assert statepath.read_bytes()==state_after;now=read(statepath);now['market_simulation']=state.get('market_simulation',{});assert assets(now)==assets(state);atomic(statepath,data(now))
   if migrated:
    with closing(sqlite3.connect(dbpath,uri=True)) as db,db:
     db.execute('attach database ? as beforev13',((backup/'market-before-v13.sqlite').as_uri()+'?mode=ro',))
     for sid,event in db.execute('select spid,last_event from prices').fetchall():
      if event!='fair-calibration:nostalgia-utility-ep-v13:'+str(sid):raise RuntimeError('Later price progress retained; rollback refused')
     db.execute('delete from fair_values');db.execute('insert into fair_values select * from beforev13.fair_values');db.execute('delete from player_market_factors');db.execute('insert into player_market_factors select * from beforev13.player_market_factors')
     for row in db.execute('select * from beforev13.prices').fetchall():db.execute('update prices set basis_price=?,current_price=?,updated_at=?,last_event=? where spid=?',(*row[1:],row[0]))
     db.execute("delete from price_events where event_id like 'fair-calibration:nostalgia-utility-ep-v13:%'");db.execute("delete from metadata where key like 'fair_%'");db.execute("insert into metadata select * from beforev13.metadata where key like 'fair_%'")
     for table in ['fair_generation_history','fair_value_history']:
      if not db.execute('select name from beforev13.sqlite_master where name=?',(table,)).fetchone():db.execute('drop table '+table)
      else:db.execute('delete from '+table+" where revision='fair-value-v12'")
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
   probe=api('market_price_store?spid=19176944&grade=1');status=api('market_status');active=api('hot_update_status')
   if probe.get('active_valuation_revision')=='nostalgia-utility-ep-v13' and probe['active_valuation_model_sha256']==p['audit']['model_sha256'] and status['background']['running'] and status['background']['errors']==0 and active['revision']==hot['revision'] and active['watcher_running'] and active['error'] is None and set(active['routes'])==set(hot['routes']):break
  except Exception as exc:last_error=str(exc)
  time.sleep(.5)
 else:raise RuntimeError('Restore not verified; preserve all live progress: '+str(locals().get('last_error')))
 report.update(status='INSTALLED_AND_LIVE_PASS',asset_projection_equal=assets(read(S/'gamedata/state.json'))==report.pop('asset_before'),shop_equal=sha(S/'gamedata/shop.json')==report.pop('expected_shop_sha256'),live_price_probe=probe,background=status['background'],hot_update_status=active,locks_released=True,state_shop_replaced=False,historical_preference_not_measured_playability=True)
 (P/'installed-handback.json').write_bytes(data(report))
 # Another legitimate writer may already have inherited this layer.
 if SELF.replace('/','\\').encode() in (S/'play-local.bat').read_bytes():(W/'root-current-top.json').write_bytes(data(dict(report,handoff=str(P/'installed-handback.json'))))
 print(json.dumps(report,ensure_ascii=False),flush=True);return True
if __name__=='__main__':install()
