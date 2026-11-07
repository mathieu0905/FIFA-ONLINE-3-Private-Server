"""Independent invariants and actual AVM2 execution evidence for this change."""
from build_traits import *
import ast,subprocess
def main():
 before=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);before.row_factory=sqlite3.Row
 after=sqlite3.connect((R/'trait-build/fifadb.sqlite').as_uri()+'?mode=ro',uri=True);after.row_factory=sqlite3.Row
 old={r['spid']:dict(r) for r in before.execute('SELECT * FROM players')}
 new={r['spid']:dict(r) for r in after.execute('SELECT * FROM players')}
 assert old.keys()==new.keys();ims=[]
 for sid,p in old.items():
  q=new[sid]
  if sid//1000000!=84:assert p==q;continue
  assert all(p[k]==q[k] for k in p if k not in ('trait1','badges'))
  assert p['trait1']&q['trait1']==p['trait1']
  assert p['badges']&q['badges']==p['badges']
  ims.append(p)
 assert len(ims)==123
 groups=collections.defaultdict(list)
 for p in old.values():
  if p['spid']>=1000000 and p['spid']//1000000!=84:groups[p['playerid']].append(p)
 keeper_count=0;field_count=0
 for p in ims:
  q=new[p['spid']];pos=p['preferredposition1'];others=groups[p['playerid']]
  allowed=set(range(30))-set((0,3,4,6,9,11,2,8,17))
  if pos==0:
   allowed&={5,10,20,21,23,26,28};keeper_count+=1
   assert q['trait1']&(1<<20) and q['trait1']&(1<<21) and q['trait1']&(1<<23)
   assert q['badges']==p['badges']
  else:
   allowed-={19,20,21,23};field_count+=1
   gold=14 if pos<=8 else 15 if pos<=18 else 16
   assert q['badges']&(1<<gold)
   for other in others:assert q['badges']&other['badges']==other['badges']
  visible=lambda card:sum(bool(card['trait1']&(1<<i)) for i in allowed)
  assert visible(q)>max(visible(o) for o in others)
  assert visible(q)>visible(p)
  for o in others:assert (o['trait1']&mask(allowed))&q['trait1']==o['trait1']&mask(allowed)
 assert (field_count,keeper_count)==(113,10)
 # Every other table, including names, eligibility, valuation references and
 # identities, must match byte-for-value, not only table sizes.
 for name, in before.execute("SELECT name FROM sqlite_master WHERE type='table'"):
  if name=='players':continue
  table='"'+name.replace('"','""')+'"'
  assert sorted(map(tuple,before.execute('SELECT * FROM '+table)),key=repr)==sorted(map(tuple,after.execute('SELECT * FROM '+table)),key=repr),name
 before.close();after.close()
 result=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(R/'test_vm.py')],capture_output=True,text=True,encoding='utf8',errors='replace')
 assert result.returncode==0,result.stdout+result.stderr
 assert 'ALL_HISTORY_VM_PASS' in result.stdout
 log=(R/'vm/result.log').read_text('utf8');assert log.count('PASS ')==17
 for p in R.glob('*.py'):ast.parse(p.read_text('utf-8-sig'))
 # The installation entry must defer before inspecting a plan, acquiring
 # locks, stopping services or writing formal files when the game is active.
 installer=load(R/'install.py','detail_install_test')
 original_idle=installer.tx.idle;original_plan=installer.plan
 installer.tx.idle=lambda:False
 installer.plan=lambda:(_ for _ in ()).throw(AssertionError('Planning reached while playing'))
 try:installer.main()
 finally:installer.tx.idle=original_idle;installer.plan=original_plan
 deferred=json.loads((R/'install-status.json').read_text('utf8'))
 assert deferred['status']=='DEFERRED_GAME_RUNNING' and not deferred['formal_files_written'] and not deferred['services_restarted']
 # Exercise the shared CAS/rollback code with tiny disposable files only.
 temp=R/'transaction-check';temp.mkdir(exist_ok=True)
 dst=temp/'target';dst.write_bytes(b'latest');src=temp/'new';src.write_bytes(b'ours')
 e=dict(target=dst,source=src,before=hashlib.sha256(b'older').hexdigest(),after=hashlib.sha256(b'ours').hexdigest())
 try:installer.tx.cas(e)
 except RuntimeError:pass
 else:raise AssertionError('CAS accepted a newer target')
 assert dst.read_bytes()==b'latest'
 e['before']=installer.tx.current_hash(dst);backup=temp/'backup';backup.write_bytes(b'latest');e['backup']=backup
 installer.tx.cas(e);assert dst.read_bytes()==b'ours'
 dst.write_bytes(b'later-other-chat')
 assert installer.tx.rollback([e])==[str(dst)] and dst.read_bytes()==b'later-other-chat'
 dst.write_bytes(b'ours');assert installer.tx.rollback([e])==[] and dst.read_bytes()==b'latest'
 report=dict(status='PASS',IM_cards=123,outfield_with_position_native_gold=field_count,goalkeepers_with_native_traits=keeper_count,
  exact_non_IM_rows=True,all_other_tables_exact=True,all_original_trait_and_badge_bits_retained=True,
  all_visible_positive_counts_strictly_above_same_identity_seasons=True,AVM2_checks=17,lookup_chunk_boundaries=342,
  game_running_install_deferral=True,CAS_and_later_writer_rollback_protection=True,
  full_import=json.loads((R/'trait-build/report.json').read_text('utf8'))['full_import'],
  ui_sha256=base.sha(R/'ui-build/SquadAssets.big'),VM_log_sha256=base.sha(R/'vm/result.log'),
  tooling={p.name:base.sha(p) for p in R.glob('*.py')},formal_written=False,native_gui_verified=False,match_verified=False)
 base.save(R/'tests.json',report);print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()

