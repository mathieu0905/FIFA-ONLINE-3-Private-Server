"""Prepare history permissions/current-club deltas without changing production files.

Never install an incomplete career audit.  The resource/installation stage consumes
only a READY_FOR_RESOURCE_BUILD plan, bound to all current production inputs.
"""
from pathlib import Path
from collections import defaultdict,Counter
from contextlib import closing
import datetime,gzip,hashlib,json,sqlite3,sys
import collect as source
import map_clubs
P=source.P;S=source.S;C=Path('D:/FO3ID/32795');CHINA_TEAM=999327
ROOT=P;SERVER=S;CLIENT=C
write=source.write
def load(path,name):
 import importlib.util
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def build_plan():
 registry=source.read(S/'gamedata/custom_rosters.json');mapping=source.read(P/'club-mapping.json')
 cards={int(c['fo3_spid']):c for c in registry['cards']};pids={int(c['base_playerid']) for c in cards.values()}
 with closing(sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  db.row_factory=sqlite3.Row
  players={r['spid']:dict(r) for r in db.execute('select * from players')}
  old=defaultdict(list)
  for pid,_,tid,start,end,loan in db.execute('select * from playerhistory order by playerid,ordernum'):old[pid].append((tid,start,end,loan))
 assert cards.keys()<=players.keys()
 for sid,card in cards.items():assert players[sid]['playerid']==card['base_playerid']
 assert not any(r['teamid']==CHINA_TEAM for r in players.values()),'Check existing China team instead of reassigning'
 flags=[dict(spid=sid,before=players[sid]['historyopen'],after=1) for sid in sorted(cards) if players[sid]['historyopen']!=1]
 china=[dict(spid=sid,before=players[sid]['teamid'],after=CHINA_TEAM,league_before=players[sid]['leagueid'],league_after=2028) for sid in sorted(cards) if sid//1000000==327]
 # De-duplicate the exact same source spell, preserving separate loan/permanent
 # and youth/senior dates. No unknown date is invented from today's date.
 incoming=defaultdict(set);provenance=defaultdict(list)
 for row in china:
  if row['before']>0:incoming[players[row['spid']]['playerid']].add((row['before'],-1,-1,0))
 for row in mapping['resolved']:
  if row['playerid'] not in pids:continue
  incoming[row['playerid']].add((int(row['teamid']),row['joinedyear'],row['endyear'],row['loan']))
  provenance[row['playerid']].append(row)
 for path in (source.SRC/'careers').glob('*.json'):
  r=source.read(path);pid=r['playerid']
  if r.get('status')!='OK' or pid not in pids:continue
  raw=gzip.decompress(Path(r['raw_file']).read_bytes())
  assert hashlib.sha256(raw).hexdigest()==r['raw_sha256'],path
  assert int(r['source_spid'])%1000000==int(r.get('source_playerid',pid)),path
  for row in r['career']:
   tid=mapping['korean'].get(row['club_ko'])
   if tid is not None:incoming[pid].add((int(tid),row['joinedyear'],row['endyear'],row['loan']))
 changes=[]
 for pid,rows in sorted(incoming.items()):
  # This union never rewrites old spells or drops any previously earned club.
  after=sorted(set(old.get(pid,[]))|rows,key=lambda r:(r[1],r[2] if r[2]>=0 else 9999,r[0],r[3]))
  if after!=old.get(pid,[]):changes.append(dict(playerid=pid,before=old.get(pid,[]),after=after,added_clubs=sorted({r[0] for r in after}-{r[0] for r in old.get(pid,[])})))
 source_issues=[]
 for pid in sorted(pids):
  path=source.SRC/'wiki'/f'{pid}.json'
  r=source.read(path) if path.exists() else {'status':'NOT_COLLECTED'}
  if r.get('status')!='OK':source_issues.append(dict(playerid=pid,status=r['status'],title=r.get('title'),expected_dob=r.get('expected_dob'),source_dob=r.get('source_dob')))
 pending_clubs=mapping['unresolved']
 baseline={str(path):sha(path) for path in [S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/custom_rosters.json',S/'server_display_zh.json',S/'play-local.bat',P/'club-mapping.json',Path(__file__)]}
 return dict(status='SOURCE_REVIEW_REQUIRED' if source_issues or pending_clubs else 'READY_FOR_RESOURCE_BUILD',created_at=datetime.datetime.now().astimezone().isoformat(),registered_cards=len(cards),identities=len(pids),history_permissions=flags,china_current_clubs=china,china_team=dict(teamid=CHINA_TEAM,name='中国明日之星',leagueid=2028),history_changes=changes,source_issues=source_issues,unresolved_clubs=pending_clubs,baseline=baseline,formal_files_written=False,state_shop_written=False,attributes_changed=False)
def apply_database(plan,target):
 # Also used by local regression: incomplete source plans remain explicitly
 # incomplete and must not be mistaken for an installable resource.
 import shutil
 shutil.copyfile(S/'gamedata/fifadb.sqlite',target)
 with closing(sqlite3.connect(target)) as db:
  with db:
   for row in plan['history_permissions']:db.execute('update players set historyopen=? where spid=?',(row['after'],row['spid']))
   for row in plan['china_current_clubs']:db.execute('update players set teamid=?,leagueid=? where spid=?',(row['after'],row['league_after'],row['spid']))
   for row in plan['history_changes']:
    db.execute('delete from playerhistory where playerid=?',(row['playerid'],))
    db.executemany('insert into playerhistory(playerid,ordernum,teamid,joinedyear,endyear,loan) values(?,?,?,?,?,?)',[(row['playerid'],n,*spell) for n,spell in enumerate(row['after'])])
def main():
 plan=build_plan();source.write(P/'preparation-plan.json',plan)
 print(json.dumps({k:plan[k] for k in ['status','registered_cards','identities','formal_files_written']}))
 print(json.dumps(dict(flags_to_enable=len(plan['history_permissions']),china_cards=len(plan['china_current_clubs']),changed_identities=len(plan['history_changes']),source_issues=len(plan['source_issues']),unresolved_clubs=len(plan['unresolved_clubs']))))
if __name__=='__main__':main()
