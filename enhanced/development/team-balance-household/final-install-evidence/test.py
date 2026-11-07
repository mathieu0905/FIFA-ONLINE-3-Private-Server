"""Meaningful history, identity and roster regressions against current production functions."""
from pathlib import Path
import copy
import json
import sqlite3
import sys
sys.dont_write_bytecode=True
import balance
import prepare
import manual


def run(database):
    source=(prepare.SERVER/'http_config.py').read_text('utf8')
    market={int(k) for k in json.loads((prepare.SERVER/'gamedata/fa_prices.json').read_text('utf8'))}
    ns=balance.functions(source,database,market)
    cards,hist=ns['tc_static']()
    checks=[]
    # Every season of a repaired identity must see every reviewed old club.
    for pid,(_,_,_,career) in manual.DATA.items():
        expected={row[0] for row in career}
        assert expected<=hist[pid],(pid,expected-hist[pid])
        seasons=[(sid,c) for sid,c in cards.items() if c[0]==pid]
        assert seasons
        assert all(expected<=({c[1]}|hist[pid]) for sid,c in seasons)
    checks.append(f'All reviewed supported senior clubs apply to every existing season of all {len(manual.DATA)} manually matched identities')
    assert 312 in hist[238380]
    checks.append('Yashin exact Nexon career resolves to Moscow Dynamo 312')
    assert 10 in hist[230026] and 54 in hist[230026] and 1939 in hist[230026]
    checks.append('Denis Law gains both Manchester clubs, Torino and Huddersfield')
    assert 7 in hist[249] and 11 in hist[249]
    assert not {112893,112996}&hist[249]
    checks.append('Phil Neville playing history contains Everton and United; no coaching teams imported')
    with sqlite3.connect('file:'+Path(database).as_posix()+'?mode=ro',uri=True) as db:
        law=db.execute('SELECT joinedyear,endyear FROM playerhistory WHERE playerid=230026 AND teamid=10 ORDER BY joinedyear').fetchall()
        assert law==[(1960,1961),(1973,1974)]
        cole=db.execute('SELECT loan FROM playerhistory WHERE playerid=239 AND teamid=1919 ORDER BY loan').fetchall()
        assert cole==[(0,),(1,)]
        assert db.execute('SELECT COUNT(*) FROM playerhistory WHERE playerid=245 AND teamid=88 AND loan=1').fetchone()[0]==1
    checks+=['Repeated Manchester City spells remain distinct','Bristol City loan and permanent spells remain distinct','Nicky Butt Birmingham loan remains a loan']
    players=[]
    for pid in (36,239,245,230026):
        sid=next(s for s,c in cards.items() if c[0]==pid and c[1]!=11)
        players.append(dict(id=str(pid),spid=sid,grade=1,levelinfo={'level':1}))
    team=dict(players=players,squad=dict(positions=[dict(id=p['id'],spid=p['spid'],pos=i+1) for i,p in enumerate(players)]))
    assert dict(teamcolorid=17,boostindex=0,teamid=11) in ns['active_teamcolors'](team)
    checks.append('Four formerly missed legends with non-United card clubs activate United production color')
    duplicate=copy.deepcopy(team)
    sid=players[0]['spid']
    for i in range(4):
        duplicate['players'][i].update(spid=sid)
        duplicate['squad']['positions'][i].update(spid=sid)
    assert not any(c['teamcolorid']==17 for c in ns['active_teamcolors'](duplicate))
    checks.append('Four copies/seasons of one real identity do not activate a club tier')
    # Stored candidates must contain 11 different identities and only supported
    # natural position roles; no all-attacker or duplicated-card pseudo XI.
    result=json.loads((prepare.ROOT/'balance.json').read_text('utf8'))
    assert result['database_sha256']==prepare.sha(database)
    for entry in result['results']:
        if entry['status']!='PASS':continue
        for score in entry['ratings'].values():
            assert len(score['roster'])==11 and len({p['playerid'] for p in score['roster']})==11
        if entry['pool'].endswith('_mixed') or entry['pool'].endswith('_ordinary_only'):
            assert all(p['spid']//1000000 not in (84,327) for p in entry['ratings']['current']['roster'])
    checks.append('Every compared XI has 11 distinct identities; club comparisons exclude top-tier moments and China future cards')
    assert ns['TC_MOMENTS_GROUPS']==ns['_tc_groups']((3,5,4),(6,8,6),(9,10,8),(11,11,10))
    assert ns['TC_CLUB_GROUPS']==ns['_tc_groups']((4,5,1),(6,7,2),(8,9,3),(10,11,4))
    checks.append('Moments top-tier feature, reinforcement rules and current club tiers are not changed by the household repair')
    merged=prepare.load(prepare.OLD/'build.py','history_merge_regression').merge
    with sqlite3.connect('file:'+Path(database).as_posix()+'?mode=ro',uri=True) as db:
        rows=[tuple(r) for r in db.execute('SELECT teamid,joinedyear,endyear,loan FROM playerhistory WHERE playerid=239 ORDER BY ordernum')]
    assert merged(rows,manual.DATA[239][3])==rows
    checks.append('Applying reviewed Andy Cole career twice is idempotent')
    proof=prepare.load(prepare.OLD/'build.py','history_table_regression').verify_tables(database,prepare.SERVER/'gamedata/fifadb.sqlite')
    checks.append('SQLite integrity, all non-history tables and every existing club eligibility preserved')
    report=dict(status='PASS',case_count=len(checks),checks=checks,source_sha256=prepare.sha(prepare.SERVER/'http_config.py'),
        database_sha256=prepare.sha(database),manual_sha256=prepare.sha(prepare.ROOT/'manual.py'),
        test_sha256=prepare.sha(Path(__file__)),table_proof=proof,real_assets_written=False,native_match_verified=False)
    prepare.write(prepare.ROOT/'tests.json',report)
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':run(prepare.BUILD/'fifadb.sqlite')
