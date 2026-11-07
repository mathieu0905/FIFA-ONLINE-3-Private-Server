"""Read the current official runtime sources against a detached market snapshot."""
from pathlib import Path
import os,sys,sqlite3,tempfile
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795');sys.path.insert(0,str(S));sys.dont_write_bytecode=True
os.environ.update(FO3_GAME=str(C),FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and args[2]&0x643:
  p=Path(os.fsdecode(args[0])).resolve()
  if p.is_relative_to(S) or p.is_relative_to(C):raise RuntimeError('Official write blocked by regression host')
sys.addaudithook(guard)
import market_price_store
temp=tempfile.TemporaryDirectory(dir=R,prefix='market-snapshot-');db=Path(temp.name)/'prices.sqlite'
src=sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(db);src.backup(dst);src.close();dst.close()
init=market_price_store.MarketPriceStore.__init__;flush=market_price_store.MarketPriceStore.flush
market_price_store.MarketPriceStore.__init__=lambda self,path:init(self,db)
market_price_store.MarketPriceStore.flush=lambda self,events:0
import http_config as h
market_price_store.MarketPriceStore.__init__=init;market_price_store.MarketPriceStore.flush=flush
def close():h.market_engine.exchange.price_store._db.close();temp.cleanup()
