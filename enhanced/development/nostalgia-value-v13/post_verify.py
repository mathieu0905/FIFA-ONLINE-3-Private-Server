"""Verify whole-catalogue publication and actual base/derived grade prices, read-only."""
from pathlib import Path
from contextlib import closing
import ast,datetime,gzip,hashlib,json,sqlite3,sys,urllib.request
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(P));sys.path.append('D:/fifaol3/value-redesign-v12')
from effective_boosts import grade_boosts
from fair_value_model import economic_curve
def read(p):return json.loads(Path(p).read_text('utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(name):
 with urllib.request.urlopen('http://127.0.0.1:8088/api/'+name,timeout=15) as f:return json.load(f)
def main():
 h=read(P/'installed-handback.json');folder=Path(read(P/'latest-build.json')['path']);build=read(folder/'report.json');cfg=read(S/'gamedata/fair-value-v13-model.json');oldcfg=read(S/'gamedata/fair-value-v12-model.json');assert cfg['curve']==oldcfg['curve'];assert cfg['currency_scale']==oldcfg['currency_scale']*1000
 for target,artifact in [(S/'gamedata/fifadb.sqlite','fifadb.sqlite'),(S/'gamedata/custom_rosters.json','custom_rosters.json'),(C/'data/data_0.big','data_0.big')]:assert sha(target)==sha(folder/artifact)
 with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  db.row_factory=sqlite3.Row;db.execute('begin');db.execute('attach database ? as beforev13',((Path(h['backup'])/'market-before-v13.sqlite').as_uri()+'?mode=ro',))
  assert not db.execute('select * from beforev13.seeds except select * from main.seeds limit 1').fetchone();assert not db.execute('select * from beforev13.price_events except select * from main.price_events limit 1').fetchone()
  count=db.execute('select count(*) from fair_values').fetchone()[0];assert count==build['catalogue_rows'];assert db.execute("select count(*) from price_events where event_id like 'fair-calibration:nostalgia-utility-ep-v13:%'").fetchone()[0]==count
  values={r['spid']:dict(r) for r in db.execute('select * from fair_values')};factors=dict(db.execute('select playerid,factor from player_market_factors'));prices=dict(db.execute('select spid,current_price from prices'))
  historical_count=db.execute("select count(*) from fair_value_history where revision='fair-value-v12'").fetchone()[0];assert historical_count==count
  assert all(prices[sid]==round(r['economic_value']*factors[r['playerid']])+r['strict_floor'] for sid,r in values.items())
 with closing(sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  db.row_factory=sqlite3.Row
  for change in read(folder/'changes.json'):assert dict(db.execute('select * from players where spid=?',(change['spid'],)).fetchone())==change['after']
  rows=[dict(r) for r in db.execute('select p.*,n.short as name from players p left join nameschi n using(playerid)')];eligible={r[0] for r in db.execute('select p.spid from players p join permid m using(spid) where m.transferable=1 and p.spid>=1000000 and p.playerid in(select playerid from namesind)')};eligible|={int(x) for x in read(S/'gamedata/fa_prices.json')}
 boost=grade_boosts();probes=[]
 for sid in [19173731,19195864,19176944,19201862,84037576,93214100,48167905,30037576,13158023,84238380]:
  r=values[sid];identity=r['economic_value']/economic_curve(r['effective_score'],cfg);results=[]
  for g in [1,10,20]:
   result=api('market_price_store?spid='+str(sid)+'&grade='+str(g));delta=boost[g]-5;expected=round(economic_curve(r['effective_score']+delta,cfg)*identity*factors[r['playerid']])+r['strict_floor']+33*delta;assert result['value']==expected,(sid,g,result['value'],expected);assert result['active_valuation_revision']=='nostalgia-utility-ep-v13';results.append(dict(grade=g,price_ep=result['value']))
  probes.append(dict(spid=sid,prices=results))
 # The actual enhancement implementation is byte-for-byte inherited, not refitted.
 journal=read(Path(h['backup'])/'transaction.json');i=next(i for i,r in enumerate(journal['files']) if r['relative']=='fair_value_store.py');oldsource=Path(h['backup'])/(str(i)+'-fair_value_store.py')
 def class_ast(p):return ast.dump(next(n for n in ast.parse(Path(p).read_text('utf8')).body if isinstance(n,ast.ClassDef) and n.name=='FairLayer'),include_attributes=False)
 assert class_ast(oldsource)==class_ast(S/'fair_value_store.py')
 st=read(S/'gamedata/state.json');before=read(Path(h['backup'])/'state-fresh.json');assets=lambda d:{k:v for k,v in d.items() if k!='market_simulation'};assert assets(st)==assets(before);assert sha(S/'gamedata/shop.json')==sha(Path(h['backup'])/'shop-fresh.json')
 market=api('market_status');hot=api('hot_update_status');assert market['background']['running'] and market['background']['errors']==0;assert hot['watcher_running'] and hot['error'] is None
 roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split();seasons={r['id']:r['label'] for r in read(S/'gamedata/custom_rosters.json')['seasons']};export=[]
 for r in rows:
  if r['spid'] not in eligible:continue
  w=cfg['role_weights'][roles[r['preferredposition1']]];v=values[r['spid']];export.append(dict(spid=r['spid'],name=r['name'],season=seasons.get(r['spid']//1000000,str(r['spid']//1000000)),ability=sum(r[k]*a for k,a in w.items())//sum(w.values())+5,attribute_score=v['effective_score'],historical_preference_factor=cfg['identity_factors'].get(str(r['playerid']),{}).get('factor',1),price_ep=prices[r['spid']]))
 export.sort(key=lambda r:(-r['ability'],-r['price_ep'],r['spid']));counts={}
 for r in export:counts[r['season']]=counts.get(r['season'],0)+1
 lines=['全赛季正式卡价（1级+1主位置能力降序）',datetime.datetime.now().astimezone().isoformat(),'价格已采用新EP币值及有限历史偏好溢价；属性估值分不等于实测实战能力。强化沿现有曲线派生。','能力｜赛季｜球员｜属性估值分｜历史偏好因子｜当前参考价EP｜SPID']
 for r in export:lines.append(f"{r['ability']}｜{r['season']}｜{r['name']}｜{r['attribute_score']:.2f}｜{r['historical_preference_factor']:.3f}｜{r['price_ep']:,}｜{r['spid']}")
 (P/'全赛季正式卡价.txt').write_text('\n'.join(lines)+'\n','utf8')
 result=dict(status='PASS',at=datetime.datetime.now().astimezone().isoformat(),all_catalogue_cards=count,tradeable_cards=len(export),season_counts=counts,all_prices_match_new_economics_and_shared_factors=True,new_calibration_receipts=count,prior_generation_archived_rows=historical_count,historical_seeds_and_trade_events_exact=True,all88_formal_rows_match_authentic_sources=True,base_price_calibrated_only=True,enhancement_FairLayer_ast_unchanged=True,curve_shape_unchanged=True,actual_grade_boosts=boost,live_base_and_derived_grade_probes=probes,asset_projection_equal=True,shop_equal=True,background=market['background'],hot=hot,native_or_match_verified=False)
 (P/'post-install-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps({k:v for k,v in result.items() if k not in ['season_counts']},ensure_ascii=False))
if __name__=='__main__':main()
