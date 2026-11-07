"""Exercise actual installed pack definitions against detached disposable state only."""
from pathlib import Path
import copy, hashlib, importlib.util, json, os, sys, threading

ROOT = Path(__file__).resolve().parent
SERVER = Path(r'D:\FO3ID\server')
sys.path.insert(0, str(SERVER))
sys.dont_write_bytecode = True
os.environ.update(FO3_MAX_GRADE='20', FO3_LANGUAGE='chi')

def guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)) and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        p = Path(os.fsdecode(args[0])).resolve()
        if p.is_relative_to(SERVER) or p.is_relative_to(Path(r'D:\FO3ID\32795')):
            raise RuntimeError('Test attempted formal write: ' + str(p))

sys.addaudithook(guard)
import market_price_store, all_item_icons
market_price_store.MarketPriceStore.flush = lambda self, events: 0
all_item_icons.install = lambda host: None
import pack_value
# Shop expected-value pricing scans the entire database; this test does not change prices.
# Keep actual per-drawn-card pricing intact and stub only unrelated shop quote calculation.
pack_value.ValueModel.value = lambda self, itemid, trail=(): 1.0
pack_value.ValueModel.quote = lambda self, itemid, kind='ordinary': 1
import http_config as h
print('Installed host imported; beginning isolated pack regressions', flush=True)
from hot_update_runtime import compile_handlers, RequestHost

handlers = compile_handlers((ROOT / 'bulk_business.py').read_bytes(), 'bulk_business.py',
                            [{'path': '/item/{item_id}/use', 'function': 'open_pack'}], allow_templates=True)
handler = handlers['/item/{item_id}/use']
base = copy.deepcopy(h._state())
slot = h._default_slot(base)
base_coach = h.my_coach(base)
base_coach['items'] = []
base_coach.pop('bulk_player_pack_receipts', None)
base_coach['_admin_generation'] = 'disposable-bulk-regression'
base['teams'][str(slot)]['players'] = []
state = copy.deepcopy(base)
saved_count = 0

def read():
    return copy.deepcopy(state)

def save(value):
    global state, saved_count
    state = copy.deepcopy(value)
    saved_count += 1

h._state, h._save = read, save
original_resources = h.coach_me_resources
h.coach_me_resources = lambda st, sl: [{'uri': '/coach/me', 'body': {'items': h.coach_items(st, sl)}}]
checks = []

def reset(itemid, count=3, capacity=100):
    global state, saved_count
    state = copy.deepcopy(base)
    saved_count = 0
    h.MAX_PLAYERS = capacity
    h.inventory_add(h.my_coach(state), itemid, count)
    return str(next(row for row in h.coach_items(state, slot) if row['itemid'] == itemid)['_id'])

def call(token, request):
    return json.loads(handler(RequestHost(h, {'item_id': token}), '', json.dumps(request).encode())[1])

def request(count=3, key='bulk-regression-0001'):
    return dict(bulk=True, requestId=key, expectedRemains=count)

risk_ids = [int(i) for section in ('risk_packs', 'strength_packs') for i, data in h.product_packs.get(section, {}).items()
            if data.get('mode') != 'choice' and h.item_def(int(i))['category'] == 'PLAYERPACK']
catalogue_ids = [int(i) for i, data in h.pack_catalogue['items'].items() if data['mode'] == 'random']
cadence_ids = [i for i in h.pack_cadence.items if h.item_def(i)['category'] == 'PLAYERPACK']
ordinary_ids = [i for i in h.PACKS if i not in set(risk_ids + catalogue_ids + cadence_ids)
                and h.item_def(i)['category'] == 'PLAYERPACK' and not h.item_def(i).get('draft')]
all_ids = list(dict.fromkeys(risk_ids + catalogue_ids + cadence_ids + ordinary_ids))
print('Random SKUs: '+str(len(all_ids)), flush=True)
for index, itemid in enumerate(all_ids):
    if index % 20 == 0:
        print('Testing random SKU '+str(index+1)+'/'+str(len(all_ids)), flush=True)
    token = reset(itemid)
    out = call(token, request())
    assert out.get('result') and out['opened'] == 3 and len(out['players']) == 3, (itemid, out)
    assert out['remaining'] == 0 and saved_count == 1
    assert len(state['teams'][str(slot)]['players']) == 3
    pool = dict(h.pack_pool(itemid))
    grades = {g for g, w in h.pack_grades(itemid) if w > 0}
    assert all(p['spid'] in pool and p['grade'] in grades for p in out['players']), itemid
    assert len({p['_id'] for p in out['players']}) == 3
    replay = call(token, request())
    assert replay['replayed'] and replay['players'] == out['players'] and saved_count == 1
checks.append({'all_random_skus_open_and_replay': len(all_ids), 'risk': len(risk_ids),
               'catalogue': len(catalogue_ids), 'cadence': len(cadence_ids), 'ordinary': len(ordinary_ids)})

sample = risk_ids[0]
token = reset(sample, 7, 2)
out = call(token, request(7))
assert out['opened'] == 2 and out['remaining'] == 5 and out['limitedByCapacity']
assert sum(i['remains'] for i in h.my_coach(state)['items'] if i['itemid'] == sample) == 5
new_token = str(next(r for r in out['items'] if r['itemid'] == sample)['_id'])
assert new_token != token
snapshot = copy.deepcopy(state)
full = call(new_token, request(5, 'bulk-regression-full'))
assert not full['result'] and state == snapshot and saved_count == 1
h.MAX_PLAYERS = 100
out2 = call(new_token, request(5, 'bulk-regression-next'))
assert out2['opened'] == 5 and out2['remaining'] == 0 and len(state['teams'][str(slot)]['players']) == 7
checks.append('partial_capacity_full_capacity_and_remaining_next_open')

