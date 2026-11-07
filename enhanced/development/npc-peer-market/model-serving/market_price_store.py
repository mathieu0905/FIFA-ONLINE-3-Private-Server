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
 def basis(self,spid):
  with self._lock:return self._prices.get(int(spid),0.)
 def current(self,spid):
  value=self.basis(spid);return max(1,round(value)) if value>0 else 0
 def initial(self,spid):return self._initial.get(int(spid),0)
 def applied(self,event_id):return event_id in self._events
 def flush(self,events):
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
  return dict(mode='one_time_model_seed_then_market_trades',runtime_model_loaded=False,price_region=self.meta['price_region'],seed_model_sha256=self.meta['model_sha256'],seed_revision=self.meta['seed_revision'],priced_cards=len(self._prices),price_events=len(self._events),last_error=self.last_error,database=str(self.path))
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
