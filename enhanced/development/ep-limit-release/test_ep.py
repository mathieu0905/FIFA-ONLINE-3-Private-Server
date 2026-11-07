from pathlib import Path
import ast, copy, hashlib, json, os, sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
S = ROOT / 'server'
def audit(event, args):
    if event in ('socket.bind', 'subprocess.Popen'):
        raise PermissionError('No service start in EP regression')
    if event == 'open':
        path, mode, flags = args
        if isinstance(path, (str, bytes, Path)) and ((mode and any(c in mode for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            if not Path(os.fsdecode(path)).resolve().is_relative_to(ROOT):
                raise PermissionError('External write blocked: ' + str(path))
sys.addaudithook(audit)
sys.path.insert(0, str(S)); os.chdir(S)
sys.argv = ['http_config.py']
os.environ.update(FO3_ADMIN_PORT='0', FO3_MAX_GRADE='20', FO3_LANGUAGE='chi', FO3_GAME='D:/FO3ID/32795')
import http_config as h
import admin
admin.hc = h
assert Path(h.HERE) == S and Path(h.gen_teams.DB) == S / 'gamedata/fifadb.sqlite'
original = copy.deepcopy(h._state())
def target():
    return admin.API['summary']({})['admin_target']
counter = 0
def grant(payload, operation=None):
    global counter
    counter += 1
    return admin.API['ep']({**payload, '_admin_target': target(), '_admin_operation': operation or f'ep-regression-{counter:08d}'})

try:
    admin.check_i18n()
    before_ast=ast.parse((ROOT/'before/http_config.py').read_text(encoding='utf-8'))
    after_ast=ast.parse((S/'http_config.py').read_text(encoding='utf-8'))
    before_functions={x.name:ast.dump(x) for x in before_ast.body if isinstance(x,ast.FunctionDef)}
    after_functions={x.name:ast.dump(x) for x in after_ast.body if isinstance(x,ast.FunctionDef)}
    for name in ('card_price','stat_price','enhance_cost','pack_price','add_ep','cup_reward_ep'):
        assert before_functions[name]==after_functions[name],name
    # Quotes convert once; no wallet, player, listing, historical sale or stock
    # quantities are reset by the transition.
    migration=copy.deepcopy(h._state());m=migration['market_simulation'];m.pop('player_price_divisor',None)
    m['books']={'42':{'epoch':123,'rows':[{'price':1234567,'count':0},{'price':999,'count':2}]}}
    m['rare_books']={};m['legacy_supply']=[{'price':1000000,'count':1}]
    m['supply_version']=3
    migration['offers']=[{'status':'sold','price':999999999,'completefee':{'base':99999}}]
    coaches=copy.deepcopy(migration['coaches']);teams=copy.deepcopy(migration['teams']);offers=copy.deepcopy(migration['offers'])
    h.market_engine.prepare(migration)
    assert m['books']['42']['rows']==[{'price':1234,'count':0},{'price':1,'count':2}]
    assert m['legacy_supply']==[{'price':1000,'count':1}]
    again=copy.deepcopy(migration);h.market_engine.prepare(migration);assert migration==again
    assert migration['coaches']==coaches and migration['teams']==teams and migration['offers']==offers
    exact = 100000000000000001
    r = grant({'set':str(exact)}, 'ep-regression-exact-set')
    assert r == {'ep':exact, 'ep_exact':str(exact)}, r
    st = h._state()
    assert h.my_coach(st)['ep'] == exact
    assert admin.API['summary']({})['coach']['ep_exact'] == str(exact)
    assert grant({'set':str(exact)}, 'ep-regression-exact-set') == r
    assert h.my_coach(h._state())['ep'] == exact
    assert grant({'add':'7'})['ep'] == exact + 7
    assert grant({'add':'-3'})['ep'] == exact + 4
    for bad in (str(10**18+1), 10**18+1, True, 1.5, '1.5', '1e18', '', ' 1', None, '-1'):
        before = (S/'gamedata/state.json').read_bytes()
        assert grant({'set':bad}).get('admin_grant_rejected'), bad
        assert (S/'gamedata/state.json').read_bytes() == before
    assert grant({'set':str(10**18)})['ep'] == 10**18
    assert grant({'set':0})['ep'] == 0
    assert grant({'add':'-1'})['ep'] == 0

    # Real purchase handler and asset persistence, with deterministic private NPC
    # supply only. No production HTTP or balance is touched.
    engine = h.market_engine
    ratings = h.card_ovrs([s for s in h.market_spids() if s // 1000000 != 84])
    spid = max(ratings, key=lambda s: ratings[s] or 0)
    unscaled_price = h.card_price(spid,20)
    price = h.player_value_price(spid,20)
    assert 10**13 < unscaled_price < 10**18, unscaled_price
    assert price == unscaled_price // 1000
    assert engine.reference(spid,20) == price
    row = {'spid':spid, 'grade':20, 'price':price, 'count':1}
    rows_before = engine.rows
    engine.rows = lambda *args: [row] if row['count'] else []
    grant({'set':str(price-1)})
    st = copy.deepcopy(h._state())
    result = json.loads(engine.purchase(spid,20,price,'',b'{}')[1])
    assert result.get('result') is False and 'NOT_ENOUGH_EP' in str(result), result
    assert h._state() == st
    grant({'set':str(exact)})
    st = copy.deepcopy(h._state()); slot = h._default_slot(st)
    old = copy.deepcopy(st['teams'][str(slot)]['players'])
    result = json.loads(engine.purchase(spid,20,price,'',b'{}')[1])
    assert result['result'] is True, result
    after = h._state(); players = after['teams'][str(slot)]['players']
    assert h.my_coach(after)['ep'] == exact-price
    assert len(players) == len(old)+1 and players[:len(old)] == old
    assert players[-1]['spid'] == spid and h.grade_of(players[-1]) == 20
    snap = copy.deepcopy(after)
    assert json.loads(engine.purchase(spid,20,price,'',b'{}')[1])['result'] is False
    assert h._state() == snap
    engine.rows = rows_before
    report = dict(status='PASS', isolated=True, exact_balance=exact, test_price=price,
                  tests=['player_value_div1000','shop_reward_enhancement_price_functions_unchanged','npc_quote_migration_once_no_refill',
                         'wallet_players_and_sold_entitlements_preserved','exact_decimal_set_add_sub','replay_does_not_duplicate','invalid_values_do_not_write',
                         'zero_and_limit','insufficient_balance_no_mutation','real_market_high_price_purchase',
                         'old_players_preserved','stock_replay_no_double_charge','six_language_labels'])
    (ROOT/'test-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
finally:
    h._save(original)
