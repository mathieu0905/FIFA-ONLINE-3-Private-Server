"""Production-function regressions with temporary cards only; no service imports or live assets."""
from contextlib import closing
from pathlib import Path
import ast
import copy
import functools
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
sys.dont_write_bytecode=True
import prepare


def functions(source,database,labels=None):
    harness=(prepare.ROOT.parent/'team-bonus20/test.py').read_text('utf8')
    node=next(n for n in ast.parse(harness).body if isinstance(n,ast.FunctionDef) and n.name=='functions')
    outer=dict(ast=ast,functools=functools,closing=closing,Database=lambda:None)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'production-function-extractor','exec'),outer)
    ns=outer['functions'](source,real=True)
    ns.update(os=os,json=json,HERE=str(prepare.SERVER),_db=lambda:sqlite3.connect('file:'+Path(database).as_posix()+'?mode=ro',uri=True))
    # Classification is analysis metadata only, never a production bonus.
    ns['ANALYSIS_EXCLUDED_SEASONS']=frozenset(ns['TC_LEGENDS']+(12,19,26,31,32,33,37,38,39,41,43,84,95,97,327))
    ns['analysis_club_names']=lambda: labels if labels is not None else json.loads((prepare.SERVER/'server_display_zh.json').read_text('utf8'))['names_by_id']['TEAMNAMES_CHI.json']
    ns['STAT_COLS']=sorted({k for weights in ns['ROLE_WEIGHTS'].values() for k in weights})
    ns['GRADE_BOOST']=(0,5,6,7,8,10,12,14,17,20,24)+tuple(24+2*(g-10) for g in range(11,21))
    with closing(ns['_db']()) as db:
        db.row_factory=sqlite3.Row
        stats={r['spid']:dict(r) for r in db.execute('SELECT * FROM players')}
    ns['card_stats']=lambda ids:{sid:stats[sid] for sid in ids}
    return ns


