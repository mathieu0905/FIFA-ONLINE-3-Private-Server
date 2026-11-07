from pathlib import Path
from contextlib import closing
import sys,json,sqlite3,time,importlib.util
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 from fair_value_model import economic_curve
 helper=load(P/'system_quotes.py','v14_quote');installer=load(P/'install.py','v14_install');boost=load(Path('D:/fifaol3/value-redesign-v12/effective_boosts.py'),'boost').grade_boosts()
 state=json.loads((S/'gamedata/state.json').read_text('utf8'));old=json.loads((S/'gamedata/fair-value-v13-model.json').read_text('utf8'));new=json.loads((P/'model.json').read_text('utf8'))
 with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').resolve().as_uri()+'?mode=ro',uri=True)) as db:
  values={r[0]:tuple(r[1:]) for r in db.execute('select * from fair_values')};factors=dict(db.execute('select playerid,factor from player_market_factors'))
 after,receipt,changes=helper.reissue(state,old,new,values,factors,boost,time.time(),economic_curve)
 assert installer.assets(after)==installer.assets(state);assert installer.protected_market(after)==installer.protected_market(state)
 result=dict(status='PASS',formal_written=False,receipt=receipt,all_asset_inventory_cost_expiry_and_trade_fields_unchanged=True,maximum_reissued_ask=max((r['after'] for r in changes),default=0),changed_grade_counts={str(g):sum(r['grade']==g for r in changes) for g in range(1,21)})
 (P/'quote-dry-run.json').write_text(json.dumps(result,indent=2)+'\n','utf8');print(json.dumps(result))
if __name__=='__main__':main()
