"""Exercise official match builders in memory; never invoke real save operations."""
import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parent
SERVER = pathlib.Path(r'D:\FO3ID\server')
sys.dont_write_bytecode = True
sys.path.insert(0, str(SERVER))
sys.argv = [sys.argv[0]]
os.environ['FO3_MAX_GRADE'] = '20'
os.environ['FO3_LANGUAGE'] = 'chi'
import http_config as hc

spec = importlib.util.spec_from_file_location('ai_progression_under_test', ROOT/'ai_opponent_progression.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


def main():
    watched = [SERVER/'gamedata/state.json', SERVER/'gamedata/shop.json']
    before_files = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    original = hc.match_side.__wrapped__ if getattr(hc, '_ai_opponent_progression_installed', False) else hc.match_side
    # The host save boundary is blocked before creating any synthetic manager.
    def reject_save(*args, **kwargs):
        raise AssertionError('A read-only match builder tried to persist data')
    hc._save = reject_save
    patch.install(hc)
    wrapped = hc.match_side
    patch.install(hc)
    assert hc.match_side is wrapped
    cases = []
    raws = {}
    for tid in (241, 243, 1, 9):
        raw = hc.roster_team(tid)
        raws[tid] = raw
        prior = copy.deepcopy(raw)
        expected = original(copy.deepcopy(raw), tid)
        ai = hc.match_side(raw, tid)
        assert raw == prior, 'Roster/cached input mutated'
        assert len(ai['team']['players']) == len(raw['players'])
        assert all(p['grade'] == 10 and p['levelinfo']['level'] == 30 and p['levelinfo']['exp'] == 0
                   for p in ai['team']['players'])
        assert ai['ready'] and not ai['players']
        assert ai['tactics'] == expected['tactics'] and ai['kit'] == expected['kit']
        assert ai['team']['squad'] == expected['team']['squad']
        assert ai['team']['teamcolors'] == expected['team']['teamcolors']
        assert {p['spid'] for p in ai['team']['players']} == {p['spid'] for p in expected['team']['players']}
        # User-bearing sides must have the exact old serialization, even when the
        # same club/player identity is used on both sides.
        user = {'id': 'synthetic-only', 'name': 'in-memory', 'levelinfo': {'level': 1}}
        mine = copy.deepcopy(raw)
        for i, p in enumerate(mine['players']):
            p['grade'] = i % 11
            p['levelinfo'] = {'level': i % 30 + 1, 'exp': i}
        original_mine = copy.deepcopy(mine)
        assert hc.match_side(mine, tid, user) == original(copy.deepcopy(mine), tid, user)
        assert mine == original_mine
        cases.append(dict(case='all_players_and_user_isolation', teamid=tid,
                          players=len(ai['team']['players']), baseline_summary=expected['team']['summary'],
                          boosted_summary=ai['team']['summary']))

    raw = copy.deepcopy(raws[241])
    # Retain existing identity/contract/stamina and locked flags in the source;
    # forcing levels is confined to the detached computer side.
    raw['players'][0].update(grade=20, levelinfo={'level': 12, 'exp': 350}, locked=True)
    prior = copy.deepcopy(raw)
    assert all(p['grade'] == 10 and p['levelinfo']['level'] == 30
               for p in hc.match_side(raw, 241)['team']['players'])
    assert raw == prior
    cases.append(dict(case='existing_high_grade_and_xp_detached'))

    # Build every real league difficulty without creating/saving a match.
    state = {'league2': {'difficultyselect': 10, 'leagueid': 53},
             'teams': {'0': copy.deepcopy(raws[241])}}
    coach = {'id': 'memory', 'name': 'memory', 'levelinfo': {'level': 1}, 'teamid': 241}
    hc.coach_me = lambda st, slot: coach
    hc._default_slot = lambda st: 0
    hc._tactics = lambda st: (None, [hc.default_tactic(0)])
    hc.roster_team = lambda tid: raws[tid]
    for difficulty in range(10, 25):
        state['league2']['difficultyselect'] = difficulty
        for playtype in ('play', 'mgr'):
            request = {'home': 243, 'away': 241, 'round': 0}
            hc.match_side = original
            baseline = hc.league_match_body(copy.deepcopy(state), request, playtype)
            hc.match_side = wrapped
            prior = copy.deepcopy(state)
            result = hc.league_match_body(state, request, playtype)
            assert state == prior
            assert result['gamesettings'] == baseline['gamesettings']
            assert result['gamesettings']['difficulty'] == difficulty
            assert result['side']['left'] == baseline['side']['left']
            assert all(p['grade'] == 10 and p['levelinfo']['level'] == 30
                       for p in result['side']['right']['team']['players'])
            cases.append(dict(case='league_match', difficulty=difficulty, playtype=playtype))

    # Run the actual cup handler with a purely in-memory save destination.
    cup = {'difficulty': 0, 'phases': [{'system': 'knock-out'}], 'current': {'phase': 0}}
    state['cups'] = {'synthetic-cup': cup}
    hc._state = lambda: state
    hc.cup_my_pair = lambda cup: ({'teams': [{'teamid': 241}, {'teamid': 243}]}, {'homeidx': 0, 'awayidx': 1})
    saved = []
    hc._save = lambda st: saved.append(copy.deepcopy(st))
    for difficulty in range(5):
        cup['difficulty'] = difficulty
        result = json.loads(hc.ep_cup_match('synthetic-cup', '', b'')[1])
        match = state['match']
        assert result['result']
        assert match['gamesettings']['difficulty'] == difficulty
        assert match['gamesettings']['drawMode'] == 2
        assert match['side']['left']['team']['players'] == original(raws[241], 241, coach)['team']['players']
        assert all(p['grade'] == 10 and p['levelinfo']['level'] == 30
                   for p in match['side']['right']['team']['players'])
        cases.append(dict(case='cup_match', difficulty=difficulty))
    assert len(saved) == 5
    rules = json.loads(hc.ENDPOINTS['/info/ai-opponent-rules']('', b'')[1])
    assert rules['grade'] == 10 and rules['level'] == 30
    after_files = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    report = dict(status='PASS', cases=cases, case_count=len(cases), rules=rules,
                  source_sha256=hashlib.sha256((ROOT/'ai_opponent_progression.py').read_bytes()).hexdigest(),
                  official_state_shop_written=False, gui_used=False,
                  native_match_verified=False, live_observation_before=before_files,
                  live_observation_after=after_files,
                  concurrent_live_changes_preserved=before_files != after_files)
    (ROOT/'tests.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(status='PASS', cases=len(cases))))


if __name__ == '__main__':
    main()
