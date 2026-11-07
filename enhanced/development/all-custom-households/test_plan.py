"""Temporary-data regression of the proposed club permissions and history merge."""
from pathlib import Path
from contextlib import closing
import json,sqlite3,tempfile
import prepare as p
def main():
 plan=p.build_plan();checks=[]
 with tempfile.TemporaryDirectory(prefix='household-regression-',dir=p.P) as root:
  target=Path(root)/'fifadb.sqlite';p.apply_database(plan,target)
  with closing(sqlite3.connect(target,uri=True)) as db:
   assert db.execute('pragma integrity_check').fetchone()[0]=='ok';checks.append('SQLite integrity')
   db.execute('attach database ? as original',((p.S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',))
   registry=p.source.read(p.S/'gamedata/custom_rosters.json');spids={c['fo3_spid'] for c in registry['cards']};china={s for s in spids if s//1000000==327}
   cols=[r[1] for r in db.execute('pragma table_info(players)')];safe=[c for c in cols if c not in ('historyopen','teamid','leagueid')];projection=','.join('"'+c+'"' for c in safe)
   for a,b in [('main','original'),('original','main')]:assert not db.execute(f'select {projection} from {a}.players except select {projection} from {b}.players limit 1').fetchone()
   checks.append('Every card attribute, skill, identity, position and model selector preserved')
   for (name,) in db.execute("select name from sqlite_master where type='table'").fetchall():
    if name in ('players','playerhistory'):continue
    q='"'+name.replace('"','""')+'"'
    for a,b in [('main','original'),('original','main')]:assert not db.execute(f'select * from {a}.{q} except select * from {b}.{q} limit 1').fetchone(),name
   checks.append('All unrelated tables and permissions preserved')
   changed={r[0] for r in db.execute('select a.spid from players a join original.players b using(spid) where a.historyopen is not b.historyopen')};assert changed<=spids
   assert all(db.execute('select historyopen from players where spid=?',(s,)).fetchone()==(1,) for s in spids);checks.append('Every registered custom card opens native career history')
   teams_changed={r[0] for r in db.execute('select a.spid from players a join original.players b using(spid) where a.teamid is not b.teamid or a.leagueid is not b.leagueid')};assert teams_changed==china and len(china)==32
   assert db.execute('select count(*) from players where spid/1000000=327 and teamid=?',(p.CHINA_TEAM,)).fetchone()[0]==32;checks.append('Exactly 32 China Future current clubs change')
   assert not db.execute('select playerid,teamid from original.playerhistory except select playerid,teamid from main.playerhistory limit 1').fetchone();checks.append('Every original historical eligibility preserved')
   for row in plan['china_current_clubs']:
    if row['before']>0:assert db.execute('select 1 from playerhistory where playerid=? and teamid=?',(row['spid']%1000000,row['before'])).fetchone()
   checks.append('China current-club reassignment preserves real former current clubs')
   for change in plan['history_changes']:
    actual={tuple(r) for r in db.execute('select teamid,joinedyear,endyear,loan from playerhistory where playerid=?',(change['playerid'],))};assert set(map(tuple,change['after']))==actual
   checks.append('All verified proposed spell dates and loan flags survive database application')
   # Exact native predicate: A.historyopen=1 is required by PlayerListUtil.
   for sid in spids:
    pid=sid%1000000
    expected=db.execute('select count(*) from playerhistory where playerid=?',(pid,)).fetchone()[0]
    actual=db.execute('select count(*) from players A join playerhistory B on A.playerid=B.playerid where A.spid=? and A.historyopen=1',(sid,)).fetchone()[0];assert actual==expected
   checks.append('Native history predicate agrees with server-visible histories for every custom card')
 report=dict(status='PASS',checks=checks,case_count=len(checks),plan_status=plan['status'],source_review_complete=False,formal_files_written=False,assets_written=False,resource_verified=False,native_match_verified=False,baseline=plan['baseline'])
 p.source.write(p.P/'plan-tests.json',report);print(json.dumps({k:report[k] for k in ('status','case_count','plan_status','formal_files_written','native_match_verified')}))
if __name__=='__main__':main()
