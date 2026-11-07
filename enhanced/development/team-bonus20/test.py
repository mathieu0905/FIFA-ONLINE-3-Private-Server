"""Execute exact proposed functions with synthetic cards and no persistence capability."""
from pathlib import Path
import ast
import copy
import functools
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from prepare import ROOT, SERVER, transform
sys.dont_write_bytecode = True

class Database:
    rows = [(84000000+i, i) for i in range(1, 13)] + [(93000000+i, 100+i) for i in range(1, 13)]
    def execute(self, query):
        assert query.startswith('SELECT '), 'Write query prohibited'
        return self
    def fetchall(self): return self.rows
    def close(self): pass

def functions(source, real=False):
    tree = ast.parse(source)
    start = source.index('TC_CLUB, TC_NATION, TC_SEASON =')
    wanted = {'_tc_groups','tc_seasons','tc_season_of','_in','_S','_CLUB','_PIDS',
              '_tc_boost','_tc_special_groups','tc_special_sets','tc_colors','ep_teamcolor',
              '_tc_tier','tc_static','active_teamcolors','xi_ratings'}
    nodes = []
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name in wanted: nodes.append(n)
        elif isinstance(n,(ast.Assign,ast.AugAssign)):
            text = ast.get_source_segment(source,n)
            if (start <= source.find(text) < source.index('def ep_teamcolor', start) and
                    (text.startswith('TC_') or text.startswith('_SPECIAL') or text.startswith('_TC_OVR'))): nodes.append(n)
            elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FA_SEASONS' for t in n.targets): nodes.append(n)
    # FA_SEASONS is only referenced when functions run, not during declarations.
    ns = dict(functools=functools, closing=closing, POSOVR='test_rating', _db=Database,
              on_market=lambda s:True, POS_SUB=28, iid=lambda p:str(p['id']),
              grade_of=lambda p:p.get('grade',1), player_levelinfo=lambda p:p['levelinfo'],
              STAT_COLS=['speed','strength'], GRADE_BOOST=tuple(range(21)),
              POS_ROLE=['GK']*28, ROLE_WEIGHTS={'GK':{'speed':50,'strength':50}},
              _default_slot=lambda st:0, _json=lambda obj:obj)
    if real:
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ROLE_WEIGHTS','POS_ROLE','POSOVR') for t in node.targets):
                exec(compile(ast.Module(body=[node],type_ignores=[]),'real-rating-constants','exec'),ns)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'extracted-team-color-functions','exec'),ns)
    return ns

def team(n, grade=10):
    players = [dict(id=str(i), spid=(84000000+i if i<=n else 93000100+i), grade=grade,
                    levelinfo={'level':1,'exp':0}) for i in range(1,12)]
    return dict(players=players, squad={'positions':[dict(id=p['id'],spid=p['spid'],pos=i) for i,p in enumerate(players)]})

def bind(ns, tm):
    cards = {p['spid']:(int(p['id']),241,45) for p in tm['players']}
    ns['tc_static'] = lambda:(cards,{})
    ns['card_stats'] = lambda ids:{s:{'speed':100,'strength':100} for s in ids}
    ns['_state'] = lambda:{'teams':{'0':tm}}

def rated(ns, tm):
    bind(ns,tm)
    tm = copy.deepcopy(tm)
    tm['teamcolors'] = ns['active_teamcolors'](tm)
    return ns['xi_ratings'](tm), tm['teamcolors']

