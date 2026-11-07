from pathlib import Path
P=Path(__file__).resolve().parent

def main():
 old=Path('D:/fifaol3/value-redesign-v12/install.py').read_text('utf8');prefix=old[:old.index('def plan():')]
 prefix=prefix.replace("SELF='patches/fair_value_v12_preflight.py';MANIFEST='patches/fair-value-v12-installed.json';RECEIPT='patches/fair-value-v12-receipt.json'","SELF='patches/grade_price_v14_preflight.py';MANIFEST='patches/grade-price-v14-installed.json';RECEIPT='patches/grade-price-v14-receipt.json'")
 prefix=prefix.replace("owner='fair-value-v12'","owner='grade-price-v14'").replace("'.fair-v12.tmp'","'.grade-v14.tmp'")
 old=Path('D:/fifaol3/nostalgia-value-v13/transaction.py').read_text('utf8');tail=old[old.index('def offline_commit(p):'):]
 tail=tail.replace('v13','v14').replace('V13','V14').replace('nostalgia-utility-ep-v14','base-times-enhancement-v14')
 tail=tail.replace("  check=load(S/'tools/player_import/check.py','v14_formal_import');certificate=check.validate(S,C,full=True);assert certificate==read(S/'gamedata/player-import-validation.json')",'')
 tail=tail.replace("  after=maintenance.migrate_state(state,'base-times-enhancement-v14');after['market_simulation']['price_events']=[];assert assets(after)==assets(state)\n  for k,v in state.get('market_simulation',{}).items():\n   if k not in ['fair_revision','fair_revision_history','identity_quotes','price_events']:assert after['market_simulation'][k]==v,k", """  before_prices={r[0]:r[1] for r in sqlite_rows(backup/'market-before-v14.sqlite','select spid,current_price from prices')}
  assert dict(sqlite_rows(dbpath,'select spid,current_price from prices'))==before_prices,'+1 changed'
  after=maintenance.migrate_state(state,'base-times-enhancement-v14');after['market_simulation']['price_events']=[]
  values={r[0]:tuple(r[1:]) for r in sqlite_rows(dbpath,'select * from fair_values')};factor_map=dict(sqlite_rows(dbpath,'select playerid,factor from player_market_factors'))
  quote=load(P/'system_quotes.py','v14_quote_transaction');boost=load(W/'value-redesign-v12/effective_boosts.py','v14_boost').grade_boosts();model=load(S/'fair_value_model.py','v14_curve')
  after,quote_receipt,quote_changes=quote.reissue(after,read(S/'gamedata/fair-value-v13-model.json'),read(S/'gamedata/fair-value-v14-model.json'),values,factor_map,boost,time.time(),model.economic_curve)
  assert assets(after)==assets(state);assert protected_market(after)==protected_market(state)
  (backup/'system-requoted-offers.json').write_bytes(data(dict(receipt=quote_receipt,changes=quote_changes)))""")
 tail=tail.replace("restored_cards=88,ep_unit_multiplier=1000,official_full_import=certificate['status']", "plus1_prices_unchanged=True,system_quote_receipt=quote_receipt,official_import_check='PASS',enhancement_rates_unchanged=True")
 tail=tail.replace("else:db.execute('delete from '+table+\" where revision='fair-value-v12'\")", "else:db.execute('delete from '+table+\" where revision='nostalgia-utility-ep-v13'\")")
 tail=tail.replace("probe=api('market_price_store?spid=19176944&grade=1')", "probe=api('market_price_store?spid=84037576&grade=20')")
 tail=tail.replace("historical_preference_not_measured_playability=True", "native_match_validation=False,independent_grade_curve=True")
 source=prefix+(P/'transaction_plan.py').read_text('utf8')+'\n'+tail;compile(source,'install.py','exec');(P/'install.py').write_text(source,'utf8');print('Compiled v14 official installer')

if __name__=='__main__':main()