def fixture(path):
    with sqlite3.connect('file:'+(prepare.SERVER/'gamedata/fifadb.sqlite').as_posix()+'?mode=ro',uri=True) as real:
        schema=real.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='players'").fetchone()[0]
        fields=[r[1] for r in real.execute('PRAGMA table_info(players)')]
    c=sqlite3.connect(path);c.execute(schema);c.execute('CREATE TABLE playerhistory(playerid INTEGER,teamid INTEGER)')
    def add(code,pid,club=11,league=13,nationalteam=1318):
        row=dict.fromkeys(fields,70)
        row.update(spid=code*1000000+pid,playerid=pid,teamid=club,leagueid=league,nationalteamid=nationalteam,nationality=45,
                   birthdate='1/1/1980 12:00:00 AM',preferredposition1=13,preferredposition2=0,preferredposition3=5,preferredposition4=25,
                   height=180,internationalrep=0,skillmoves=2,attackingworkrate=1,defensiveworkrate=1)
        c.execute('INSERT INTO players('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',[row[k] for k in fields])
        return row['spid']
    for i in range(1,12):
        add(88,1000+i);add(93,2000+i,league=2028);add(88,4000+i,club=243,league=53)
    add(91,1001)
    for code in (12,19,26,31,32,33,37,38,39,41,43,48,55,84,95,97,327):
        for i in range(1,12):add(code,30000+code*100+i,league=2028)
    for code,pid,club,league in [(40,70001,11,2028),(856,70002,11,13),(88,71001,1318,78),(88,71002,999918,2028),(88,71003,113703,2028),(0,71004,11,13)]:add(code,pid,club,league)
    for pid in range(1001,1012):c.execute('INSERT INTO playerhistory VALUES (?,?)',(pid,243))
    c.commit();c.close()


def team(n,grade=10):
    players=[dict(id=str(i),spid=(88001000+i if i<=n else 93002000+i),grade=grade,levelinfo={'level':20,'exp':0}) for i in range(1,12)]
    return dict(players=players,squad=dict(positions=[dict(id=p['id'],spid=p['spid'],pos=13) for p in players]))


def rated(ns,tm):
    tm=copy.deepcopy(tm);tm['teamcolors']=ns['active_teamcolors'](tm)
    return ns['xi_ratings'](tm),tm['teamcolors']


def main():
    if '--installed' in sys.argv:
        original=(prepare.ROOT/'baseline-http.py').read_text('utf8');proposed=(prepare.SERVER/'http_config.py').read_text('utf8')
        assert proposed==prepare.transform(original)
    else:
        original=(prepare.SERVER/'http_config.py').read_text('utf8');proposed=prepare.transform(original)
    checks=[]
    assert 'TC_ORDINARY_CLUB_BASE' not in proposed and 'tc_ordinary_club_sets' not in proposed
    checks.append('No ordinary-only reward definitions, memberships or feature colors in proposed production source')
    with tempfile.TemporaryDirectory(prefix='cards-',dir=prepare.ROOT) as temp:
        path=Path(temp)/'cards.sqlite';fixture(path)
        old=functions(original,path);new=functions(proposed,path)
        assert new['TC_CLUB_GROUPS']==new['_tc_groups']((4,5,1),(6,7,3),(8,9,5),(10,10,7),(11,11,8))
        before={c['teamcolorid']:c for c in old['tc_colors']()};after={c['teamcolorid']:c for c in new['tc_colors']()}
        assert before.keys()==after.keys()
        for cid,color in before.items():
            expected=copy.deepcopy(color)
            if color['type']=='club':
                named=next((b for c,t,b in new['TC_NAMED_CLUBS'] if c==cid),None)
                expected['boostgroups']=new['_tc_boost'](new['TC_CLUB_GROUPS'],named) if named is not None else new['TC_CLUB_GROUPS']
            assert after[cid]==expected
        assert old['tc_special_sets']()==new['tc_special_sets']()
        checks.append('Only base club tiers change; all other colors, memberships, specialties and moments preserved')
        for n in range(12):
            tm=team(n);a,_=rated(old,tm);b,_=rated(new,tm)
            assert all(b[k]-a[k]==4 for k in a),(n,a,b)
            checks.append(str(n)+' ordinary starters: exact same full-club +4 delta for every card type, no ordinary extra')
        for grade in (1,5,9,12,16,20):
            a,_=rated(old,team(11,grade));b,_=rated(new,team(11,grade));assert all(b[k]-a[k]==4 for k in a)
        checks.append('All reinforcement tiers preserved without ordinary-card reward')
        with closing(sqlite3.connect(path)) as db:
            db.execute('DELETE FROM playerhistory');db.commit()
        ns=functions(proposed,path)
        for n in range(12):
            tm=team(11)
            for i in range(n,11):
                sid=88004001+i;tm['players'][i]['spid']=sid;tm['squad']['positions'][i]['spid']=sid
            active=ns['active_teamcolors'](tm)
            club=[c for c in active if c['teamcolorid']==ns['TC_CLUB'] and c['teamid']==11]
            if n<4:assert not club
            else:
                expected=0 if n<6 else 1 if n<8 else 2 if n<10 else 3 if n==10 else 4
                assert len(club)==1 and club[0]['boostindex']==expected,(n,club)
        checks.append('Actual XI activation respects every base club threshold 0..11')
    realold=functions(original,prepare.SERVER/'gamedata/fifadb.sqlite');realnew=functions(proposed,prepare.SERVER/'gamedata/fifadb.sqlite')
    assert len(realold['tc_colors']())==len(realnew['tc_colors']())
    assert realold['tc_special_sets']()==realnew['tc_special_sets']()
    checks.append('Full formal catalog has no added colors or changed special memberships')
    report=dict(status='PASS',case_count=len(checks),checks=checks,baseline_sha256=hashlib.sha256(original.encode()).hexdigest(),
        proposed_sha256=hashlib.sha256(proposed.encode()).hexdigest(),transformer_sha256=prepare.sha(prepare.ROOT/'prepare.py'),
        test_sha256=prepare.sha(Path(__file__)),ordinary_club_features=0,ordinary_reward_removed=True,
        total_colors=len(realnew['tc_colors']()),formal_files_written=False,state_shop_written=False,
        installed_source_checked='--installed' in sys.argv,native_game_verified=False,match_verified=False)
    prepare.write(prepare.ROOT/'tests.json',report)
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
