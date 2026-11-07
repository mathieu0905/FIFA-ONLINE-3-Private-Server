"""Prepare a private save using current production code and installed client assets."""
from pathlib import Path
import json,hashlib,shutil,datetime,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
Q=Path('D:/FO3QA/modern_player_integration_v2/private-servers')
name='model9-main-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
O=Q/name;assert not O.exists();O.mkdir()
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
files=list(S.glob('*.py'))+[S/'server_display_zh.json']
for folder in ['admin','responses','certs','patches','player_editor','tools/re']:
 files.extend(p for p in (S/folder).rglob('*') if p.is_file() and p.suffix.lower() in ['.py','.json','.html','.htm','.css','.js','.pem','.txt','.png','.big'])
files.extend(p for p in (S/'gamedata').glob('*.json') if '.before' not in p.name)
files.append(S/'gamedata/fifadb.sqlite')
hashes={p.relative_to(S).as_posix():sha(p) for p in files}
assert len(hashes)==len(files)
for p in files:
 t=O/p.relative_to(S);t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,t)
 assert sha(t)==hashes[p.relative_to(S).as_posix()]
assert all(sha(S/relative)==value for relative,value in hashes.items()),'Production changed during snapshot; prepare a new session at the GUI handoff boundary'
st=json.loads((O/'gamedata/state.json').read_text('utf8'))
assert any(c.get('name')=='ggmu' and c.get('slot')==0 for c in st['coaches'])
client={}
for relative in ['data/data_0.big','data/data_3.big','data/data_4.big','data/data_6.big']:
 client[relative]=sha(Path('D:/FO3ID/32795')/relative)
meta=dict(status='PREPARED_NO_LISTENERS',private_server=str(O),production_code_hashes=hashes,current_client_hashes=client,production_written=False,game_started=False,fixture_written_to_production=False,private_coach='ggmu',private_test_playerids=[243715,252371,251854,256790,256630,238794,246669,277643,257534])
(O/'model-session.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
(R/'current-native-session.json').write_text(json.dumps(dict(private_server=str(O),metadata=str(O/'model-session.json')),indent=2),encoding='utf8')
print(json.dumps(dict(status=meta['status'],private_server=str(O),copied_files=len(files)),ensure_ascii=False))
