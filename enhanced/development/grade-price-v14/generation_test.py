from pathlib import Path
from contextlib import closing
import importlib.util,sys,sqlite3,tempfile,json,hashlib
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 helper=load(P/'fair_value_store.py','v14_test_helper')
 with tempfile.TemporaryDirectory(prefix='fo3-v14-') as folder:
  path=Path(folder)/'market.sqlite'
  with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').resolve().as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(path)) as dst:src.backup(dst)
  with closing(sqlite3.connect(path)) as db:
   before={t:db.execute('select * from '+t+' order by 1').fetchall() for t in ['prices','seeds','player_market_factors','price_events']}
  proof=helper.install_catalogue(path,P/'catalogue.json.gz',P/'model.json',S/'gamedata/fifadb.sqlite');assert proof['applied']
  for version in [12,13,14]:
   cat=P/'catalogue.json.gz' if version==14 else S/f'gamedata/fair-value-v{version}-catalogue.json.gz'
   cfg=P/'model.json' if version==14 else S/f'gamedata/fair-value-v{version}-model.json'
   helper.verify_installed(path,cat,cfg,S/'gamedata/fifadb.sqlite')
  assert not helper.install_catalogue(path,P/'catalogue.json.gz',P/'model.json',S/'gamedata/fifadb.sqlite')['applied']
  with closing(sqlite3.connect(path)) as db:
   for t in ['seeds','player_market_factors']:assert db.execute('select * from '+t+' order by 1').fetchall()==before[t]
   assert dict(db.execute('select spid,current_price from prices'))=={r[0]:r[2] for r in before['prices']}
   oldevents={r[0]:r for r in before['price_events']};new={r[0]:r for r in db.execute('select * from price_events')};assert all(new[k]==v for k,v in oldevents.items())
   db.execute("update metadata set value=? where key='fair_source_database'",(str(S/'gamedata/fifadb.sqlite'),));db.commit()
  # Exercise actual public runtime store/reference with new helper, not formula only.
  sys.modules['fair_value_store']=helper;storemod=load(S/'market_price_store.py','v14_store_test');store=storemod.MarketPriceStore(path)
  boost=load(Path('D:/fifaol3/value-redesign-v12/effective_boosts.py'),'v14_boost').grade_boosts()
  state={'market_simulation':{'fair_revision':'base-times-enhancement-v14'}}
  try:
   base=store.fair.reference(84037576,state,1,boost);peak=store.fair.reference(84037576,state,20,boost);assert peak==base*5000
   for row in before['prices']:
    sid=row[0];b=store.fair.reference(sid,state,1,boost);assert b==row[2]
    assert store.fair.reference(sid,state,20,boost)==b*5000
  finally:store.close()
 report=dict(status='PASS',generations_verified=[12,13,14],all_base_prices_unchanged=True,seeds_events_and_factors_preserved=True,actual_runtime_reference=True,im_ronaldo_grade1=base,im_ronaldo_grade20=peak,quote_source_sha256=hashlib.sha256((P/'system_quotes.py').read_bytes()).hexdigest())
 (P/'generation-regression.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report))
 prepared=json.loads((P/'prepared.json').read_text('utf8'))
 for n in prepared['outputs']:prepared['outputs'][n]=hashlib.sha256((P/n).read_bytes()).hexdigest()
 (P/'prepared.json').write_text(json.dumps(prepared,indent=2)+'\n','utf8')
if __name__=='__main__':main()
