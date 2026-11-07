"""Persistent market prices. Neural estimates are imported once by the installer.

There is deliberately no model import, attribute lookup, or automatic reseeding
in the runtime. Committed trade-price events are replayable and idempotent.
"""
from pathlib import Path
from contextlib import closing
import gzip,hashlib,json,math,sqlite3,threading,time

MAX_PRICE=5_600_000_000_000_000

class MarketPriceStore:
 def __init__(self,path):
  self.path=Path(path).resolve();self._lock=threading.RLock();self.last_error=None
  self._db=sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,check_same_thread=False,timeout=30)
  self.meta=dict(self._db.execute('select key,value from metadata'))
  if self.meta.get('schema')!='1':raise ValueError('Unsupported market price database')
  self._prices={int(s):float(p) for s,p in self._db.execute('select spid,basis_price from prices')}
  self._initial={int(s):int(p) for s,p in self._db.execute('select spid,initial_price from seeds')}
  self._events={r[0] for r in self._db.execute('select event_id from price_events')}
  if self._prices.keys()!=self._initial.keys():raise ValueError('Incomplete market-price coverage')
  if not all(math.isfinite(p) and 1<=p<=MAX_PRICE for p in self._prices.values()):raise ValueError('Invalid current market price')
  self.fair=None
  if self.meta.get('fair_revision'):
   from fair_value_store import FairLayer
   self.fair=FairLayer(self)
 def basis(self,spid):
  if self.fair is not None:return self.fair.reference(spid)
  with self._lock:return self._prices.get(int(spid),0.)
 def current(self,spid):
  value=self.basis(spid);return max(1,round(value)) if value>0 else 0
 def initial(self,spid):return self._initial.get(int(spid),0)
 def applied(self,event_id):return event_id in self._events
 def flush(self,events):
  if self.fair is not None:return self.fair.flush(events)
  if not events:return 0
  changed={};new_ids=[]
  with self._lock:
   try:
    with self._db:
     for event in events:
      key=event['event_id']
      if key in self._events or key in new_ids:continue
      spid=int(event['spid']);before=float(event['before']);after=float(event['after']);actual=changed.get(spid,self._prices.get(spid,0.))
      if spid not in self._prices or not all(math.isfinite(v) for v in (before,after)) or not 1<=after<=MAX_PRICE:raise ValueError('Invalid market price event')
      if actual!=before:raise RuntimeError('Market price cursor changed; refusing to overwrite newer price')
      if event['reason'] not in ('funded_trade_volume','legacy_market_movement'):raise ValueError('Unsupported price movement source')
      self._db.execute('insert into price_events values(?,?,?,?,?,?,?)',(key,spid,before,after,float(event['at']),event['reason'],json.dumps(event.get('evidence',{}),separators=(',',':'))))
      self._db.execute('update prices set basis_price=?,current_price=?,updated_at=?,last_event=? where spid=?',(after,max(1,round(after)),float(event['at']),key,spid))
      changed[spid]=after;new_ids.append(key)
    self._prices.update(changed);self._events.update(new_ids);self.last_error=None
   except Exception as exc:self.last_error=f'{type(exc).__name__}: {exc}';raise
  return len(new_ids)
 def status(self):
  result=dict(mode='one_time_model_seed_then_market_trades',runtime_model_loaded=False,price_region=self.meta['price_region'],seed_model_sha256=self.meta['model_sha256'],seed_revision=self.meta['seed_revision'],active_valuation_revision=self.meta.get('valuation_revision'),active_valuation_model_sha256=self.meta.get('valuation_model_sha256'),priced_cards=len(self._prices),price_events=len(self._events),last_error=self.last_error,database=str(self.path))
  if self.fair is not None:result.update(mode='bounded_same_player_curve',runtime_model_loaded=True,active_valuation_revision=self.meta['fair_revision'],active_valuation_model_sha256=self.meta['fair_model_sha256'],attribute_profile_sha256=self.meta['fair_profile_sha256'],market_factor_scope='same player across all seasons',market_factor_bounds=self.fair.model['market_factor_bounds'],profile_error=self.fair.last_profile_error)
  return result
 def close(self):self._db.close()

def initialize(path,seed_path,revision):
 """Explicit install-only operation. Existing prices are never reset."""
 path=Path(path)
 if path.exists():
  verify_seed(path,seed_path);return False
 with gzip.open(seed_path,'rt',encoding='utf8') as f:seed=json.load(f)
 rows=seed['rows'];assert seed['schema']==1 and seed['price_region']=='kr' and all(type(p) is int and 1<=p<=MAX_PRICE for _,p in rows)
 assert hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()==seed['seed_prices_sha256']
 with closing(sqlite3.connect(path)) as db,db:
  db.executescript('''
   create table metadata(key text primary key,value text not null);
   create table seeds(spid integer primary key,initial_price integer not null,model_sha256 text not null,initialized_at real not null);
   create table prices(spid integer primary key references seeds(spid),basis_price real not null,current_price integer not null,updated_at real not null,last_event text);
   create table price_events(event_id text primary key,spid integer not null,before_price real not null,after_price real not null,at real not null,reason text not null,evidence text not null);
  ''')
  stamp=time.time();meta=dict(schema='1',price_region='kr',model_sha256=seed['model_sha256'],seed_revision=revision,denomination_divisor='1000',seed_prices_sha256=seed['seed_prices_sha256'])
  db.executemany('insert into metadata values(?,?)',meta.items())
  db.executemany('insert into seeds values(?,?,?,?)',[(s,p,seed['model_sha256'],stamp) for s,p in rows])
  db.executemany('insert into prices values(?,?,?,?,null)',[(s,float(p),p,stamp) for s,p in rows])
 verify_seed(path,seed_path);return True