token = reset(sample)
snapshot = copy.deepcopy(state)
for req in [request(4), dict(bulk=1, requestId='bulk-regression-0001', expectedRemains=3),
            request(3, 'short'), dict(request(), spids=[1]), dict(request(), expectedRemains=True)]:
    assert not call(token, req)['result']
    assert state == snapshot and saved_count == 0
assert not call(token + 'tampered', request())['result']
checks.append('tamper_stale_stock_and_malformed_request_no_mutation')

token = reset(sample)
other = next(i for i in risk_ids if i != sample)
h.inventory_add(h.my_coach(state), other, 11)
h.my_coach(state)['depot'] = [{'_id': 'depot-test', 'itemid': sample, 'remains': 9}]
before = copy.deepcopy(state)
call(token, request())
assert next(i for i in h.my_coach(state)['items'] if i['itemid'] == other)['remains'] == 11
assert h.my_coach(state)['depot'] == h.my_coach(before)['depot']
for key, value in h.my_coach(before).items():
    if key not in ('items', 'bulk_player_pack_receipts'):
        assert h.my_coach(state)[key] == value, key
checks.append('only_same_sku_inventory_consumed_wallet_other_assets_preserved')

choice_ids = [int(i) for i in h.PACKS if h.item_def(i)['category'] == 'DRAFTPACK']
for itemid in choice_ids:
    token = reset(itemid)
    before = copy.deepcopy(state)
    assert not call(token, request())['result'], itemid
    assert state == before and saved_count == 0
checks.append({'all_choices_reject_bulk': len(choice_ids)})

# Confirm normal requests still pass through the native engine with its receipt rules.
token = reset(sample)
single = call(token, {})
assert single['result'] and 'player' in single and 'players' not in single
assert sum(i['remains'] for i in h.my_coach(state)['items'] if i['itemid'] == sample) == 2
assert call(token, {})['replayed'] and saved_count == 1
checks.append('single_native_use_and_native_receipt_unchanged')

token = reset(sample)
before = copy.deepcopy(state)
def fail_save(value):
    raise OSError('injected precommit failure')
h._save = fail_save
try:
    call(token, request())
    raise AssertionError('Expected save failure')
except OSError:
    pass
assert state == before
h._save = save
out = call(token, request())
assert out['opened'] == 3 and saved_count == 1
checks.append('precommit_failure_no_partial_write_retry_once')

token = reset(sample)
outputs = []
threads = [threading.Thread(target=lambda: outputs.append(call(token, request()))) for _ in range(8)]
for thread in threads: thread.start()
for thread in threads: thread.join()
assert len(outputs) == 8 and all(out['result'] for out in outputs)
assert sum(bool(out.get('replayed')) for out in outputs) == 7 and saved_count == 1
assert len(state['teams'][str(slot)]['players']) == 3
assert not call(token, request(4))['result']
checks.append('eight_concurrent_retries_one_commit_conflicting_replay_rejected')

token = reset(sample)
h.my_coach(state)['items'].append({'_id': 'second-stack', 'itemid': sample, 'remains': 4, 'product_open_seq': 0})
out = call(token, request(7))
assert out['opened'] == 7 and out['remaining'] == 0 and saved_count == 1
checks.append('multiple_stacks_same_sku_one_transaction')

# Identical RNG input must produce the same cards and cadence bookkeeping as native single use.
for itemid in list(dict.fromkeys(risk_ids[:2]+catalogue_ids[:2]+cadence_ids+ordinary_ids[:2])):
    token = reset(itemid, 3)
    if itemid in cadence_ids:
        data = h.pack_cadence.items[itemid]
        ledger = h.pack_cadence.ledger(h.my_coach(state))
        if data.get('pity'):
            ledger['pity'][data['pity']['key']] = data['pity']['after']-1
        ledger['marks'] = h.pack_cadence.config['mark_exchange']['cost']-1
    start = copy.deepcopy(state)
    h.random.seed(478932)
    singles = []
    for unused in range(3):
        uid = str(next(r for r in h.coach_items(state,slot) if r['itemid']==itemid)['_id'])
        one = call(uid,{})
        assert one['result'], (itemid, one)
        singles.append((one['player']['spid'],one['player']['grade']))
    native = copy.deepcopy(state)
    state = copy.deepcopy(start)
    saved_count = 0
    h.random.seed(478932)
    out = call(token,request())
    assert [(p['spid'],p['grade']) for p in out['players']] == singles, itemid
    assert h.my_coach(state).get('pack_cadence') == h.my_coach(native).get('pack_cadence'), itemid
    assert sorted((r['itemid'],r['remains']) for r in h.my_coach(state)['items']) == sorted((r['itemid'],r['remains']) for r in h.my_coach(native)['items']), itemid
checks.append('seeded_native_draw_equivalence_including_forced_pity_and_mark_exchange')

token = reset(sample)
h.coach_me_resources = original_resources
out = call(token, request())
assert out['result'] and isinstance(out['resources'],list) and out['resources']
assert out['playerCount'] == 3 and out['opened'] == len(out['players'])
checks.append('actual_native_resources_serialization')

report = dict(status='PASS', checks=checks, real_state_written=False, formal_files_written=False,
              unrelated_shop_expected_value_calculation_stubbed=True,
              native_gui_verified=False, source_sha256=hashlib.sha256((ROOT/'bulk_business.py').read_bytes()).hexdigest())
(ROOT / 'server-tests.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps(report, ensure_ascii=False))
