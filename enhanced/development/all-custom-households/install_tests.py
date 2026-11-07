"""Regression on the actual fresh verified-subset installation database."""
from pathlib import Path
from contextlib import closing
import copy,json,sqlite3
import prepare as p
def main():
 out=Path(p.source.read(p.P/'install-build-current.json')['build']);plan=p.source.read(out/'plan.json');target=out/'fifadb.sqlite';checks=[]
 with closing(sqlite3.connect(target,uri=True)) as db:
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok';db.execute('attach database ? as original',((p.S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',));checks.append('SQLite integrity')
  columns=[r[1] for r in db.execute('pragma table_info(players)') if r[1] not in ('historyopen','teamid','leagueid')];fields=','.join('"'+c+'"' for c in columns)
  for a,b in [('main','original'),('original','main')]:assert not db.execute(f'select {fields} from {a}.players except select {fields} from {b}.players limit 1').fetchone()
  checks.append('Every card ability, potential, star, model selector, name identity and preferred position preserved')
  for (name,) in db.execute("select name from sqlite_master where type='table'").fetchall():
   if name in ('players','playerhistory'):continue
   q='"'+name.replace('"','""')+'"'
   for a,b in [('main','original'),('original','main')]:assert not db.execute(f'select * from {a}.{q} except select * from {b}.{q} limit 1').fetchone(),name
  checks.append('Every unrelated table and every removed-player deletion preserved')
  registered={c['fo3_spid'] for c in p.source.read(p.S/'gamedata/custom_rosters.json')['cards']};china={sid for sid in registered if sid//1000000==327}
  assert all(db.execute('select historyopen from players where spid=?',(sid,)).fetchone()==(1,) for sid in registered)
  flags={r[0] for r in db.execute('select a.spid from players a join original.players b using(spid) where a.historyopen is not b.historyopen')};assert flags<=registered
  clubs={r[0] for r in db.execute('select a.spid from players a join original.players b using(spid) where a.teamid is not b.teamid or a.leagueid is not b.leagueid')};assert clubs==china and len(china)==32;checks.append('Only registered cards open history; exactly 32 China current teams change')
  assert not db.execute('select * from original.playerhistory except select * from main.playerhistory limit 1').fetchone();checks.append('Every original history row, date, loan and eligibility preserved exactly')
  for r in plan['history_changes']:
   got=[tuple(x) for x in db.execute('select teamid,joinedyear,endyear,loan from playerhistory where playerid=? order by ordernum',(r['playerid'],))];assert got==list(map(tuple,r['after']))
  checks.append('Verified new club rows match frozen source plan with dates/loan flags')
  for sid in registered:
   pid=sid%1000000;expected=db.execute('select count(*) from playerhistory where playerid=?',(pid,)).fetchone()[0]
   assert db.execute('select count(*) from players A join playerhistory B on A.playerid=B.playerid where A.spid=? and A.historyopen=1',(sid,)).fetchone()[0]==expected
  checks.append('Native PlayerListUtil history predicate exposes every registered card history')
 balance=p.load(p.P.parent/'team-balance-household/balance.py','verified_household_production_test');source=(p.S/'http_config.py').read_text('utf8');ns=balance.functions(source,target,set())
 cards,hist=ns['tc_static']();assert {5,17,21}<=hist[256790];assert {44,47,50,52,243,1848}<=hist[7631];assert {11,240,110374}<=hist[193080];checks.append('Musiala Chelsea/Southampton/Bayern youth, Cassano missing clubs and De Gea full supported clubs exposed')
 candidates=[];seen=set()
 for sid in sorted(registered):
  pid,team,nation=cards[sid]
  if pid not in seen and team!=5 and 5 in hist.get(pid,set()):candidates.append(sid);seen.add(pid)
  if len(candidates)==4:break
 assert len(candidates)==4
 def team(ids):
  players=[dict(id=str(i+1),spid=sid,grade=1,levelinfo={'level':1}) for i,sid in enumerate(ids)]
  return dict(players=players,squad=dict(positions=[dict(id=x['id'],spid=x['spid'],pos=i+1) for i,x in enumerate(players)]))
 assert dict(teamcolorid=ns['TC_CLUB'],boostindex=0,teamid=5) in ns['active_teamcolors'](team(candidates));checks.append('Four distinct former/youth Chelsea identities activate production club tier')
 assert not any(x['teamcolorid']==ns['TC_CLUB'] for x in ns['active_teamcolors'](team([candidates[0]]*4)));checks.append('Duplicate identities cannot activate a club tier')
 assert dict(teamcolorid=ns['TC_CLUB'],boostindex=0,teamid=p.CHINA_TEAM) in ns['active_teamcolors'](team(sorted(china)[:4]));checks.append('Four China Future current clubs activate the production club tier')
 payloads=p.source.read(out/'payloads.json')
 if (out/'season-placement.json').exists():
  placement=p.source.read(out/'season-placement.json');before=[r for r in placement['before'] if r.get('value')!=[856]];after=[r for r in placement['after'] if r.get('value')!=[856]]
  assert before==after and sum(r.get('value')==[856] for r in placement['after'])==1
  assert placement['after'][placement['inserted_index']]['value']==[856];checks.append('New 25U filter inserted by card strength; all old season definitions and relative order preserved')
 for lang in ('eng','chi','ind','kor','tha','vie'):
  with closing(sqlite3.connect(out/f'{lang}.sqlite')) as db:assert db.execute('select teamname from team where teamid=?',(p.CHINA_TEAM,)).fetchone()==('中国明日之星',)
 checks.append('All six native language team tables resolve China Future name')
 result=dict(status='PASS',case_count=len(checks),checks=checks,database_sha256=p.sha(target),installer_build=str(out),source_sha256=p.sha(p.S/'http_config.py'),formal_files_written=False,real_assets_written=False,native_match_verified=False,full_coverage_claimed=False)
 p.source.write(p.P/'tests.json',result);print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