def main():
    original = ((ROOT/'baseline-http.py') if '--installed' in sys.argv else (SERVER/'http_config.py')).read_text('utf8')
    if '--installed' in sys.argv:
        assert (SERVER/'http_config.py').read_text('utf8')==transform(original), 'Installed source differs from reviewed delta'
    before, after = functions(original), functions(transform(original))
    cases = []
    def passed(name): cases.append(name)
    old_colors = before['tc_colors'](); new_colors = after['tc_colors']()
    by_id = {c['teamcolorid']:c for c in new_colors}
    assert len(by_id)==len(new_colors)
    assert all(by_id[c['teamcolorid']]==c for c in old_colors)
    passed('All existing color definitions and thresholds unchanged')
    assert after['TC_GRADE'][:len(before['TC_GRADE'])]==before['TC_GRADE']
    passed('Existing reinforcement rules unchanged')
    for n in range(12):
        tm=team(n); snapshot=copy.deepcopy(tm)
        old,_=rated(before,tm); new,active=rated(after,tm)
        extra=0 if n<3 else 2 if n<=5 else 3 if n<=8 else 4 if n<=10 else 5
        assert tm==snapshot
        for p in tm['players']:
            assert new[p['id']]-old[p['id']]==(extra if p['spid']//1000000==84 else 0)
        matches=[c for c in active if c['teamcolorid']==60084]
        assert bool(matches)==bool(extra)
        if matches: assert isinstance(matches[0]['teamid'],str)
        passed(f'Moments {n} starters: exact independent +{extra}, other players untouched')
    for grade in range(1,21):
        tm=team(11,grade); old,_=rated(before,tm); new,_=rated(after,tm)
        grade_delta=max(0,grade-10)
        assert all(new[k]-old[k]==5+grade_delta for k in old)
        passed(f'All XI +{grade}: highest grade only, moments +5 stacks once')
    for grade in range(11,21):
        tm=team(0,grade); old,_=rated(before,tm); new,_=rated(after,tm)
        assert all(new[k]-old[k]==grade-10 for k in old)
        # One starter below threshold selects the previous eligible full-XI tier.
        tm['players'][0]['grade']=grade-1
        mixed,_=rated(after,tm)
        lower,_=rated(after,team(0,grade-1))
        # Compare team-color contribution after removing synthetic intrinsic grade.
        assert all(mixed[p['id']]-p['grade']==lower[p['id']]-(grade-1) for p in tm['players'])
        passed(f'+{grade}: full XI required; mixed XI falls to next satisfied tier')
    tm=team(2)
    tm['players'].append(dict(id='12',spid=84000012,grade=20,levelinfo={'level':1,'exp':0}))
    tm['squad']['positions'].append(dict(id='12',spid=84000012,pos=28))
    _,active=rated(after,tm)
    assert not any(c['teamcolorid']==60084 for c in active)
    passed('Bench moments do not contribute to starting XI count')
    tm=team(3)
    tm['players'][2]['spid']=tm['players'][1]['spid']
    tm['squad']['positions'][2]['spid']=tm['players'][1]['spid']
    _,active=rated(after,tm)
    assert not any(c['teamcolorid']==60084 for c in active)
    passed('Repeated player identity does not count twice')
    tm=team(11)
    bind(after,tm)
    data=after['ep_teamcolor']('',b'')
    assert data['teamColorSpecials']['60084']==sorted(p['spid'] for p in tm['players'])
    assert {c['teamid'] for c in data['teamColors'] if c['type'] in ('special','feature')}==set(data['teamColorSpecials'])
    passed('Native static response includes string-keyed feature membership')
    assert by_id[60084]['type']=='feature'
    # Real current player identities are read through SQLite read-only mode.
    def readonly_db():
        return sqlite3.connect((SERVER/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
    real_before,real_after=functions(original,real=True),functions(transform(original),real=True)
    for ns in (real_before,real_after):
        ns['_db']=readonly_db
    with closing(readonly_db()) as db:
        actual={r[0] for r in db.execute('SELECT spid FROM players WHERE spid / 1000000 = 84')}
    assert actual and real_after['tc_special_sets']()[60084][0]==frozenset(actual)
    assert 60084 not in real_before['tc_special_sets']()
    passed(f'Read-only current DB: all {len(actual)} season-84 cards included, other seasons excluded')
    real_colors_before=real_before['tc_colors'](); real_colors_after=real_after['tc_colors']()
    real_index={c['teamcolorid']:c for c in real_colors_after}
    assert all(real_index[c['teamcolorid']]==c for c in real_colors_before)
    passed('Read-only current DB: every existing color definition unchanged')
    # Source-bound bytecode contract: no client edit and no inferred arbitrary type.
    sys.path.insert(0,r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\experience_levels')
    from avm_patch import ABC,dis
    from inspect_client import inspect
    inspect()
    a=ABC((ROOT/'TeamColorController.abc').read_bytes())
    bytecode=lambda mid:'\n'.join(dis(a.A,a.A['body'][mid]))
    assert 'pushstring "feature"' in bytecode(59) and 'getproperty _teamColorSpecials' in bytecode(59)
    assert 'setproperty __featureTeamColor' in bytecode(82)
    assert 'getproperty __featureTeamColor' in bytecode(79)
    assert 'pushstring "feature"' in bytecode(78)
    assert 'setproperty __featureTeamColor' in bytecode(43)
    passed('Current official client supports independent feature classification/application/clear')
    report=dict(status='PASS',case_count=len(cases),cases=cases,
                baseline_sha256=hashlib.sha256(original.encode('utf8')).hexdigest(),
                proposed_sha256=hashlib.sha256(transform(original).encode('utf8')).hexdigest(),
                transformer_sha256=hashlib.sha256((ROOT/'prepare.py').read_bytes()).hexdigest(),
                installed_source_checked='--installed' in sys.argv,
                scope='Exact extracted proposed functions, synthetic cards and read-only official client bytecode; no running service imports or save functions',
                formal_files_written=False,services_restarted=False,native_game_verified=False,match_verified=False)
    (ROOT/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(report,ensure_ascii=True))

if __name__=='__main__': main()
