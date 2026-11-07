"""Reinforce the season19 card kind: base mean87, elite92/93, preserve identities."""
from pathlib import Path
import collections,copy,datetime,gzip,hashlib,importlib.util,json,math,shutil,sqlite3,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');W=Path('D:/fifaol3')
sys.path[:0]=[str(W/'manutd-legends'),str(S)]
import organize_seasons as resource
TAG='nostalgia-strength-mean87-v15'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 out=P/('build-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));out.mkdir()
 with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as market:meta=dict(market.execute('select key,value from metadata'))
 config=json.loads(meta['fair_model_json']);old_revision=config['revision'];active_model=next(p for p in (S/'gamedata').glob('fair-value-*-model.json') if read(p)['revision']==old_revision)
 paths=[S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',S/'responses/static_roster.json',C/'data/data_0.big',S/'fair_value_model.py',S/'fair_value_store.py',active_model,S/'tools/player_import/check.py']
 baseline={str(p):sha(p) for p in paths};weights=resource.weights();shutil.copyfile(paths[0],out/'fifadb.sqlite');stats=resource.STATS
 with sqlite3.connect(out/'fifadb.sqlite') as db:
  db.row_factory=sqlite3.Row;rows=[dict(p) for p in db.execute('select * from players where spid/1000000=19 order by spid')];assert len(rows)==88
  bases=[resource.primary(r,weights) for r in rows];lo,hi=0.,40.
  for _ in range(90):
   mid=(lo+hi)/2
   if sum(min(93,max(85,b+mid)) for b in bases)<87*len(rows):lo=mid
   else:hi=mid
  ideal=[min(93,max(85,b+(lo+hi)/2)) for b in bases];targets=[math.floor(v+1e-10) for v in ideal];left=87*len(rows)-sum(targets)
  order=sorted(range(len(rows)),key=lambda i:(-(ideal[i]-targets[i]),-bases[i],rows[i]['spid']))
  assert 0<=left<len(rows)
  for i in order[:left]:targets[i]+=1
  assert sum(targets)==87*88 and min(targets)>=85 and max(targets)==93 and 92 in targets
  changes=[]
  for old,before,target in zip(rows,bases,targets):
   choices=[]
   for shift in range(65):
    values={k:min(99,max(1,old[k]+shift)) for k in stats};value=resource.primary({**old,**values},weights);choices.append(((abs(value-target),shift),values,value,shift))
   _,values,value,shift=min(choices,key=lambda x:x[0]);assert value==target
   update={**values,'overallrating':target,'potential':max(target,old['potential'])};db.execute('update players set '+','.join(k+'=?' for k in update)+' where spid=?',list(update.values())+[old['spid']])
   now=dict(db.execute('select * from players where spid=?',(old['spid'],)).fetchone());assert all(now[k]==v for k,v in old.items() if k not in update)
   changes.append(dict(spid=old['spid'],playerid=old['playerid'],before_base=before,after_base=target,shift=shift,changed_fields=[k for k in update if update[k]!=old[k]]))
  db.commit();db.execute('attach database ? as original',(str(paths[0]),))
  for table, in db.execute("select name from main.sqlite_master where type='table'").fetchall():
   table='"'+table.replace('"','""')+'"';where=' where spid/1000000<>19' if table=='"players"' else ''
   assert not db.execute('select * from main.'+table+where+' except select * from original.'+table+where+' limit 1').fetchone(),table
   assert not db.execute('select * from original.'+table+where+' except select * from main.'+table+where+' limit 1').fetchone(),table
   assert db.execute('select count(*) from main.'+table).fetchone()==db.execute('select count(*) from original.'+table).fetchone()
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  registry=read(paths[1]);by_spid={r['spid']:r for r in changes};updated=0
  for card in registry['cards']:
   change=by_spid.get(card['fo3_spid'])
   if change:
    if card.get('attribute_correction'):card.setdefault('attribute_correction_history',[]).append(card['attribute_correction'])
    card.update(base_ovr=change['after_base'],display_plus1_ovr=change['after_base']+5,attribute_correction=dict(revision=TAG,policy='enhanced card kind; primary base mean87, floor85, elite92/93; profile-preserving affine stats capped99',before_base=change['before_base'],after_base=change['after_base'],changed_fields=change['changed_fields']));updated+=1
  assert updated==88;save(out/'custom_rosters.json',registry)
  roster=read(paths[2]);original=copy.deepcopy(roster['seasons']);ranked=[]
  for i,e in enumerate(roster['seasons']):
   values=[resource.primary(dict(r),weights) for r in db.execute('select * from players where spid/1000000 in ('+','.join('?' for _ in e['value'])+')',e['value'])];assert values;ranked.append((sum(values)/len(values),max(values),i,e))
  ranked.sort(key=lambda x:(-x[0],-x[1],x[2]));roster['seasons']=[r[3] for r in ranked];assert sorted(json.dumps(e,sort_keys=True) for e in original)==sorted(json.dumps(e,sort_keys=True) for e in roster['seasons']);save(out/'static_roster.json',roster)
 codec=resource.codec;member='data/db2/fifadb.db.db2';decoded=bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(C/'data/data_0.big',member)));assert b'SQLite format 3\0'+decoded[16:]==paths[0].read_bytes()
 big=out/'data_0.big';shutil.copyfile(C/'data/data_0.big',big);encoded=resource.encrypted_sqlite(decoded,(out/'fifadb.sqlite').read_bytes());codec.replace_member(big,member,codec.refpack(encoded),len(encoded))
 assert b'SQLite format 3\0'+bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(big,member)))[16:]==(out/'fifadb.sqlite').read_bytes()
 layout=load(S/'tools/check_data0_layout.py','nostalgia87_layout').inspect(big,baseline=C/'data/data_0.big',changed_members={member},expected_count=len(codec.bigdir.entries(C/'data/data_0.big')));assert layout['status']=='PASS';save(out/'layout.json',layout)
 checker=load(S/'tools/player_import/check.py','nostalgia87_import');certificate=checker.validate(S,C,database=out/'fifadb.sqlite',data0=big,registry=out/'custom_rosters.json',full=True);assert certificate['status']=='PLAYER_IMPORT_FULL_PASS';save(out/'player-import-validation.json',certificate)
 model=load(S/'fair_value_model.py','nostalgia87_fair_model');config=copy.deepcopy(config);config.update(revision=TAG,previous_revision=old_revision);config['nostalgia_strength_policy']=dict(season=19,cards=88,base_mean=87,base_range=[85,93],native_gameplay_or_model_changes=False)
 catalogue=model.build_catalogue(out/'fifadb.sqlite',config);catalogue['expected_previous_revision']=old_revision;save(out/'model.json',config)
 (out/'catalogue.json.gz').write_bytes(gzip.compress(model.canonical(catalogue),mtime=0));model.verify_profiles(out/'fifadb.sqlite',catalogue,config)
 # Preserve all current curve parameters and same-player factors. Only the88 profiles change.
 with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert dict(db.execute('select key,value from metadata'))['fair_revision']==old_revision
  before_profiles={r[0]:tuple(r[1:]) for r in db.execute('select spid,playerid,economic_value,strict_floor,effective_score,profile_sha256 from fair_values')}
 changed_profiles=[]
 for r in catalogue['rows']:
  value=(r['playerid'],r['economic_value'],r['strict_floor_ep'],r['effective_score'],r['profile_sha256'])
  if value!=before_profiles[r['spid']]:changed_profiles.append(r['spid'])
 assert set(changed_profiles)==set(by_spid)
 market=out/'price-regression.sqlite'
 with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(market) as dst:src.backup(dst)
 store=load(S/'fair_value_store.py','nostalgia87_price_regression')
 with sqlite3.connect(market) as db:old_prices=dict(db.execute('select spid,current_price from prices'));old_factors=db.execute('select * from player_market_factors order by playerid').fetchall();old_events=db.execute('select count(*) from price_events').fetchone()[0]
 store.install_catalogue(market,out/'catalogue.json.gz',out/'model.json',out/'fifadb.sqlite');valuation=store.verify_installed(market,out/'catalogue.json.gz',out/'model.json',out/'fifadb.sqlite')
 with sqlite3.connect(market) as db:
  assert db.execute('select * from player_market_factors order by playerid').fetchall()==old_factors
  assert all(price==old_prices[sid] for sid,price in db.execute('select spid,current_price from prices') if sid not in by_spid)
  assert db.execute('select count(*) from price_events').fetchone()[0]==old_events+len(catalogue['rows'])
 for p,h in baseline.items():assert sha(p)==h,('Refresh changed baseline',p)
 save(out/'changes.json',changes)
 report=dict(status='PREPARED_AND_REGRESSION_PASS',output=str(out),baseline=baseline,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='price-regression.sqlite'},cards=88,before_mean=sum(bases)/88,after_mean=87.0,base_distribution=dict(sorted(collections.Counter(targets).items())),all_non_target_rows_exact=True,identity_models_traits_stars_positions_preserved=True,layout=layout['status'],player_import=certificate['status'],fair_profile_binding=valuation,only_88_valuation_profiles_changed=True,other_current_prices_preserved_in_temporary_regression=True,player_market_factors_preserved=True,enhancement_curve_unchanged=True,old_revision=old_revision,new_revision=TAG,model_sha256=catalogue['model_sha256'],profile_sha256=catalogue['profile_sha256'],real_assets_written=False,native_ui_verified=False)
 save(out/'report.json',report);save(P/'latest-build.json',dict(path=str(out)));print(json.dumps({k:v for k,v in report.items() if k not in ('baseline','outputs')},ensure_ascii=True),flush=True)
if __name__=='__main__':main()
