"""In-memory host and temporary reward settings; never run another server."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import os
import random
import sqlite3
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True
R = Path(__file__).resolve().parent
S = Path(r'D:\FO3ID\server')
os.environ.update(FO3_MAX_GRADE='20', FO3_LANGUAGE='chi')
sys.argv = [sys.argv[0]]
sys.path.insert(0, str(S))

# The production market installs a pending-event replay on import. Redirect its
# database before loading the host, and leave that unrelated startup replay out
# of these UI/reward tests. No listener or background worker is started.
import market_price_store
MARKET_TEMP = tempfile.TemporaryDirectory(dir=R, prefix='market-fixture-')
MARKET_DB = Path(MARKET_TEMP.name)/'prices.sqlite'
source = sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro', uri=True)
destination = sqlite3.connect(MARKET_DB)
source.backup(destination)
source.close();destination.close()
LIVE_DATA = True
if LIVE_DATA:
    sys.path.insert(0,str(R))
    import price_extension
    price_extension.apply(MARKET_DB,R/'prices.json')
old_store_init = market_price_store.MarketPriceStore.__init__
old_store_flush = market_price_store.MarketPriceStore.flush
market_price_store.MarketPriceStore.__init__ = lambda self, path: old_store_init(self, MARKET_DB)
market_price_store.MarketPriceStore.flush = lambda self, events: 0


def staged(name, filename):
    module = types.ModuleType(name)
    module.__file__ = str(S/filename)
    sys.modules[name] = module
    exec(compile((R/'adapted-source'/filename).read_text('utf8'), module.__file__, 'exec'), module.__dict__)
    return module


gen = staged('gen_teams', 'gen_teams.py')
if LIVE_DATA:
    gen.DB = str(R/'prepared-v3/fifadb.sqlite')
    gen.CURRENT_SEASON = gen._current_season()
admin = staged('admin', 'admin.py')
hc = staged('http_config', 'http_config.py')
market_price_store.MarketPriceStore.__init__ = old_store_init
market_price_store.MarketPriceStore.flush = old_store_flush
admin.hc = hc


def body(response):
    return json.loads(response[1])


def main():
    cases = []
    if LIVE_DATA:
        cards = json.loads((R/'input/cards.json').read_text('utf8'))
        assert gen.CURRENT_SEASON == 300
        assert all(hc.on_market(c['fo3_spid']) and hc.player_value_price(c['fo3_spid'],1)>0 for c in cards)
        cases.append('all_32_future_cards_market_eligible_and_positive_price')
        for itemid in (92000000,92000014):
            if itemid in hc.PACKS:
                assert all(spid//1000000 not in (300,325,327) for spid,weight in hc.pack_pool(itemid))
        cases.append('legacy_packs_do_not_gain_new_seasons')
    # Reject every write until the synthetic state destination is installed.
    hc._save = lambda st: (_ for _ in ()).throw(AssertionError('Unexpected save'))
    with tempfile.TemporaryDirectory(dir=R, prefix='regression-') as temporary:
        temp = Path(temporary)
        hc.MATCH_REWARD_FILE = str(temp/'match_rewards.json')
        hc.OWN_ASSETS, hc.ASSETS = str(temp/'own'), str(temp/'cache')
        own, cache = Path(hc.OWN_ASSETS), Path(hc.ASSETS)
        small = cache/'externalAssets/crests/small/s11.png'
        small.parent.mkdir(parents=True)
        small.write_bytes(b'native-small-fixture')
        assert hc.asset_path('externalAssets/crests/large/s11.png') == str(small)
        assert hc.cdn_file('externalAssets/crests/large/s11.png')[1] == b'native-small-fixture'
        cases.append('crest_other_size_fallback')
        exact = own/'externalAssets/crests/large/s11.png'
        exact.parent.mkdir(parents=True)
        exact.write_bytes(b'exact-own-fixture')
        assert hc.asset_path('externalAssets/crests/large/s11.png') == str(exact)
        assert hc.asset_path('../outside.png') is None
        assert hc.asset_path(str(small.resolve())) is None
        cases.append('asset_priority_and_path_escape')

        ids = [tid for _, leagues in hc.club_index() for lid, teams in leagues if lid == 78 for tid in teams]
        assert len(ids) >= 40
        with hc.closing(hc._db()) as con:
            for tid in ids:
                team = gen.team(con, tid)
                assert team and team['summary']['league']['id'] == 78
                ps = team['team']['players']
                assert len({p['spid'] % 1000000 for p in ps}) == len(ps)
                assert len(team['team']['squad']['positions']) == 11
            assert gen.team(con, 0) is None and gen.team(con, -1) is None
        cases.append('national_teams_'+str(len(ids)))
        assert hc.club_index()[-1][1][-1][0] == 78 or any(lid == 78 for lid, teams in hc.club_index()[-1][1])
        cases.append('national_group_last')

        old_db = gen.DB
        gen.DB = str(temp/'season-detection.sqlite')
        with sqlite3.connect(gen.DB) as con:
            con.execute('create table players(spid integer)')
            assert gen._current_season() == 88
            con.execute('insert into players values(300123456)'); con.commit()
            assert gen._current_season() == 300
        con.close()
        gen.DB = old_db
        cases.append('26_live_default_only_when_installed')

        left = hc.match_side(hc.roster_team(241), 241, {'id': 'synthetic', 'name': 'synthetic', 'levelinfo': {'level':1}})
        right = hc.match_side(hc.roster_team(243), 243)
        match = hc.new_match('League_2_league', left, right)
        result = hc.sim_result(match, [], True, random.Random(7))
        for key, side in (('home','left'), ('away','right')):
            positions = match['side'][side]['squad']['positions']
            for p, slot in zip(result[key]['players'], positions):
                assert p['role'] == slot['pos'] and p['spid'] == slot['spid']
                assert p['dbid'] == int(slot['spid']) % 1000000
        cases.append('simulation_positions_and_full_seasons')
        old_result = copy.deepcopy(result)
        for key in ('home','away'):
            for p in result[key]['players']:
                p.update(role=0, spid=p['dbid'])
        hc.fill_players(match, result)
        assert result['home']['players'] == old_result['home']['players']
        assert result['away']['players'] == old_result['away']['players']
        assert result['motm']['spid'] == old_result['motm']['spid']
        cases.append('played_positions_seasons_and_motm')

        default = hc.match_reward_cfg()
        assert default['result']['win'] == {'ep':2000,'coach':300,'player':150}
        malformed = copy.deepcopy(default); malformed['result']['win']['ep'] = True
        Path(hc.MATCH_REWARD_FILE).write_text(json.dumps(malformed),'utf8')
        assert hc.match_reward_cfg() == default
        cases.append('bad_settings_fall_back_without_crash')
        chosen = copy.deepcopy(default); chosen['cards'] = [[1, {'ep':1234}]]
        saved = admin.API['match_rewards_set'](chosen)
        assert saved == chosen and hc.match_reward_cfg() == chosen
        assert 'match_rewards' in admin.READ_ONLY and 'match_rewards_set' not in admin.READ_ONLY
        cases.append('atomic_admin_settings_read_every_match')
        for bad in (True, -1, 1.5, float('nan'), 10**10):
            invalid = copy.deepcopy(chosen); invalid['result']['win']['ep'] = bad
            try:
                admin.API['match_rewards_set'](invalid)
            except (ValueError, TypeError, admin.AdminError):
                pass
            else:
                raise AssertionError('Bad reward accepted: '+repr(bad))
        assert hc.match_reward_cfg() == chosen
        cases.append('invalid_settings_never_replace_valid_configuration')

        storage = {'coaches':[], 'defaultcoachid':'', 'teams':{}}
        saves = []
        hc._state = lambda: copy.deepcopy(storage)
        def save(st):
            saves.append(copy.deepcopy(st));storage.clear();storage.update(copy.deepcopy(st))
        hc._save = save
        spids = [p['spid'] for p in hc.roster_team(241)['players']]
        assert body(hc.ENDPOINTS['/coach/0/new/step/3']('', json.dumps({'id':241,'spids':spids}).encode()))['result']
        assert body(hc.ENDPOINTS['/coach/0']('', json.dumps({'id':241,'coachName':'memory-only'}).encode()))['result']
        assert body(hc.ENDPOINTS['/coach/0/default']('', b''))['result']
        body(hc.ENDPOINTS['/league2/calendar']('', json.dumps({'difficulty':10,'sponsor':'1'}).encode()))
        st = copy.deepcopy(storage)
        match = hc.league_match_body(st, {'home':241,'away':243,'round':0}, 'play')
        mid = match['id'];match['stage'] = 'playing';st['match'] = match
        save(st)
        stats = hc.sim_result(match, [], True, random.Random(9))
        stats['home']['score'], stats['away']['score'] = 2, 0
        for key in ('home','away'):
            for p in stats[key]['players']:p.update(role=0,spid=p['dbid'])
        ep_before = hc.my_coach(storage).get('ep',hc.START_EP)
        count = len(saves)
        response = body(hc.ep_match_end(mid, '', json.dumps(stats).encode()))
        assert response['result'] and len(saves) == count+1
        reward = storage['match']['reward']
        assert len(reward['extra']['availables']) == 3 and reward['extra']['selected'] == {'normal':[0]}
        assert reward['money']['reward']['total'] == 2000 and reward['cashreward']['total'] == 1000
        assert hc.my_coach(storage).get('ep',0) == ep_before+2000+1234
        assert storage['match']['result']['home']['players'][1]['role'] != 0
        paid = copy.deepcopy(storage)
        for _ in range(10):
            assert body(hc.ep_match_end(mid, '', json.dumps(stats).encode()))['result']
            assert storage == paid
        cases.append('one_guarded_commit_includes_ep_exp_cash_card_and_result')
        cases.append('ten_replays_no_duplicate_rewards')

        html = (R/'adapted-source/admin/index.html').read_text('utf8')
        import re
        scripts = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', html, re.S)
        for i, code in enumerate(scripts):
            file = temp/('script-'+str(i)+'.js');file.write_text(code,'utf8')
            subprocess.run(['node','--check',str(file)], check=True, capture_output=True)
        cases.append('custom_admin_javascript_syntax')
        assert html.count('id="match"') == 1 and html.count('async match()') == 1
        cases.append('single_match_admin_tab')

    original_ast = ast.parse((S/'http_config.py').read_text('utf8'))
    changed_ast = ast.parse((R/'adapted-source/http_config.py').read_text('utf8'))
    functions = lambda tree: {n.name: ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    before, after = functions(original_ast), functions(changed_ast)
    intended = {'cdn_file','match_reward','roster','from_file','sim_result','ep_match_end','club_index','pack_pool','tc_seasons','tc_special_sets','tc_colors'}
    assert all(before[name] == after[name] for name in before.keys()-intended)
    hooks = lambda tree: [ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr in ('install','install_runtime')]
    assert hooks(original_ast) == hooks(changed_ast)
    cases.append('all_custom_install_hooks_and_unrelated_functions_preserved')
    report = dict(status='PASS', case_count=len(cases), cases=cases, real_state_shop_written=False,
                  services_started=False, native_game_verified=False)
    (R/('integrated-live-tests.json' if LIVE_DATA else 'compat-tests.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    finally:
        hc.market_engine.exchange.price_store._db.close()
        MARKET_TEMP.cleanup()
