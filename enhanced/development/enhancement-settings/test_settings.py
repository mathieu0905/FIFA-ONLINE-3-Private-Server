"""Run production setting module and actual enhancement handlers with temporary data only."""
import ast
import copy
import hashlib
import http.client
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
from unittest.mock import patch

SERVER = Path(r'D:\FO3ID\server')
sys.path.insert(0, str(SERVER))
import enhancement_settings
import enhancement20
import admin

source = ast.parse((SERVER / 'http_config.py').read_text(encoding='utf-8-sig'))
functions = {'enhance_pair', 'enhance_grade', 'enhance_rate', 'enhance25_rate',
             'ep_enhance_preview', 'ep_enhance25_preview', 'ep_enhance', 'ep_enhance25',
             'enhance_es', 'enhance25_result'}
code = compile(ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in functions], type_ignores=[]), '<production-enhancement-handlers>', 'exec')


def make_hc(folder):
    hc = types.ModuleType('settings_test_hc')
    hc.HERE = str(folder)
    hc.MAX_GRADE = 20
    hc.GRADE_BOOST = tuple(range(21))
    hc.ENHANCE_RATE = (1., 1., .81, .64, .50, .26, .15, .07, .04, .02) + tuple(.015 * .8 ** (g - 10) for g in range(10, 20)) + (0.,)
    hc.add_player = lambda *a, **k: None
    hc.ep_transfer_purchase = hc.ep_transfer_price = lambda *a: None
    hc.ROUTES = []
    hc.STATE_LOCK = threading.RLock()
    enhancement20.install(hc)
    exec(code, hc.__dict__)
    hc.grade_of = lambda p: p['grade']
    hc.iid = lambda p: p['id']
    hc._default_slot = lambda st: 0
    hc._json = lambda obj: ('application/json', json.dumps(obj).encode())
    hc.player_value_price = lambda *args: 100
    hc.player_levelinfo = lambda p: {'level': 1, 'exp': 0}
    hc.enhance_cost = lambda p: 1000
    hc.boost_stack = lambda *args: None
    hc.ENHANCE_EVENT = {'eventid': 1001}
    hc.EVENT_BOOST = hc.ES_BOOST = .10
    hc.ES_RESTORE = 3
    hc.ITEMS = {52: (None, None, None, {'boost': .15})}
    hc.ENHANCE_DROP_FROM = 5
    hc.random = types.SimpleNamespace(random=lambda: .5)
    hc._save = lambda st: None  # in-memory fixtures, never production _save
    hc.add_ep = lambda *a: None
    hc.add_es = lambda *a: None
    hc.coach_me = lambda *a: {'money': {'ep': 999999}}
    hc.coach_me_resources = lambda *a: {}
    hc.merge_into = lambda team, pa, pb: team['players'].remove(pb)
    return hc


def body(response):
    return json.loads(response[1])


def expect_failure(fn):
    try:
        fn()
    except (ValueError, OSError):
        return
    raise AssertionError('expected rejection')


def fingerprint():
    return {name: hashlib.sha256((SERVER / 'gamedata' / name).read_bytes()).hexdigest()
            for name in ('state.json', 'shop.json')}


