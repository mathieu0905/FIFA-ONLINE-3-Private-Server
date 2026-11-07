"""Read-only verification of nine original-missing identities in the current release."""
from pathlib import Path
import sys,json,hashlib,sqlite3,subprocess
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path[:0]=['D:/FO3ID/server/tools/re','D:/FO3ID/server',str(W/'work/face_asset_mapping_v2/analysis_deps')]
import bigdir,extract_fifadb
from lupa.lua51 import LuaRuntime
C=Path('D:/FO3ID/32795');S=Path('D:/FO3ID/server');MODEL=Path('D:/FO3QA/modern_player_integration_v2/model19-v4')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
catalog=json.loads((MODEL/'model_catalog24.json').read_text('utf8'))
rows=[r for r in catalog['players'] if r['existing_db_rows']==0];assert len(rows)==9
before=sha(C/'data/data_0.big');server_before=sha(S/'gamedata/fifadb.sqlite')
db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
raw=bytes(extract_fifadb.decrypt(bigdir.read(C/'data/data_0.big','data/db2/fifadb.db.db2')))
assert hashlib.sha256(b'SQLite format 3\0'+raw[16:]).hexdigest()==server_before
lua_source=bigdir.read(C/'data/data_0.big','data/fifarna/lua/assets/player.lua')
assert hashlib.sha256(lua_source).hexdigest()==sha(MODEL/'lua/player-modern.lua')
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute("_input={};_state={};gSportsRNA={GetTable=function(self,name,idx) if name=='wvState' then return _state end return _input end,GetInt=function(self,t,k) return t[k] or 0 end,GetFloat=function(self,t,k) return t[k] or 0 end}")
lua.execute(lua_source.decode('latin1'))
language={}
for lang in ['eng','chi','ind','kor','tha','vie']:
 raw=bytes(extract_fifadb.decrypt(bigdir.read(C/'data/data_0.big',f'data/db2/{lang}.db.db2')))
 con=sqlite3.connect(':memory:');con.deserialize(b'SQLite format 3\0'+raw[16:]);language[lang]=con
results=[]
for row in rows:
 pid=row['playerid'];spid=row['local_spid'];selector=row['reserved_head_selector']
 actual=db.execute('select playerid,headtypecode,headclasscode from players where spid=?',(spid,)).fetchone()
 assert actual==(pid,selector,1),(pid,actual)
 names={lang:con.execute('select full,short from names where playerid=?',(pid,)).fetchone() for lang,con in language.items()}
 assert all(names.values()),(pid,names)
 assert names['chi'][0]==row['name_zh'],(pid,names['chi'],row['name_zh'])
 portraits=[]
 for prefix in ['_cache/games/fo3id','_cache/cdn']:
  path=C/prefix/'externalAssets/players'/f'p{spid}.png';assert path.is_file();portraits.append(dict(path=str(path),sha256=sha(path)))
 assert portraits[0]['sha256']==portraits[1]['sha256']
 lua.globals()['_input']=lua.table_from(dict(playerassetid=pid,playerHead=selector,playerHeadClass=1,faceProxyHeadClass=1,eyeColor=9))
 lua.execute('db={player={[0]={}}};PlayerUpdate(0)');mapped=dict(lua.globals().db.player[0].items())
 assert all(mapped.get(k)==pid for k in ['playerassetid','head','hair','faceType']),(pid,mapped)
 assert mapped['headClass']==mapped['faceProxyHeadClass']==0 and mapped['eyeColor']==9
 assert lua.globals().GetFaceTexTemplate(0)==f'data/sceneassets/faces/face_{pid}_0_0_0_0_0_0_0_0_textures.rx3'
 results.append(dict(playerid=pid,spid=spid,name_zh=row['name_zh'],selector=selector,db_row=actual,names=names,portraits=portraits,lua51_resolved_fields={k:mapped[k] for k in ['playerassetid','head','hair','faceType','headClass','faceProxyHeadClass','eyeColor']},native_near_verified=False,native_far_verified=False,native_match_verified=False))
assert sha(C/'data/data_0.big')==before and sha(S/'gamedata/fifadb.sqlite')==server_before
guard=S/'tools/player_import/check.py'
assert guard.is_file(),'Full native player import guard must be installed; the old nine-player UI-only check is insufficient'
checked=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(guard),'--server',str(S),'--client',str(C)],check=True,capture_output=True,text=True)
import_gate=json.loads(checked.stdout)
report=dict(status='PASS_CURRENT_DATA_LUA51_AND_IMPORT_GATE_NATIVE_PARTIAL',identities=results,full_import_gate=import_gate,client_data0_sha256=before,server_sqlite_sha256=server_before,lua_sha256=hashlib.sha256(lua_source).hexdigest(),production_written=False,original_missing_identity_count=9,native_verified=False,native_limit='Bellingham home dribbling human-confirmed separately; all other native scenes remain individually pending')
(ROOT/'integration-PASS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status=report['status'],original_missing_identity_count=9,playerids=[r['playerid'] for r in results]),ensure_ascii=False))
