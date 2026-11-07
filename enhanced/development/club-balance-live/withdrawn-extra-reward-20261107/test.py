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
    additional=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('tc_ordinary_club_names','tc_ordinary_club_sets')]
    exec(compile(ast.Module(body=additional,type_ignores=[]),'ordinary-club-functions','exec'),ns)
    ns.update(os=os,json=json,HERE=str(prepare.SERVER),_db=lambda:sqlite3.connect('file:'+Path(database).as_posix()+'?mode=ro',uri=True))
    if labels is not None:ns['tc_ordinary_club_names']=lambda:labels
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
        original=(prepare.SERVER/'http_config.py').read_text('utf8')
        proposed=prepare.transform(original)
    checks=[]
    with tempfile.TemporaryDirectory(prefix='cards-',dir=prepare.ROOT) as temp:
        path=Path(temp)/'cards.sqlite';fixture(path)
        labels={'11':'曼联','243':'皇马','1318':'英格兰','999918':'神童','113703':'传奇联队'}
        old=functions(original,path,labels);new=functions(proposed,path,labels)
        expected_base=[(4,5,1),(6,7,3),(8,9,5),(10,10,7),(11,11,8)]
        assert new['TC_CLUB_GROUPS']==new['_tc_groups'](*expected_base)
        assert new['TC_ORDINARY_CLUB_GROUPS']==new['_tc_groups']((3,4,1),(5,6,2),(7,8,3),(9,11,4))
        checks.append('Exact approved club and ordinary-support tiers')
        before={x['teamcolorid']:x for x in old['tc_colors']()};after={x['teamcolorid']:x for x in new['tc_colors']()}
        assert len(after)==len(new['tc_colors']())
        for cid,color in before.items():
            changed=copy.deepcopy(color)
            if color['type']=='club':
                changed['boostgroups']=new['_tc_boost'](new['TC_CLUB_GROUPS'],next(b for c,t,b in new['TC_NAMED_CLUBS'] if c==cid)) if cid!=17 else new['TC_CLUB_GROUPS']
            assert after[cid]==changed,(cid,color)
        assert old['TC_GRADE']==new['TC_GRADE'] and old['TC_MOMENTS_GROUPS']==new['TC_MOMENTS_GROUPS']
        checks.append('Every existing non-club color, named-club specialty, grade and moments definition preserved')
        memberships=new['tc_special_sets']();ordinary=new['tc_ordinary_club_sets']()
        assert 1000011 in ordinary and 1000243 in ordinary
        for n in range(12):
            tm=team(n);before_team=copy.deepcopy(tm);a,_=rated(old,tm);b,active=rated(new,tm)
            extra=0 if n<3 else 1 if n<=4 else 2 if n<=6 else 3 if n<=8 else 4
            for i in range(1,12):assert b[str(i)]-a[str(i)]==4+(extra if i<=n else 0),(n,i,b[str(i)]-a[str(i)])
            assert tm==before_team
            assert any(x['teamcolorid']==1000011 for x in active)==bool(extra)
            checks.append(f'{n} ordinary starters: correct boundary, recipient isolation and independent grade/base stacking')
        for grade in (1,5,9,12,16,20):
            a,_=rated(old,team(11,grade));b,_=rated(new,team(11,grade));assert all(b[k]-a[k]==8 for k in a)
        checks.append('All grade thresholds retain their bonuses; ordinary +4 and full club +8 stack once')
        for code in (12,19,26,31,32,33,37,38,39,41,43,48,55,84,95,97,327):
            for i in range(1,12):assert code*1000000+30000+code*100+i not in ordinary[1000011][0]
        checks.append('All native legend variants, ICON, nostalgia, moments and China future cards are excluded from ordinary reward')
        assert 40070001 in ordinary[1000011][0] and 856070002 in ordinary[1000011][0] and 91001001 in ordinary[1000011][0]
        checks.append('NHD/WB and a newly registered non-legend UCL season are classified by card type, not retirement of the person')
        assert not any(cid in ordinary for cid in (1001318,1999918,1113703))
        assert 71004 not in ordinary[1000011][0]
        checks.append('National, fantasy/all-star placeholder clubs and season-zero engine rows cannot unlock ordinary support')
        duplicate=team(0)
        for i in range(4):
            sid=88001001 if i%2==0 else 91001001
            duplicate['players'][i]['spid']=sid;duplicate['squad']['positions'][i]['spid']=sid
        _,active=rated(new,duplicate);assert not any(c['teamcolorid']==1000011 for c in active)
        checks.append('Different seasons of one person count only once')
        bench=team(0)
        for i in range(1,5):
            p=dict(id='bench'+str(i),spid=88001000+i,grade=20,levelinfo={'level':20})
            bench['players'].append(p);bench['squad']['positions'].append(dict(id=p['id'],spid=p['spid'],pos=28))
        _,active=rated(new,bench);assert not any(c['teamcolorid']==1000011 for c in active)
        checks.append('Bench cards do not contribute')
        # Every ordinary player fits two activated clubs, but independent feature
        # selection grants the best support only once.
        a,_=rated(old,team(11));b,active=rated(new,team(11))
        assert any(x['teamcolorid']==1000243 for x in active) and all(b[k]-a[k]==8 for k in a)
        checks.append('Multiple true club histories use the highest ordinary reward, never sum multiple feature colors')
        tm=team(3);new['_state']=lambda:{'teams':{'0':tm}}
        response=new['ep_teamcolor']('',b'')
        assert response['teamColorSpecials']['1000011']==[88001001,88001002,88001003]
        assert all(isinstance(c['teamid'],str) for c in response['teamColors'] if c['type']=='feature')
        checks.append('Native feature string IDs and owned-card-only special membership response')
    started=time.monotonic();real=functions(proposed,prepare.SERVER/'gamedata/fifadb.sqlite')
    colors=real['tc_colors']();sets=real['tc_ordinary_club_sets']();raw=json.dumps(dict(teamColors=colors,teamColorSpecials={str(k):[] for k in sets}),ensure_ascii=False).encode('utf8')
    assert len({c['teamcolorid'] for c in colors})==len(colors)
    cards,_=real['tc_static']()
    assert all(sid//1000000 not in real['TC_ORDINARY_EXCLUDED_SEASONS'] and sid in cards for spids,_ in sets.values() for sid in spids)
    checks.append('Full formal catalog: unique IDs, no excluded season leaks and all memberships reference existing cards')
    report=dict(status='PASS',case_count=len(checks),checks=checks,baseline_sha256=hashlib.sha256(original.encode()).hexdigest(),
        proposed_sha256=hashlib.sha256(proposed.encode()).hexdigest(),transformer_sha256=prepare.sha(prepare.ROOT/'prepare.py'),
        test_sha256=prepare.sha(Path(__file__)),ordinary_club_features=len(sets),total_colors=len(colors),
        cold_catalog_seconds=round(time.monotonic()-started,3),unowned_catalog_bytes=len(raw),
        excluded_seasons=sorted(real['TC_ORDINARY_EXCLUDED_SEASONS']),formal_files_written=False,state_shop_written=False,
        installed_source_checked='--installed' in sys.argv,native_game_verified=False,match_verified=False)
    (prepare.ROOT/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