before = fingerprint()
checks = []
with tempfile.TemporaryDirectory(prefix='fo3-enhancement-') as folder:
    hc = make_hc(folder)
    defaults = hc.ENHANCE_RATE
    old_rates = {(g, m): hc.enhance_rate({'grade': g}, {'grade': m})
                 for g in range(1, 20) for m in range(21)}
    enhancement_settings.install(hc)
    assert defaults == hc.ENHANCE_RATE
    assert not (Path(folder) / 'gamedata' / 'enhancement_rates.json').exists()
    assert all(hc.enhance_rate({'grade': g}, {'grade': m}) == r for (g, m), r in old_rates.items())
    checks.append('399 default/material combinations unchanged; no initial config write')
    get = hc.enhancement_settings_get
    put = hc.enhancement_settings_set
    original = get()
    rates = {g: float(g) for g in original['rates']}
    changed = put({'rates': rates, 'revision': original['revision']})
    assert all(abs(hc.ENHANCE_RATE[int(g)] - rates[g] / 100) < 1e-12 for g in rates)
    assert hc.enhance_rate({'grade': 6}, {'grade': 1}) == .06
    assert hc.enhance_rate({'grade': 6}, {'grade': 6}) == .09
    assert abs(hc.enhance25_rate({'grade': 6}, {'grade': 1}, True, {'itemid': 52}, '1001') - .41) < 1e-12
    assert hc.enhance_rate({'grade': 19}, {'grade': 0}) == 1
    checks.append('all 19 grades apply immediately; material/item/point/event stacking preserved')
    restarted = make_hc(folder)
    enhancement_settings.install(restarted)
    assert restarted.enhancement_settings_get() == changed
    checks.append('settings persist on fresh initialization')
    path = Path(folder) / 'gamedata' / 'enhancement_rates.json'
    saved = path.read_bytes()
    active = hc.ENHANCE_RATE
    for bad in (None, [], {}, {**rates, '20': 1}, {**rates, '1': True},
                {**rates, '1': -1}, {**rates, '1': 101}, {**rates, '1': '50'},
                {**rates, '1': float('nan')}, {**rates, '1': float('inf')}):
        expect_failure(lambda: put({'rates': bad, 'revision': changed['revision']}))
        assert path.read_bytes() == saved and hc.ENHANCE_RATE == active
    expect_failure(lambda: put({'rates': rates, 'revision': original['revision']}))
    with patch.object(enhancement_settings.os, 'replace', side_effect=OSError('simulated disk failure')):
        expect_failure(lambda: put({'rates': {**rates, '1': 90}, 'revision': changed['revision']}))
    assert path.read_bytes() == saved and hc.ENHANCE_RATE == active
    assert not list(path.parent.glob('*.tmp'))
    checks.append('invalid numbers/shape, stale saves and disk failures leave file and active probabilities unchanged')
    for chance, success in ((0, False), (100, True)):
        put({'rates': {**rates, '6': chance}, 'revision': get()['revision']})
        for version in (1, 25):
            fixture = {'teams': {'0': {'players': [{'id': 'a', 'spid': 1, 'grade': 6}, {'id': 'b', 'spid': 1, 'grade': 1}]}}}
            hc._state = lambda: fixture
            preview = (hc.ep_enhance_preview('a', 'b', '', b'') if version == 1 else
                       hc.ep_enhance25_preview('a', 'b', '0', '-1', '-1', '', b''))
            assert body(preview)['probability'] == chance
            result = (hc.ep_enhance('a', 'b', None, None, '', b'') if version == 1 else
                      hc.ep_enhance25('a', 'b', '0', '-1', '-1', '', b''))
            assert body(result)['success'] is success
            assert body(result)['grade'] == (7 if success else 5)
    checks.append('production v1/v2.5 previews and actual roll handlers honor saved 0%/100% using in-memory cards')
    admin.hc = hc
    enhancement_settings.register_admin(hc, admin)
    server = admin.http.server.ThreadingHTTPServer(('127.0.0.1', 0), admin.Admin)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def request(method, route, payload=None, header=False):
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        conn.request(method, route, json.dumps(payload) if payload is not None else None,
                     {'X-FO3-Admin': '1'} if header else {})
        response = conn.getresponse()
        result = response.status, response.read()
        conn.close()
        return result
    try:
        status, raw = request('GET', '/api/enhancement')
        assert status == 200 and len(json.loads(raw)['rates']) == 19
        payload = {'rates': rates, 'revision': get()['revision']}
        assert request('GET', '/api/enhancement_set')[0] == 403
        assert request('POST', '/api/enhancement_set', payload)[0] == 403
        status, raw = request('POST', '/api/enhancement_set', payload, True)
        assert status == 200 and json.loads(raw)['rates'] == rates
        assert json.loads(request('POST', '/api/enhancement_set', payload, True)[1]).get('error')
    finally:
        server.shutdown()
        server.server_close()
    checks.append('production admin HTTP GET/read, POST/header guard, successful save and stale-write rejection')
after = fingerprint()
result = {'status': 'PASS', 'checks': checks, 'production_assets_before': before,
          'production_assets_after': after, 'assets_unchanged_during_test': before == after}
Path(__file__).with_name('test-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
