"""Prepare authentic season19 attributes, evidence premiums and an EP-scale revision."""
from pathlib import Path
from contextlib import closing
import collections,copy,datetime,gzip,hashlib,importlib.util,json,math,shutil,sqlite3,statistics,sys
P=Path(__file__).resolve().parent;W=Path('D:/fifaol3');S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(P));sys.path.append(str(S))
import fair_value_model as model
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf8')
def load(p,name):
 sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def utility_factors(config):
 with gzip.open(W/'npc-peer-market/anchor-retraining-v10/training-data.json.gz','rt',encoding='utf8') as f:data=[r for r in json.load(f) if r['kind']=='real']
 roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split();groups=collections.defaultdict(list)
 for r in data:
  r['score']=model.effective_score(r['attributes']|{'playerid':r['playerid']},config);r['logcurve']=math.log(model.economic_curve(r['score'],config));groups[(r['spid']//1000000,roles[r['attributes']['preferredposition1']])].append(r)
 evidence=collections.defaultdict(list)
 for (season,role),group in groups.items():
  if len(group)<12:continue
  for r in group:
   peers=sorted((x for x in group if x['playerid']!=r['playerid']),key=lambda x:abs(x['score']-r['score']))[:12]
   if len(peers)<8 or max(abs(x['score']-r['score']) for x in peers)>5:continue
   expected=statistics.median(math.log(x['price'])+r['logcurve']-x['logcurve'] for x in peers)
   evidence[r['playerid']].append(dict(spid=r['spid'],season=season,role=role,source_price=r['price'],log_residual=math.log(r['price'])-expected,peer_spids=[x['spid'] for x in peers],source_url=r['source_url']))
 result={};old=config.get('identity_factors',{});pids={r['playerid'] for r in data}|{int(x) for x in old}
 for pid in pids:
  observations=evidence.get(pid,[])
  if len(observations)>=2:
   shift=statistics.median(x['log_residual'] for x in observations)*len(observations)/(len(observations)+6)
   factor=min(1.5,max(1.,math.exp(max(-50,min(50,shift)))));kind='historical_same_season_role_near_ability_preference'
  else:factor=max(1.,old.get(str(pid),{}).get('factor',1.));kind='prior_bounded_anchor' if factor>1 else 'neutral_no_reliable_history'
  result[str(pid)]=dict(factor=factor,real_quotes=len(observations),evidence_kind=kind,not_measured_native_playability=True)
 return result,evidence
def main():
 out=P/('build-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
 baseline={str(p):sha(p) for p in [S/'gamedata/fifadb.sqlite',S/'gamedata/custom_rosters.json',C/'data/data_0.big',S/'gamedata/fair-value-v12-model.json',S/'fair_value_model.py',S/'fair_value_store.py']}
 original_model=read(S/'gamedata/fair-value-v12-model.json');config=copy.deepcopy(original_model);config.update(revision='nostalgia-utility-ep-v13',previous_revision='fair-value-v12',currency_scale=original_model['currency_scale']*1000,ep_unit_multiplier=1000,identity_factor_bounds=[1.,1.5],valuation_score_kind='attribute_proxy_not_measured_playability')
 factors,evidence=utility_factors(original_model);config['identity_factors']=factors;config['utility_policy']=dict(method='leave-player-out nearest12 same-season same-role quote residual, adjusted for ability curve; max score gap5; at least2 independent seasons; shrink n/(n+6)',bounds=[1,1.5],scope='shared per native identity; not an executable gameplay buff or measured match rating',unknown_factor=1,source_prices='historical KR quotes, no synthetic labels')
 save(out/'model.json',config);save(out/'utility-evidence.json',dict(method=config['utility_policy'],observations={str(k):v for k,v in evidence.items()}))
 audit=read(W/'nostalgia-attribute-review/audit.json');spec=read(W/'nostalgic-season/roster-audit.json');source=Path(audit['source_backup']['path']);assert sha(source)==audit['source_backup']['sha256'];prior={r['spid']:r for r in audit['rows']}
 registry=read(S/'gamedata/custom_rosters.json');fields=model.fields(config);changes=[]
 dbpath=out/'fifadb.sqlite'
 with closing(sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)) as a,closing(sqlite3.connect(dbpath)) as b:a.backup(b)
 roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
 with closing(sqlite3.connect(dbpath,uri=True)) as db,closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as orig,db:
  db.row_factory=sqlite3.Row;orig.row_factory=sqlite3.Row
  for card in spec['cards']:
   sid=19000000+card['base_playerid'];before=dict(db.execute('select * from players where spid=?',(sid,)).fetchone());donor=dict(orig.execute('select * from players where spid=?',(card['template_spid'],)).fetchone())
   assert hashlib.sha256(json.dumps(donor,sort_keys=True,separators=(',',':')).encode()).hexdigest()==card['source_row_sha256']
   assert all(before[k]-donor[k]==prior[sid]['field_increases'][k] for k in fields),'Another legitimate attribute edit requires fresh audit'
   after=dict(before);after.update({k:donor[k] for k in fields});weights=config['role_weights'][roles[before['preferredposition1']]];base=sum(after[k]*w for k,w in weights.items())//sum(weights.values());after.update(overallrating=base,potential=max(base,donor['potential']))
   update=fields+['overallrating','potential'];db.execute('update players set '+','.join(k+'=?' for k in update)+' where spid=?',([after[k] for k in update]+[sid]))
   change=dict(spid=sid,name=card['name_zh'],source_spid=card['template_spid'],source_digest=card['source_row_sha256'],before=before,after=after,display_before=before['overallrating']+5,display_after=base+5)
   changes.append(change);registered=next(x for x in registry['cards'] if x['fo3_spid']==sid);registered['attribute_correction']=dict(revision=config['revision'],policy='restore all33 authentic template abilities; no reputation-driven OVR lift',source_spid=card['template_spid'],source_row_sha256=card['source_row_sha256'],changed_fields=[k for k in update if before[k]!=after[k]])
  db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok';db.execute('attach database ? as previous',((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',))
  for table, in db.execute("select name from main.sqlite_master where type='table'").fetchall():
   quoted='"'+table.replace('"','""')+'"';where=' where spid/1000000!=19' if table=='players' else ''
   assert not db.execute('select * from main.'+quoted+where+' except select * from previous.'+quoted+where+' limit 1').fetchone(),table
   assert not db.execute('select * from previous.'+quoted+where+' except select * from main.'+quoted+where+' limit 1').fetchone(),table
 save(out/'custom_rosters.json',registry)
 # Existing resource tools perform ordered member replacement; no old release
 # transaction launchers are imported, and no formal files are written here.
 tools=load(W/'value-diagnosis/manutd-attribute-correction/build.py','v13_resource_helpers');member=tools.MEMBER;decoded=bytes(tools.extract_fifadb.decrypt(tools.bigdir.read(C/'data/data_0.big',member)));assert b'SQLite format 3\0'+decoded[16:]==(S/'gamedata/fifadb.sqlite').read_bytes()
 shutil.copyfile(C/'data/data_0.big',out/'data_0.big');plain=dbpath.read_bytes();encoder=tools.Cipher(tools.Blowfish(tools.extract_fifadb.KEY),tools.modes.ECB()).encryptor();encrypted=tools.extract_fifadb.swap32(encoder.update(tools.extract_fifadb.swap32(decoded[:16]+plain[16:]))+encoder.finalize());tools.replace_member(out/'data_0.big',member,tools.refpack(encrypted),len(encrypted))
 layout=tools.load(S/'tools/check_data0_layout.py','v13_layout').inspect(out/'data_0.big',baseline=C/'data/data_0.big',changed_members={member},expected_count=len(tools.bigdir.entries(C/'data/data_0.big')));assert layout['status']=='PASS';save(out/'layout.json',layout)
 checker=tools.load(S/'tools/player_import/check.py','v13_player_check');certificate=checker.validate(S,C,database=dbpath,data0=out/'data_0.big',registry=out/'custom_rosters.json',full=True);save(out/'player-import-validation.json',certificate)
 catalogue=model.build_catalogue(dbpath,config);catalogue['expected_previous_revision']='fair-value-v12'
 with gzip.open(out/'catalogue.json.gz','wt',encoding='utf8') as f:json.dump(catalogue,f,ensure_ascii=False,separators=(',',':'))
 assert baseline=={p:sha(p) for p in baseline},'Official inputs changed during build; refresh'
 save(out/'changes.json',changes);selected=[]
 for change in changes:
  if change['name'] in ['贝尔','博格巴','费莱尼','罗霍']:
   e=model.explain(change['after'],config);selected.append(dict(name=change['name'],spid=change['spid'],ability_before=change['display_before'],ability_after=change['display_after'],price_ep=e['fair_price_ep'],historical_preference_factor=e['identity_factor'],attribute_score=e['effective_score']))
 report=dict(status='PREPARED_FULL_IMPORT_PASS',output=str(out),baseline=baseline,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()},attributes_restored=88,all_other_rows_and_tables_exact=True,all_identity_models_traits_stars_and_positions_preserved=True,catalogue_rows=len(catalogue['rows']),model_sha256=catalogue['model_sha256'],profile_sha256=catalogue['profile_sha256'],ep_unit_multiplier=1000,selected=selected,layout=layout['status'],player_import=certificate['status'],formal_activated=False)
 save(out/'report.json',report);save(P/'latest-build.json',dict(path=str(out),status=report['status']));print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
