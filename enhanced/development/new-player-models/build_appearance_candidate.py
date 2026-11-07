"""Build a private appearance calibration candidate; never install or alter saves."""
from pathlib import Path
import json,sys,sqlite3,shutil,datetime
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path.insert(0,str(W/'work/season_expansion'));import roster_import as codec
b,decrypt,replace,refpack,encrypt=codec.load_codecs(S)
review=json.loads((R/'appearance-review.json').read_text('utf8'));O=R/'appearance-candidate-v1';assert not O.exists();O.mkdir()
original_db=S/'gamedata/fifadb.sqlite';original_big=C/'data/data_0.big';initial_db=codec.sha(original_db);initial_big=codec.sha(original_big)
shutil.copyfile(original_db,O/'fifadb.sqlite');allowed={p['spid']:p['changes'] for p in review['players'] if p['changes']}
with sqlite3.connect(O/'fifadb.sqlite',uri=True) as db:
 db.execute('pragma temp_store=memory');db.execute('attach database ? as old',(original_db.as_uri()+'?mode=ro',))
 for spid,fields in allowed.items():
  assert set(fields)<=set(['bodytypecode','skintonecode'])
  for field,change in fields.items():
   assert db.execute(f'select {field} from players where spid=?',(spid,)).fetchone()[0]==change['before']
   db.execute(f'update players set {field}=? where spid=?',(change['proposed'],spid))
 db.commit();assert db.execute('pragma integrity_check').fetchone()==('ok',)
 columns=[r[1] for r in db.execute('pragma table_info(players)')]
 for spid,fields in allowed.items():
  old=db.execute('select * from old.players where spid=?',(spid,)).fetchone();new=db.execute('select * from main.players where spid=?',(spid,)).fetchone()
  assert all(a==z for field,a,z in zip(columns,old,new) if field not in fields)
 where=','.join(str(i) for i in allowed)
 assert not db.execute(f'select * from old.players where spid not in ({where}) except select * from main.players limit 1').fetchone()
 for (table,) in db.execute("select name from old.sqlite_master where type='table'"):
  if table=='players':continue
  assert not db.execute(f'select * from old."{table}" except select * from main."{table}" limit 1').fetchone()
  assert not db.execute(f'select * from main."{table}" except select * from old."{table}" limit 1').fetchone()
big=O/'data_0.big';shutil.copyfile(original_big,big);dec=bytes(decrypt.decrypt(b.read(original_big,codec.MEMBER)));plain=(O/'fifadb.sqlite').read_bytes();encoded=encrypt(dec[:16]+plain[16:]);replace(big,codec.MEMBER,refpack(encoded),len(encoded))
assert b'SQLite format 3\0'+bytes(decrypt.decrypt(b.read(big,codec.MEMBER)))[16:]==plain
old=b.entries(original_big);new=b.entries(big);assert len(old)==len(new)==271 and all(a[1]+a[2]<=z[1] for a,z in zip(new,new[1:]))
with original_big.open('rb') as a,big.open('rb') as z:
 for x,y in zip(old,new):
  assert x[0]==y[0]
  if x[0]!=codec.MEMBER:a.seek(x[1]);z.seek(y[1]);assert a.read(x[2])==z.read(y[2]),x[0]
assert codec.sha(original_db)==initial_db and codec.sha(original_big)==initial_big
report=dict(status='PRIVATE_APPEARANCE_CALIBRATION_CANDIDATE_NOT_INSTALLED',source_sqlite_sha256=initial_db,source_data0_sha256=initial_big,sqlite_sha256=codec.sha(O/'fifadb.sqlite'),data0_sha256=codec.sha(big),changed_spids=sorted(allowed),appearance_review_sha256=codec.sha(R/'appearance-review.json'),non_target_compressed_members_identical=270,all_nonappearance_player_columns_identical=True,other_tables_identical=True,native_verified=False,production_written=False)
(O/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report))
