"""Read-only all-card audit plus isolated market contract regressions."""
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
import ast
import copy
import hashlib
import importlib.util
import json
import math
import random
import sqlite3
import sys
import tempfile
import threading

HERE = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')
sys.path[:0] = [str(HERE / 'payload'), str(SERVER)]
from ability_value import AbilityValuePolicy, AbilityPriceBook, MAX_PRICE
from npc_exchange import NpcExchange
from market_simulation import Market


def constants():
    values = {'MAX_GRADE': 20}
    for node in ast.parse((SERVER / 'http_config.py').read_text('utf8')).body:
        if isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id in ('GRADE_PRICE', 'GRADE_BOOST', 'ROLE_WEIGHTS', 'POS_ROLE') for n in node.targets):
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'native_constants', 'exec'), values)
    spec = importlib.util.spec_from_file_location('native_progression', SERVER / 'enhancement_progression.py')
    progression = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(progression)
    values['PROGRESSION20'] = {'price_steps': {str(g): percent / 100 for g, percent in enumerate(progression.PRICE_STEPS, 11)}}
    return values


def main():
    checks = []
    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    policy = AbilityValuePolicy(HERE / 'ability_value_policy.json')
    native = constants()
    check(policy.weights == native['ROLE_WEIGHTS'] and policy.config['position_roles'] == native['POS_ROLE'], 'Exact native client role weights')
    with closing(sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = {r['spid']: dict(r) for r in db.execute('SELECT * FROM players')}
    with closing(sqlite3.connect('file:D:/FO3ID/server/gamedata/npc-market-prices.sqlite?mode=ro', uri=True)) as db:
        prices = dict(db.execute('SELECT spid,current_price FROM prices'))
    values = {spid: policy.fair_price(raw) for spid, raw in rows.items()}
    check(set(prices) <= values.keys(), 'Every currently priced card has a valid ability price')
    check(all(type(v) is int and 100 <= v <= MAX_PRICE for v in values.values()), 'All-card prices finite, integer, local EP and Number-safe')
    check(sum(v == 1 for v in values.values()) == 0, 'No one-EP denomination collapse')
    check(len(set(values.values())) > 10000, 'Meaningful full-population price differentiation')
    rng = random.Random(7831)
    samples = rng.sample(list(rows.values()), min(1200, len(rows)))
    ability_fields = [f for f in policy.fields if f not in ('height', 'preferredposition1', 'weakfootabilitytypecode', 'skillmoves')]
    changes = 0
    for raw in samples:
        original = policy.fair_price(raw)
        for field in ability_fields:
            if raw[field] >= 255:
                continue
            changed = dict(raw)
            changed[field] += 1
            assert policy.fair_price(changed) >= original, (raw['spid'], field)
            changes += 1
        for field, upper in [('weakfootabilitytypecode', 5), ('skillmoves', 5)]:
            if raw[field] < upper:
                changed = dict(raw)
                changed[field] += 1
                assert policy.fair_price(changed) >= original, (raw['spid'], field)
        relabeled = dict(raw, spid=123, playerid=456, overallrating=1, full='arbitrary', trait1=0, trait2=0)
        assert policy.fair_price(relabeled) == original
    check(True, 'Individual ability/foot/skill increases never lower price; identifiers and unmeasured trait codes cannot distort it')
    for raw in rows.values():
        increased = dict(raw)
        for field in ability_fields:
            increased[field] = min(255, increased[field] + 1)
        assert policy.fair_price(increased) >= values[raw['spid']]
    check(True, 'Full-population simultaneous ability increase is nondecreasing')
    pair_results = []
    for strong, weak in [(9138726, 47138726), (9119152, 47119152), (9045595, 47045595)]:
        check(values[strong] > values[weak], 'Reported same-player inversion repaired: ' + str(strong))
        pair_results.append(dict(strong_spid=strong, weak_spid=weak, old_prices=[prices[strong], prices[weak]], fair_prices=[values[strong], values[weak]]))
    raw = dict(rows[47138726]); before = policy.fair_price(raw); raw['positioning'] = 66
    check(policy.fair_price(raw) >= before, 'Isolated Lescott positioning counterexample no longer decreases price')
    for field, bad in [('agility', float('nan')), ('strength', -4), ('skillmoves', 8), ('preferredposition1', 28), ('weakfootabilitytypecode', 0), ('height', True)]:
        invalid = dict(raw); invalid[field] = bad
        try:
            policy.fair_price(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid input accepted: ' + field)
    check(True, 'Invalid or nonfinite profiles are refused')
    check(policy.market_factor(1, 100) == .9 and policy.market_factor(100, 1) == 1.1 and policy.market_factor(1, 1) == 1, 'Demand movement preserved within explicit bounds')
    # Actual production market classes, using only a temporary price DB and an
    # immutable read-only connection to ability data. No server is imported/run.
    with tempfile.TemporaryDirectory(prefix='ability-regression-', dir=HERE) as temp:
        root = Path(temp)
        db = sqlite3.connect(root / 'prices.sqlite')
        db.executescript('CREATE TABLE metadata(key TEXT,value TEXT); CREATE TABLE seeds(spid INTEGER,initial_price INTEGER); CREATE TABLE prices(spid INTEGER,basis_price REAL); CREATE TABLE price_events(event_id TEXT);')
        db.executemany('INSERT INTO metadata VALUES(?,?)', [('schema', '1'), ('price_region', 'kr'), ('model_sha256', 'unchanged-test-history'), ('seed_revision', 'history-fixture')])
        fixture = [(s, prices[s]) for s in [9138726, 47138726, 9119152, 47119152, 9045595, 47045595]]
        db.executemany('INSERT INTO seeds VALUES(?,?)', fixture)
        db.executemany('INSERT INTO prices VALUES(?,?)', fixture)
        db.commit(); db.close()
        host = SimpleNamespace(**{k: v for k, v in native.items() if k != '__builtins__'},
            HERE=root, MARKET_PRICE_DB_PATH=root / 'prices.sqlite', closing=closing,
            _db=lambda: sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro', uri=True),
            player_value_price=lambda spid, grade=1: 999, on_market=lambda spid: spid in dict(fixture),
            card_ovr=lambda spid: int(policy.explain(rows[spid])['native_role_rating']),
            STATE_LOCK=threading.RLock(), _json=lambda value: value)
        market = Market(host)
        st = {'market_simulation': {'quotes': {}, 'seed': 'fixture', 'books': {}, 'legacy_supply': [], 'sales': []},
              'coaches': [{'name': 'fixture'}], 'teams': {'0': {'players': [{'_id': 'asset', 'spid': 9138726, 'grade': 8, 'experience': 123}]}},
              'balance': 123456, 'offers': [{'price': 316, 'grade': 1, 'spid': 47138726, '_market_owner': 'fixture'}]}
        host._state = lambda: st
        original = copy.deepcopy(st)
        for spid, _ in fixture:
            check(market.quote(spid, 1, st) == values[spid], 'Market +1 quote matches ability price: ' + str(spid))
            graded = [market.exchange.reference_value(spid, grade, st) for grade in range(21)]
            assert graded[0] == 0 and graded[1] == values[spid]
            assert all(a <= b <= MAX_PRICE < 2**53 for a, b in zip(graded, graded[1:]))
            assert graded[2] == values[spid] * 265 // 100
            assert graded[10] == values[spid] * 6290
        check(True, 'Exact existing grade investment factors and +0..+20 safety')
        check(st == original, 'Valuation leaves managers, balances, card instances, XP, offers and history untouched')
        # Stored/queued trade movement is interpreted in its original units.
        st['market_simulation']['quotes']['9138726'] = {'basis_price': prices[9138726] * 2}
        check(market.quote(9138726, 1, st) == round(values[9138726] * 1.1), 'Pending state basis is applied once with demand cap')
        old_offer = {'spid': 9138726, 'grade': 1, 'price': 123, 'count': 4}
        epoch = 100
        st['market_simulation']['books']['9138726'] = {'epoch': epoch, 'rows': [old_offer], 'supply_version': 3}
        book = market.book(st, 9138726, epoch * 900 + 1)
        check(book['rows'] == [old_offer], 'Existing NPC quote and quantity retained until normal expiry; no refill')
        # A fresh book must use corrected values and the unchanged stock rules.
        new_book = market.book(st, 9138726, (epoch + 1) * 900 + 1)
        check(next(r for r in new_book['rows'] if r['grade'] == 1)['price'] == market.quote(9138726, 1, st), 'Normal next stock cycle uses corrected quote')
        check(next(r for r in new_book['rows'] if r['grade'] == 1)['count'] == 12, 'Stock allocation is not increased by price repair')
        market.exchange.price_store.close()
    report = dict(status='PASS', priced_cards=len(prices), ability_profiles=len(rows),
                  single_ability_checks=changes, checks=checks, repaired_pairs=pair_results,
                  old_one_ep_cards=sum(p == 1 for p in prices.values()), new_one_ep_cards=sum(p == 1 for p in values.values()),
                  fair_price_range=[min(values.values()), max(values.values())],
                  payload_hashes=json.loads((HERE / 'payload-hashes.json').read_text('utf8')),
                  native_verified=False, formal_activated=False)
    (HERE / 'regression.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
