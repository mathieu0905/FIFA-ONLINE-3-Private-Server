"""Load the actual host without listeners, with new configs and a temporary market DB."""
from pathlib import Path
import importlib.util,json,os,sqlite3,sys,tempfile
from unittest.mock import patch
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path[:0]=[str(S),str(R)];os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi');sys.argv=[sys.argv[0]]
def guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
  p=Path(os.fsdecode(args[0])).resolve()
  if p.is_relative_to(S) or p.is_relative_to(C):raise RuntimeError('Test attempted formal write: '+str(p))
sys.addaudithook(guard)
import market_price_store
TEMP=tempfile.TemporaryDirectory(dir=R,prefix='market-test-');market=Path(TEMP.name)/'prices.sqlite'
src=sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True);dst=sqlite3.connect(market);src.backup(dst);src.close();dst.close()
original_init=market_price_store.MarketPriceStore.__init__;original_flush=market_price_store.MarketPriceStore.flush
market_price_store.MarketPriceStore.__init__=lambda self,path:original_init(self,market)
market_price_store.MarketPriceStore.flush=lambda self,events:0
old_text=Path.read_text;old_bytes=Path.read_bytes;old_exists=Path.is_file
config={str((S/'gamedata'/n).resolve()).casefold():R/n for n in ['club_season_products.json','all_item_icon_manifest.json']}
images={str((C/'_cache/games/fo3id/externalAssets/shop'/p.name).resolve()).casefold():p for p in (R/'icons').glob('*.png')}
def text(path,*a,**k):return old_text(config.get(str(path.resolve()).casefold(),path),*a,**k)
def data(path):return old_bytes(images.get(str(path.resolve()).casefold(),path))
def exists(path):return old_exists(images.get(str(path.resolve()).casefold(),path))
try:
 with patch.object(Path,'read_text',text),patch.object(Path,'read_bytes',data),patch.object(Path,'is_file',exists):
  import http_config as h
finally:
 market_price_store.MarketPriceStore.__init__=original_init;market_price_store.MarketPriceStore.flush=original_flush
def close():h.market_engine.exchange.price_store._db.close();TEMP.cleanup()
