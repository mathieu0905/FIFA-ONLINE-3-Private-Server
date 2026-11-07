def install_catalogue(database,catalogue_path,model_path,source_database):
 """Explicit atomic generation upgrade; archive old fair data, preserve trade factors."""
 model=json.loads(Path(model_path).read_text('utf8'));cat=read_catalogue(catalogue_path);proof=verify_profiles(source_database,cat,model);revision=cat['revision'];stamp=time.time()
 with closing(sqlite3.connect(database,timeout=30)) as db:
  db.execute('begin immediate')
  try:
   meta=dict(db.execute('select key,value from metadata'))
   if meta.get('fair_revision')==revision:
    if meta.get('fair_model_sha256')!=cat['model_sha256'] or meta.get('fair_profile_sha256')!=cat['profile_sha256']:raise ValueError('Generation revision reused')
    db.rollback();verify_installed(database,catalogue_path,model_path,source_database);return dict(applied=False,**proof)
   if meta.get('fair_revision')!=cat['expected_previous_revision']:raise ValueError('Active fair generation changed; rebase required')
   before=dict(db.execute('select spid,basis_price from prices'));oldvalues=db.execute('select * from fair_values').fetchall();factors=dict(db.execute('select playerid,factor from player_market_factors'))
   if set(before)!={r['spid'] for r in cat['rows']}:raise ValueError('Generation coverage differs')
   db.execute('create table if not exists fair_generation_history(revision text primary key,model_sha256 text not null,profile_sha256 text not null,model_json text not null)')
   db.execute('create table if not exists fair_value_history(revision text not null,spid integer not null,playerid integer not null,economic_value real not null,strict_floor integer not null,effective_score real not null,profile_sha256 text not null,primary key(revision,spid))')
   db.execute('insert into fair_generation_history values(?,?,?,?)',(meta['fair_revision'],meta['fair_model_sha256'],meta['fair_profile_sha256'],meta['fair_model_json']))
   db.executemany('insert into fair_value_history values(?,?,?,?,?,?,?)',[(meta['fair_revision'],*r) for r in oldvalues])
   db.execute('delete from fair_values')
   for r in cat['rows']:
    sid=r['spid'];pid=r['playerid'];factor=factors.get(pid,1.);price=round(r['economic_value']*factor)+r['strict_floor_ep'];event='fair-calibration:'+revision+':'+str(sid)
    db.execute('insert into fair_values values(?,?,?,?,?,?)',(sid,pid,r['economic_value'],r['strict_floor_ep'],r['effective_score'],r['profile_sha256']))
    db.execute('insert or ignore into player_market_factors values(?,1.,?,?)',(pid,stamp,event))
    db.execute('insert into price_events values(?,?,?,?,?,?,?)',(event,sid,before[sid],float(price),stamp,'fair_value_recalibration',json.dumps(dict(model_sha256=cat['model_sha256'],profile_sha256=r['profile_sha256'],previous_revision=meta['fair_revision'],preserved_market_factor=factor))))
    db.execute('update prices set basis_price=?,current_price=?,updated_at=?,last_event=? where spid=?',(float(price),price,stamp,event,sid))
   updates=dict(fair_revision=revision,fair_model_sha256=cat['model_sha256'],fair_profile_sha256=cat['profile_sha256'],fair_model_json=json.dumps(model,separators=(',',':')),fair_source_database=str(Path(source_database).resolve()))
   db.executemany('insert or replace into metadata values(?,?)',updates.items());db.commit()
  except BaseException:db.rollback();raise
 return dict(applied=True,**proof)


def verify_installed(database,catalogue_path,model_path,source_database):
 model=json.loads(Path(model_path).read_text('utf8'));cat=read_catalogue(catalogue_path)
 if hashlib.sha256(canonical(model)).hexdigest()!=cat['model_sha256']:raise ValueError('Catalogue/model digest differs')
 with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
  meta=dict(db.execute('select key,value from metadata'));expected={r['spid']:(r['playerid'],r['economic_value'],r['strict_floor_ep'],r['effective_score'],r['profile_sha256']) for r in cat['rows']}
  if meta.get('fair_revision')!=cat['revision']:
   generation=db.execute('select model_sha256,profile_sha256,model_json from fair_generation_history where revision=?',(cat['revision'],)).fetchone()
   if generation is None or generation[:2]!=(cat['model_sha256'],cat['profile_sha256']) or hashlib.sha256(canonical(json.loads(generation[2]))).hexdigest()!=cat['model_sha256']:raise ValueError('Historical fair generation identity differs')
   actual={r[0]:tuple(r[1:]) for r in db.execute('select spid,playerid,economic_value,strict_floor,effective_score,profile_sha256 from fair_value_history where revision=?',(cat['revision'],))}
   if actual!=expected:raise ValueError('Archived historical fair values differ')
   return dict(status='FAIR_VALUE_HISTORICAL_GENERATION_PASS',rows=len(actual),revision=cat['revision'],profile_sha256=cat['profile_sha256'])
  if meta['fair_model_sha256']!=cat['model_sha256'] or meta['fair_profile_sha256']!=cat['profile_sha256']:raise ValueError('Wrong active generation')
  actual={r[0]:tuple(r[1:]) for r in db.execute('select * from fair_values')}
  if actual!=expected:raise ValueError('Current fair values changed')
  factors=dict(db.execute('select playerid,factor from player_market_factors'));lo,hi=model['market_factor_bounds']
  if set(factors)!={r['playerid'] for r in cat['rows']} or any(not math.isfinite(f) or not lo<=f<=hi for f in factors.values()):raise ValueError('Invalid common-player factor')
  for sid,price in db.execute('select spid,current_price from prices'):
   pid,economic,floor,*_=actual[sid]
   if price!=round(economic*factors[pid])+floor:raise ValueError('Current price differs from shared factor')
 return verify_profiles(source_database,cat,model)


def migrate_state(state,revision):
 result=copy.deepcopy(state);m=result.setdefault('market_simulation',{})
 if m.get('fair_revision')==revision:return result
 previous=m.get('fair_revision');m['fair_revision']=revision
 for q in m.get('identity_quotes',{}).values():
  if q.get('pending'):q.setdefault('historical_price_samples',[]).append(dict(revision=previous,pending=q['pending']))
  q['pending']=[]
 m.setdefault('fair_revision_history',[]).append(dict(before=previous,after=revision))
 return result
