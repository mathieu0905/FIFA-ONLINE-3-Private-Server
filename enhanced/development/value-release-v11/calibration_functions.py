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
