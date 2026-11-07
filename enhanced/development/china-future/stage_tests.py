from pathlib import Path
import shutil
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');U=R.parent/'upstream-review'
out=R/'adapted-source';(out/'admin').mkdir(parents=True,exist_ok=True)
shutil.copyfile(R/'http_config.py',out/'http_config.py')
for f in ['gen_teams.py','admin.py','admin/index.html']:shutil.copyfile(S/f,out/f)
s=(U/'test_compat.py').read_text('utf8')
s=s.replace("LIVE_DATA = os.environ.get('FO3_TEST_LIVE_DATA') == '1'",'LIVE_DATA = True')
s=s.replace('live_market_extension','price_extension').replace("R/'adapted-source/gamedata/fo4-live-price-extension.json'","R/'prices.json'")
s=s.replace("R/'live-prepared-v3/fifadb.sqlite'","R/'prepared-v3/fifadb.sqlite'").replace("R/'live-data-input/cards.json'","R/'input/cards.json'")
s=s.replace("c['spid']","c['fo3_spid']").replace('all_688_new_cards','all_32_future_cards').replace('not in (300,325)','not in (300,325,327)')
s=s.replace("'ep_match_end','club_index','pack_pool'","'ep_match_end','club_index','pack_pool','tc_seasons','tc_special_sets','tc_colors'")
(R/'test_compat.py').write_text(s,'utf8')
s=(U/'test_transaction.py').read_text('utf8').replace('703','42').replace('(1,351,42)','(1,21,42)')
(R/'test_transaction.py').write_text(s,'utf8')
print('Combined in-memory tests staged; no additional game service')
