"""Read-only formal data and real API check, including all enhancement grades."""
from pathlib import Path
from contextlib import closing
import datetime,gzip,json,math,sqlite3,urllib.request
from fair_value_model import economic_curve
from effective_boosts import grade_boosts
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
def api(suffix):
 with urllib.request.urlopen('http://127.0.0.1:8088/api/'+suffix,timeout=15) as response:return json.load(response)
def main():
 handback=json.loads((P/'installed-handback.json').read_text('utf8'));config=json.loads((S/'gamedata/fair-value-v12-model.json').read_text('utf8'))
 with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  values={r[0]:tuple(r[1:]) for r in db.execute('select * from fair_values')};factors=dict(db.execute('select playerid,factor from player_market_factors'))
  db.execute('attach database ? as historical',((Path(handback['backup'])/'market-before-fair.sqlite').as_uri()+'?mode=ro',))
  assert not db.execute('select * from historical.seeds except select * from main.seeds limit 1').fetchone()
  assert not db.execute('select * from historical.price_events except select * from main.price_events limit 1').fetchone()
  source_price_count=db.execute('select count(*) from prices').fetchone()[0]
 boost=grade_boosts();probes=[]
 for sid in [84000250,48000250,12000250,84121939,84037576,30037576,84238380,84214100]:
  pid,economic,floor,score,profilehash=values[sid];identity=economic/economic_curve(score,config);results=[]
  for grade in [1,10,20]:
   result=api('market_price_store?spid='+str(sid)+'&grade='+str(grade));delta=boost[grade]-5;expected=round(economic_curve(score+delta,config)*identity*factors[pid])+floor+33*delta
   assert result['mode']=='bounded_same_player_curve';assert result['active_valuation_model_sha256']==handback['live_price_probe']['active_valuation_model_sha256'];assert result['value']==expected,(sid,grade,result['value'],expected)
   results.append(dict(grade=grade,price_ep=result['value']))
  assert all(b['price_ep']>a['price_ep'] for a,b in zip(results,results[1:]));probes.append(dict(spid=sid,effective_base_score=score,prices=results))
 status=api('market_status');hot=api('hot_update_status');assert status['background']['running'] and status['background']['errors']==0;assert hot['revision']==handback['hot_update_status']['revision'] and hot['watcher_running'] and hot['error'] is None
 result=dict(status='PASS',at=datetime.datetime.now().astimezone().isoformat(),priced_cards=source_price_count,historical_seed_and_trade_events_exact=True,live_grade_price_probes=probes,background=status['background'],hot_update_status=hot,native_or_match_verified=False,formal_written=False)
 (P/'post-install-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
