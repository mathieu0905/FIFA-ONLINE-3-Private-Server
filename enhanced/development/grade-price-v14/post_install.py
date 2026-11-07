from pathlib import Path
from contextlib import closing
import json,sqlite3,hashlib,urllib.request,importlib.util,sys,time
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True
def read(p):return json.loads(Path(p).read_text('utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(path):
 with urllib.request.urlopen('http://127.0.0.1:8088/api/'+path,timeout=10) as f:return json.load(f)
def main():
 report=read(P/'installed-handback.json');assert report['status']=='INSTALLED_AND_LIVE_PASS';backup=Path(report['backup'])
 assert report['asset_projection_equal'] and report['shop_equal'] and report['plus1_prices_unchanged']
 with closing(sqlite3.connect(S/'gamedata/npc-market-prices.sqlite')) as db,closing(sqlite3.connect(backup/'market-before-v14.sqlite')) as old:
  before=dict(old.execute('select spid,current_price from prices'));now=dict(db.execute('select spid,current_price from prices'));assert before==now
  assert dict(old.execute('select * from metadata'))['fair_revision']=='nostalgia-utility-ep-v13'
  assert dict(db.execute('select * from metadata'))['fair_revision']=='base-times-enhancement-v14'
  assert db.execute('select * from seeds order by spid').fetchall()==old.execute('select * from seeds order by spid').fetchall()
  assert db.execute('select * from player_market_factors order by playerid').fetchall()==old.execute('select * from player_market_factors order by playerid').fetchall()
  oldevents={r[0]:r for r in old.execute('select * from price_events')};new={r[0]:r for r in db.execute('select * from price_events')};assert all(new[k]==v for k,v in oldevents.items())
 rates=read(P/'prepared.json')['baseline']['D:\\FO3ID\\server\\gamedata\\enhancement_rates.json'];assert sha(S/'gamedata/enhancement_rates.json')==rates
 sample=[]
 for sid in [84037576,30037576,19173731,19195864,19176944,19201862]:
  for grade in [1,5,10,15,20]:
   row=api(f'market_price_store?spid={sid}&grade={grade}');assert row['active_valuation_revision']=='base-times-enhancement-v14';assert row['current_price']==before[sid]
   assert row['value']==round(row['current_price']*read(P/'prepared.json')['multipliers'][grade]);sample.append(dict(spid=sid,grade=grade,value=row['value']))
 status=api('market_status');hot=api('hot_update_status');enh=api('enhancement')
 assert status['background']['running'] and status['background']['errors']==0 and status['background']['last_error'] is None
 assert hot['watcher_running'] and hot['error'] is None and hot['revision']==report['hot_update_status']['revision']
 assert enh['revision']==rates
 assert sha(Path('D:/FO3ID/32795/data/ui/TeamManagementPlayerEnhancementTabPage.big'))=='cd8f7b2d8dd747eb617b6b64b93631602a99ad77bdead962403b690fbbdde314'
 assert sha(Path('D:/FO3ID/32795/data/ui/TeamManagementPlayerEnhancingPopupScreen.big'))=='1d2f611d26cde0a07c0d71200aaa877c5c1a36710622e8547d828ff7eebb8815'
 output=dict(status='PASS',all_plus1_rows_unchanged=len(before),seed_and_earned_factors_preserved=True,old_events_preserved=len(oldevents),live_price_probes=sample,background=status['background'],hot=hot,enhancement_rates_revision=enh['revision'],native_gui_or_match_verified=False,enhancement_ui_hashes_preserved=True,quote_receipt=report['system_quote_receipt'])
 (P/'post-install-verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(output,ensure_ascii=False))
if __name__=='__main__':main()