def verify_seed(path,seed_path):
 """Validate immutable initial rows while allowing all legitimate current moves."""
 with gzip.open(seed_path,'rt',encoding='utf8') as f:seed=json.load(f)
 with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok','Market price DB corrupt'
  meta=dict(db.execute('select key,value from metadata'));initial={s:(p,m) for s,p,m in db.execute('select spid,initial_price,model_sha256 from seeds')}
  assert meta['schema']=='1' and meta['model_sha256']==seed['model_sha256']
  for spid,price in seed['rows']:assert initial.get(spid)==(price,seed['model_sha256']),f'Initial seed changed: {spid}'
  assert db.execute('select count(*) from prices where basis_price<1 or basis_price>? or current_price<1',(MAX_PRICE,)).fetchone()[0]==0
 return dict(seed_rows=len(seed['rows']),model_sha256=seed['model_sha256'])


def calibration_packet(packet_path):
 with gzip.open(packet_path,'rt',encoding='utf8') as f:packet=json.load(f)
 rows=packet['rows'];seen=set()
 if packet.get('schema')!=1 or not packet.get('revision') or len(packet.get('model_sha256',''))!=64:raise ValueError('Invalid calibration identity')
 for sid,price in rows:
  if type(sid) is not int or sid in seen or type(price) is not int or not 1<=price<=MAX_PRICE:raise ValueError('Invalid calibration prices')
  seen.add(sid)
 if hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()!=packet['prices_sha256']:raise ValueError('Calibration digest differs')
 return packet


def apply_calibration(database,packet_path):
 """Explicit maintenance transaction, never called during normal startup."""
 packet=calibration_packet(packet_path);revision=packet['revision'];stamp=time.time()
 with closing(sqlite3.connect(database,timeout=30)) as db:
  db.execute('begin immediate')
  try:
   meta=dict(db.execute('select key,value from metadata'))
   if meta.get('valuation_revision')==revision:
    if meta.get('valuation_model_sha256')!=packet['model_sha256'] or meta.get('valuation_prices_sha256')!=packet['prices_sha256']:raise ValueError('Calibration revision reused')
    db.rollback();verify_calibration(database,packet_path);return dict(applied=False,rows=len(packet['rows']))
   before=dict(db.execute('select spid,basis_price from prices'))
   if set(before)!=set(sid for sid,_ in packet['rows']):raise ValueError('Calibration coverage differs from current market')
   for sid,price in packet['rows']:
    event='valuation:'+revision+':'+str(sid)
    evidence=json.dumps(dict(model_sha256=packet['model_sha256'],previous_valuation=meta.get('valuation_revision',meta['seed_revision'])),separators=(',',':'))
    db.execute('insert into price_events values(?,?,?,?,?,?,?)',(event,sid,before[sid],float(price),stamp,'model_recalibration',evidence))
    db.execute('update prices set basis_price=?,current_price=?,updated_at=?,last_event=? where spid=?',(float(price),price,stamp,event,sid))
   for k,v in dict(valuation_revision=revision,valuation_model_sha256=packet['model_sha256'],valuation_prices_sha256=packet['prices_sha256']).items():db.execute('insert or replace into metadata values(?,?)',(k,v))
   db.commit()
  except BaseException:db.rollback();raise
 verify_calibration(database,packet_path)
 return dict(applied=True,rows=len(packet['rows']),revision=revision,model_sha256=packet['model_sha256'])


def verify_calibration(database,packet_path):
 """Check immutable calibration events, allowing later funded-trade prices."""
 packet=calibration_packet(packet_path);revision=packet['revision']
 with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
  meta=dict(db.execute('select key,value from metadata'))
  if meta.get('valuation_revision')!=revision or meta.get('valuation_model_sha256')!=packet['model_sha256'] or meta.get('valuation_prices_sha256')!=packet['prices_sha256']:raise ValueError('Active valuation differs')
  events={sid:(after,reason) for sid,after,reason in db.execute('select spid,after_price,reason from price_events where event_id like ?',('valuation:'+revision+':%',))}
  if events!={sid:(float(price),'model_recalibration') for sid,price in packet['rows']}:raise ValueError('Calibration events missing or changed')
 return dict(revision=revision,model_sha256=packet['model_sha256'],rows=len(events),runtime_model_loaded=False)


def migrate_quote_state(state,packet):
 """Change only quote bases; all card assets and existing offers survive."""
 import copy
 result=copy.deepcopy(state);market=result.setdefault('market_simulation',{})
 if market.get('valuation_revision')==packet['revision']:return result
 prices=dict(packet['rows'])
 for sid,quote in market.get('quotes',{}).items():
  if int(sid) not in prices:raise ValueError('Unknown existing quote')
  archive=dict(revision=packet['revision'],before_basis=quote.get('basis_price'),pending=quote.get('pending',[]))
  quote.setdefault('valuation_history',[]).append(archive)
  quote['basis_price']=float(prices[int(sid)]);quote['pending']=[]
 market['valuation_revision']=packet['revision']
 return result
