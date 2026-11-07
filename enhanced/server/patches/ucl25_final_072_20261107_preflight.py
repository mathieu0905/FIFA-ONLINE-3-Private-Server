"""Composed exact-file guard; live market DB has an immutable seed, mutable prices."""
from pathlib import Path
import hashlib,importlib.util,json
MANIFEST='patches/ucl25-final-072-20261107-installed.json'
RECEIPT='patches/ucl25-final-072-20261107-receipt.json'
SELF='patches/ucl25_final_072_20261107_preflight.py'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def preflight(server=None,client=None):
 server=Path(server or Path(__file__).resolve().parent.parent).resolve();m=json.loads((server/MANIFEST).read_text('utf8'));r=json.loads((server/RECEIPT).read_text('utf8'))
 if m.get('schema')!=1 or m.get('state_shop_replaced') is not False:raise RuntimeError('Invalid market price-store scope')
 if r.get('status')!='INSTALLED_25UCL_FINAL_072' or r.get('manifest_sha256')!=sha(server/MANIFEST) or r.get('revision')!=m['revision']:raise RuntimeError('Market price-store receipt mismatch')
 roots=dict(server=server,client=Path(client or m['client']).resolve());seen=set()
 for g in m['guards']:
  root=roots[g['root']];p=(root/g['relative']).resolve();key=(g['root'],g['relative'].replace('\\','/').casefold())
  if not p.is_relative_to(root) or p==root or key in seen:raise RuntimeError('Invalid market guard')
  seen.add(key)
  if not p.is_file() or sha(p)!=g['sha256']:raise RuntimeError('Installed file differs: '+str(key))
 required={('server',SELF),('server','play-local.bat'),('server','market_price_store.py'),('server','npc_exchange.py'),('server','market_simulation.py'),('server','market_supply_settings.py'),('server','market_supply_control.py'),('server','gamedata/npc-market-seed.json.gz'),('server','enhancement_protection40.py')}
 required.update({('server', 'play-local.bat'), ('server', 'patches/ucl25_final_072_20261107_preflight.py'), ('server', 'patches/teammanagementplayerenhancementtabpage.big'), ('client', 'data/ui/teammanagementplayerenhancingpopupscreen.big'), ('client', 'data/ui/teammanagementplayerenhancementtabpage.big'), ('server', 'patches/teammanagementplayerenhancingpopupscreen.big'), ('server', 'docs/工程经验与修改边界.txt')})
 required.update({('server', 'tools/value_v11/features.py'), ('server', 'tools/value_v11/selected-model.json.gz'), ('server', 'gamedata/valuation-v11.json.gz'), ('server', 'tools/value_v11/predict.py')})
 required.update({('server','ai_opponent_progression.py'),('server','http_config.py'),('server','docs/工程经验与修改边界.txt')})
 required.update({('server', 'docs/工程经验与修改边界.txt'), ('client', 'data/ui/teammanagementplayerenhancingpopupscreen.big'), ('server', 'patches/teammanagementplayerenhancingpopupscreen.big'), ('server', 'play-local.bat'), ('client', 'data/ui/teammanagementplayerenhancementtabpage.big'), ('server', 'patches/ucl25_final_072_20261107_preflight.py'), ('server', 'patches/teammanagementplayerenhancementtabpage.big')})
 required.update({('server', 'gamedata/player-import-validation.json'), ('server', 'gamedata/custom_rosters.json'), ('client', 'data/data_0.big'), ('server', 'gamedata/fifadb.sqlite')})
 required.update({('server', 'gamedata/fifadb.sqlite'), ('server', 'gamedata/player-import-validation.json'), ('client', 'data/data_0.big'), ('server', 'gamedata/custom_rosters.json')})
 required.update({('server', 'gamedata/fifadb.sqlite'), ('server', 'gamedata/custom_rosters.json'), ('client', 'data/data_0.big'), ('server', 'gamedata/player-import-validation.json')})
 required.update({('server', 'docs/工程经验与修改边界.txt'), ('client', 'data/ui/teammanagementplayerenhancementtabpage.big'), ('server', 'patches/teammanagementplayerenhancingpopupscreen.big'), ('server', 'patches/teammanagementplayerenhancementtabpage.big'), ('server', 'patches/ucl25_final_072_20261107_preflight.py'), ('server', 'play-local.bat'), ('client', 'data/ui/teammanagementplayerenhancingpopupscreen.big')})
 required.update({('server', 'patches/ucl25_final_072_20261107_preflight.py'), ('server', 'enhancement_protection40.py'), ('client', 'data/ui/teammanagementplayerenhancingpopupscreen.big'), ('server', 'patches/teammanagementplayerenhancementtabpage.big'), ('server', 'play-local.bat'), ('server', 'docs/工程经验与修改边界.txt'), ('client', 'data/ui/teammanagementplayerenhancementtabpage.big'), ('server', 'patches/teammanagementplayerenhancingpopupscreen.big')})
 required.update({('server','fo4_live_market.py'),('server','gamedata/fo4-live-price-extension.json'),('server','tools/player_import/prepare.py'),('server','tools/player_import/check.py'),('server','gen_teams.py'),('server','admin.py'),('server','admin/index.html'),('server','gamedata/player-import-validation.json')})
 required.update({('server', 'patches/ucl25_final_072_20261107_preflight.py'), ('client', 'data/ui/teammanagementplayercardscreen.big')})
 required.update({('server','china_future_market.py'),('server','gamedata/china-future-price-extension.json'),('server','gamedata/player-import-validation.json'),('server','responses/static_roster.json')})
 required.update({('client', 'data/ui/teammanagementplayercardscreen.big'), ('server', 'patches/ucl25_final_072_20261107_preflight.py')})
 required.update({('server','gamedata/club_season_products.json'),('server','gamedata/all_item_icon_manifest.json')})
 required.update({('server','gamedata/custom_rosters.json'),('server','gamedata/china-future-portraits.json'),('server','gamedata/player-import-validation.json')})
 required.update({('client', 'data/ui/teammanagementplayercardscreen.big'), ('server', 'patches/ucl25_final_072_20261107_preflight.py')})
 required.update({('client', 'data/ui/teammanagementplayercardscreen.big'), ('server', 'patches/ucl25_final_072_20261107_preflight.py')})
 required.update({('server', 'fair_value_model.py'), ('server', 'fair_value_store.py'), ('server', 'gamedata/fair-value-v12-model.json'), ('server', 'gamedata/fair-value-v12-catalogue.json.gz')})
 required.update({('server', 'gamedata/fair-value-v13-catalogue.json.gz'), ('server', 'gamedata/fair-value-v13-utility-evidence.json.gz'), ('server', 'gamedata/fair-value-v13-model.json')})
 required.update({('server', 'gamedata/fair-value-v14-catalogue.json.gz'), ('server', 'gamedata/fair-value-v14-model.json')})
 required.update({('server','gamedata/fair-value-nostalgia87-model.json'),('server','gamedata/fair-value-nostalgia87-catalogue.json.gz')})
 required.update({('client','data/ui/components/scrollinglist.big'),('server','patches/scrollinglist.big')})
 required.update({('client','data/ui/components/scrollinglist.big'),('server','patches/scrollinglist.big'),('client','data/ui/teammanagementscreen.big'),('server','patches/teammanagementscreen.big')})
 required.update({('server', 'upstream_social_compat.py'), ('server', 'patches/ucl25_final_072_20261107_preflight.py'), ('server', 'http_config.py'), ('server', 'responses/ladder_division_info.json'), ('server', 'play-local.bat'), ('server', 'responses/vm_chat.json'), ('server', 'messenger.py'), ('server', 'responses/ladder_reward_info.json'), ('client', 'data/ui/optioncontrolsettingscreen.big'), ('server', 'docs/工程经验与修改边界.txt'), ('server', 'admin.py'), ('server', 'admin/index.html')})
 required.update({('client','data/ui/components/scrollinglist.big'),('server','patches/scrollinglist.big'),('client','data/ui/teammanagementscreen.big'),('server','patches/teammanagementscreen.big')})
 required.update({('client','data/ui/components/scrollinglist.big'),('server','patches/scrollinglist.big'),('client','data/ui/teammanagementscreen.big'),('server','patches/teammanagementscreen.big')})
 required.update({('client','data/ui/components/scrollinglist.big'),('server','patches/scrollinglist.big'),('client','data/ui/teammanagementscreen.big'),('server','patches/teammanagementscreen.big'),('client','data/ui/components/button.big'),('server','patches/button.big')})
 required.update({('client','data/ui/components/scrollinglist.big'),('server','patches/scrollinglist.big'),('client','data/ui/teammanagementscreen.big'),('server','patches/teammanagementscreen.big'),('client','data/ui/components/button.big'),('server','patches/button.big')})
 if not required<=seen:raise RuntimeError('Incomplete market price-store guard')
 if ('server','gamedata/npc-market-prices.sqlite') in seen:raise RuntimeError('Mutable current prices must not be frozen by a file hash')
 for policy in m.get('composition',{}).get('receipt_policies',[]):
  root=roots[policy['root']];p=(root/policy['relative']).resolve()
  if not p.is_relative_to(root) or p==root:raise RuntimeError('Receipt path escape')
  receipt=json.loads(p.read_text('utf-8-sig'))
  if {k:v for k,v in receipt.items() if k!='native_status'}!=policy['installation_fields']:raise RuntimeError('Parent receipt installation fields changed')
 spec=importlib.util.spec_from_file_location('_price_seed_check',server/'market_price_store.py');store=importlib.util.module_from_spec(spec);spec.loader.exec_module(store)
 config_path=server/'gamedata/market-supply-config.json'
 if ('server','gamedata/market-supply-config.json') in seen:raise RuntimeError('Online market configuration must remain mutable')
 cfgspec=importlib.util.spec_from_file_location('_market_supply_validate',server/'market_supply_settings.py');cfg=importlib.util.module_from_spec(cfgspec);cfgspec.loader.exec_module(cfg)
 if config_path.exists():cfg.validate(json.loads(config_path.read_text('utf-8-sig')))
 seed=store.verify_seed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/npc-market-seed.json.gz')
 valuation=store.verify_calibration(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/valuation-v11.json.gz')
 spec=importlib.util.spec_from_file_location('_fo4_live_seed_guard',server/'fo4_live_market.py');extension=importlib.util.module_from_spec(spec);spec.loader.exec_module(extension)
 live_prices=extension.verify(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fo4-live-price-extension.json')
 spec=importlib.util.spec_from_file_location('_china_future_guard',server/'china_future_market.py');china_ext=importlib.util.module_from_spec(spec);spec.loader.exec_module(china_ext)
 china_prices=china_ext.verify(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/china-future-price-extension.json')
 import sys
 sys.path.insert(0,str(server))
 from fair_value_store import verify_installed
 historical_fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-v12-catalogue.json.gz',server/'gamedata/fair-value-v12-model.json',server/'gamedata/fifadb.sqlite')
 previous_fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-v13-catalogue.json.gz',server/'gamedata/fair-value-v13-model.json',server/'gamedata/fifadb.sqlite')
 fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-v14-catalogue.json.gz',server/'gamedata/fair-value-v14-model.json',server/'gamedata/fifadb.sqlite')
 nostalgia_fair_value=verify_installed(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-nostalgia87-catalogue.json.gz',server/'gamedata/fair-value-nostalgia87-model.json',server/'gamedata/fifadb.sqlite')
 import sqlite3
 with sqlite3.connect((server/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as database:
  if database.execute('select count(*) from players where playerid=231747 or spid%1000000=231747').fetchone()[0]:raise RuntimeError('Removed player reintroduced')
 import sqlite3
 with sqlite3.connect((server/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as database:
  if database.execute('select count(*) from players where playerid=231747 or spid%1000000=231747').fetchone()[0]:raise RuntimeError('Removed player reintroduced')
 spec=importlib.util.spec_from_file_location('_ucl25_value_check',server/'ucl25_value_extension.py');ucl25=importlib.util.module_from_spec(spec);spec.loader.exec_module(ucl25)
 ucl25.verify(server/'gamedata/npc-market-prices.sqlite',server/'gamedata/fair-value-25ucl-catalogue.json.gz',server/'gamedata/fair-value-25ucl-model.json',server/'gamedata/fifadb.sqlite')
 return dict(nostalgia_fair_value=nostalgia_fair_value,previous_fair_value=previous_fair_value,historical_fair_value=historical_fair_value,fair_value=fair_value,china_future_prices=china_prices,fo4_live_prices=live_prices,status='25UCL_FINAL_072_PREFLIGHT_PASS',files=len(seen),revision=m['revision'],seed=seed,valuation=valuation,runtime_model_loaded=True,native_status='PENDING',state_shop_touched=False)
def compose_manifest(server=None,client=None):
 server=Path(server or Path(__file__).resolve().parent.parent).resolve();m=json.loads((server/MANIFEST).read_text('utf8'));c=dict(m.get('composition') or {});guards=list(m['guards'])
 for rel in (MANIFEST,RECEIPT):guards.append(dict(root='server',relative=rel,sha256=sha(server/rel)))
 c.update(server=str(server),client=str(Path(client or m['client']).resolve()),guards=guards);c.setdefault('ancestry',[]);c.setdefault('receipt_policies',[])
 return c
if __name__=='__main__':print(json.dumps(preflight(),ensure_ascii=True))
