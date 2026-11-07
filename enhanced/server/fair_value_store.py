"""One common market factor per identity, with append-only trade receipts."""
from pathlib import Path
from contextlib import closing
import copy,gzip,hashlib,json,math,sqlite3,time
from fair_value_model import canonical,profile_digest,catalogue_rows,verified_catalogue_rows,verify_profiles,economic_curve

def read_catalogue(path):
 with gzip.open(path,'rt',encoding='utf8') as f:return json.load(f)

def validate_enhancement_curve(model,values):
 curve=model.get('enhancement_price_curve')
 if curve is None:return
 multipliers=curve['multipliers']
 if len(multipliers)!=21 or multipliers[:2]!=[0.,1.] or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in multipliers) or any(a>=b for a,b in zip(multipliers,multipliers[1:])):raise ValueError('Invalid enhancement price curve')
 hi=model['market_factor_bounds'][1]
 if max(round(r[1]*hi)+r[2] for r in values.values())*multipliers[-1]>(2**53-1)//3:raise ValueError('Enhancement price exceeds native reference range')

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
  validate_enhancement_curve(model,actual)
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


class FairLayer:
 def __init__(self,store):
  self.store=store;self.revision=store.meta['fair_revision'];self.model=json.loads(store.meta['fair_model_json'])
  self.values={r[0]:tuple(r[1:]) for r in store._db.execute('select spid,playerid,economic_value,strict_floor,effective_score,profile_sha256 from fair_values')}
  validate_enhancement_curve(self.model,self.values)
  self.factors=dict(store._db.execute('select playerid,factor from player_market_factors'));self.groups={}
  for sid,(pid,*_) in self.values.items():self.groups.setdefault(pid,[]).append(sid)
  if self.values.keys()!=store._prices.keys():raise ValueError('Fair price coverage changed; publish new profiles and prices together')
  self.source=Path(store.meta['fair_source_database']);self.source_stamp=None;self.last_profile_error=None;self.ensure_profiles()
  for sid in self.values:
   if store._prices[sid]!=float(self.value(sid)):raise ValueError('Fair price cache differs from common identity factor')
 def ensure_profiles(self):
  stat=self.source.stat();stamp=(stat.st_mtime_ns,stat.st_size)
  if stamp==self.source_stamp:return
  rows=verified_catalogue_rows(self.source,self.model)
  if profile_digest(rows,self.model)!=self.store.meta['fair_profile_sha256']:
   self.last_profile_error='PLAYER_ATTRIBUTES_CHANGED: publish new catalogue with the roster';raise ValueError(self.last_profile_error)
  self.source_stamp=stamp;self.last_profile_error=None
 def value(self,sid,factor=None):
  sid=int(sid)
  if sid not in self.values:return 0
  pid,economic,floor,*_=self.values[sid];f=self.factors[pid] if factor is None else factor
  lo,hi=self.model['market_factor_bounds']
  if not math.isfinite(f) or not lo<=f<=hi:raise ValueError('Invalid common-player market factor')
  return round(economic*f)+floor
 def reference(self,sid,state=None,grade=1,grade_boost=None):
  self.ensure_profiles();sid=int(sid)
  if sid not in self.values:return 0
  pid=self.values[sid][0];factor=self.factors[pid]
  if state is not None:
   market=state.get('market_simulation',{})
   if market.get('fair_revision')!=self.revision:raise ValueError('State/valuation generation differs')
   factor=market.get('identity_quotes',{}).get(str(pid),{}).get('factor',factor)
  if grade==1:return self.value(sid,factor)
  if type(grade) is not int or grade_boost is None or not 0<=grade<len(grade_boost):raise ValueError('Invalid enhancement grade')
  if grade==0:return 0
  curve=self.model.get('enhancement_price_curve')
  if curve is not None:return round(self.value(sid,factor)*curve['multipliers'][grade])
  pid,economic,floor,score,_=self.values[sid];delta=grade_boost[grade]-self.model['grade1_boost']
  # The single-card price follows playable strength. Manufacturing expected
  # cost remains a diagnostic, never an exponential/capped price multiplier.
  identity=economic/economic_curve(score,self.model)
  return round(economic_curve(score+delta,self.model)*identity*factor)+floor+33*delta
 def prepare_state(self,state):
  m=state['market_simulation']
  if m.get('fair_revision') is None:
   if m.get('price_events'):raise ValueError('Old price events must be replayed before fair migration')
   m.update(fair_revision=self.revision,identity_quotes={})
  if m['fair_revision']!=self.revision:raise ValueError('Explicit fair state migration required')
  m.setdefault('identity_quotes',{})
 def stage_trade(self,state,entry,stamp):
  self.ensure_profiles();sid=int(entry['spid']);pid=self.values[sid][0];m=state['market_simulation']
  if m.get('fair_revision')!=self.revision:raise ValueError('State/valuation generation differs')
  day=int((stamp+7*3600)//86400)
  quote=m.setdefault('identity_quotes',{}).setdefault(str(pid),dict(factor=self.factors[pid],day=day,movement=0.,pending=[]))
  if day>quote['day']:quote.update(day=day,movement=0.)
  quote['pending']=(quote['pending']+[dict(id=entry['id'],spid=sid,at=stamp,ratio=entry['ratio'],price=entry['price'],grade=entry['grade'])])[-20:]
  pending=quote['pending']
  if len(pending)<3 or max(x['at'] for x in pending)-min(x['at'] for x in pending)<1800:return
  target=sorted(x['ratio'] for x in pending)[len(pending)//2];delta=max(-math.log(1.005),min(math.log(1.005),math.log(max(1e-12,target))*.1))
  budget=max(0.,math.log(1.02)-quote['movement']);delta=max(-budget,min(budget,delta));before=quote['factor'];lo,hi=self.model['market_factor_bounds'];after=max(lo,min(hi,before*math.exp(delta)))
  if before!=after:
   m.setdefault('price_events',[]).append(dict(event_id='trade-price:'+str(entry['id']),spid=sid,before=float(self.value(sid,before)),after=float(self.value(sid,after)),at=stamp,reason='funded_trade_volume',fair_revision=self.revision,playerid=pid,factor_before=before,factor_after=after,evidence=dict(sales=copy.deepcopy(pending),median_ratio=target)))
  quote.update(factor=after,movement=quote['movement']+abs(math.log(after/before)),pending=[])
 def flush(self,events):
  if not events:return 0
  self.ensure_profiles();store=self.store;factors={};changed={};ids=[];lo,hi=self.model['market_factor_bounds']
  with store._lock:
   try:
    with store._db:
     for e in events:
      if e['event_id'] in store._events or e['event_id'] in ids:continue
      sid=int(e['spid']);pid=self.values[sid][0];before=factors.get(pid,self.factors[pid]);after=e.get('factor_after')
      if e.get('fair_revision')!=self.revision or e.get('playerid')!=pid or e.get('factor_before')!=before or not isinstance(after,(int,float)) or not math.isfinite(after) or not lo<=after<=hi:raise ValueError('Wrong or stale player factor event')
      if abs(math.log(after/before))>math.log(1.005)+1e-12:raise ValueError('Per-trade player factor step exceeds limit')
      if e['reason']!='funded_trade_volume' or e['before']!=float(self.value(sid,before)) or e['after']!=float(self.value(sid,after)):raise ValueError('Fair event amounts differ')
      if store._db.execute('update player_market_factors set factor=?,updated_at=?,last_event=? where playerid=? and factor=?',(after,e['at'],e['event_id'],pid,before)).rowcount!=1:raise RuntimeError('Player factor CAS failed')
      for linked in self.groups[pid]:
       key=e['event_id'] if linked==sid else e['event_id']+':linked:'+str(linked);old=float(self.value(linked,before));new=float(self.value(linked,after))
       if changed.get(linked,store._prices[linked])!=old:raise RuntimeError('Price cursor differs from player factor')
       evidence=dict(e.get('evidence',{}),playerid=pid,factor_before=before,factor_after=after,fair_revision=self.revision,source_event=e['event_id'])
       store._db.execute('insert into price_events values(?,?,?,?,?,?,?)',(key,linked,old,new,e['at'],'funded_trade_volume' if linked==sid else 'shared_player_market_factor',json.dumps(evidence,separators=(',',':'))))
       store._db.execute('update prices set basis_price=?,current_price=?,updated_at=?,last_event=? where spid=?',(new,int(new),e['at'],key,linked));changed[linked]=new;ids.append(key)
      factors[pid]=after
    self.factors.update(factors);store._prices.update(changed);store._events.update(ids);store.last_error=None
   except Exception as exc:store.last_error=f'{type(exc).__name__}: {exc}';raise
  return len(ids)
