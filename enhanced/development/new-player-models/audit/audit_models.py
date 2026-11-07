"""Offline artifact audit. Never opens a live application or writes installed resources."""
from pathlib import Path
import ast,collections,hashlib,json,struct,sys,sqlite3
ROOT=Path(__file__).resolve().parent
Q=Path('D:/FO3QA/modern_player_integration_v2')
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path.insert(0,'D:/FO3ID/server/tools/re');import bigdir
import zlib
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(name,data):(ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
# Reuse only the existing decoder functions; importing that script would execute its producer.
parser=W/'work/modern_player_integration_v2/inspect_rx3_headers.py'
module=ast.parse(parser.read_text('utf8'));scope={'struct':struct,'zlib':zlib,'hashlib':hashlib}
for node in module.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['unpack','inspect']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),str(parser),'exec'),scope)
catalog=json.loads((Q/'model19-v4/model_catalog24.json').read_text('utf8'))
players=[r for r in catalog['players'] if r['existing_db_rows']==0];assert len(players)==9
journal_root=Q/'qa-overlays/ggmu-bellingham-focused';journal=json.loads((journal_root/'journal.json').read_text('utf8'))
archives={}
for index in [3,4,6]:
 row=next(x for x in journal['entries'] if Path(x['target']).name==f'data_{index}.big')
 before=journal_root/row['backup'];assert sha(before)==row['before_sha256']
 archives[index]={'path':str(before),'sha256':row['before_sha256'],'entries':{r[0]:r for r in bigdir.entries(before)}}
original_data0=next(x for x in journal['entries'] if Path(x['target']).name=='data_0.big')
original_archive=journal_root/original_data0['backup'];assert sha(original_archive)==original_data0['before_sha256']
sys.path.insert(0,'D:/FO3ID/server');import extract_fifadb
decrypted=bytes(extract_fifadb.decrypt(bigdir.read(original_archive,'data/db2/fifadb.db.db2')))
plain_database=b'SQLite format 3\0'+decrypted[16:]
original_db=sqlite3.connect(':memory:');original_db.deserialize(plain_database)
original_db_rows=original_db.execute('select count(*) from players').fetchone()[0]
assert original_db_rows==60177
for row in players:assert original_db.execute('select count(*) from players where playerid=?',(row['playerid'],)).fetchone()[0]==0
original_db.close()
def folder(name):
 if name.startswith('head_'):return 4,'heads'
 if name.startswith('face_'):return 3,'faces'
 if name.startswith('hairlod_'):return 6,'hairlod'
 if name.endswith('_textures.rx3') and name.startswith('hair_'):return 4,'hair'
 if name.startswith('hair_'):return 4,'hair'
 raise ValueError(name)
reference=[]
for rel,index in [('heads/head_231747_0.rx3',4),('faces/face_231747_0_0_0_0_0_0_0_0_textures.rx3',3),('hair/hair_231747_0_0.rx3',4),('hair/hair_231747_0_textures.rx3',4),('hairlod/hairlod_231747_0_0.rx3',6)]:
 raw=bigdir.read(Path(archives[index]['path']),'data/sceneassets/'+rel)
 info=scope['inspect']('original_mbappe/'+rel,raw)
 plain,_=scope['unpack'](raw)
 info['section_type_histogram']=dict(collections.Counter(s['type'] for s in info['sections']))
 info['section_prefixes']=[dict(type=s['type'],prefix=plain[s['offset']:s['offset']+min(48,s['size'])].hex()) for s in info['sections']]
 reference.append(info)
reports=[]
for row in players:
 pid=row['playerid'];assets=[]
 for name,meta in row['acquired_model']['required_files'].items():
  path=Path(meta['path']);assert path.is_file() and sha(path)==meta['sha256'],str(path)
  raw=path.read_bytes();info=scope['inspect'](f'{pid}/{name}',raw);plain,_=scope['unpack'](raw)
  index,subfolder=folder(name);member='data/sceneassets/'+subfolder+'/'+name
  assert member not in archives[index]['entries'],member+' already existed in original'
  target=Q/f'model19-v4/archives/data_{index}.big';actual=bigdir.read(target,member)
  assert actual==raw,member+' package differs from selected source'
  installed=Path(f'D:/FO3ID/32795/data/data_{index}.big');installed_payload=bigdir.read(installed,member)
  assert installed_payload==raw,member+' installed payload differs from selected source'
  fourcc={v.decode('ascii'):plain.count(v) for v in [b'DXT1',b'DXT3',b'DXT5',b'ATI2',b'DDS '] if v in plain}
  info.update(source_path=str(path),source_sha256=meta['sha256'],original_member_present=False,archive_index=index,member=member,packaged_payload_matches_source=True,
   installed_archive=str(installed),installed_payload_sha256=hashlib.sha256(installed_payload).hexdigest(),installed_payload_matches_source=True,
   section_type_histogram=dict(collections.Counter(s['type'] for s in info['sections'])),literal_texture_markers=fourcc,
   section_prefixes=[dict(type=s['type'],prefix=plain[s['offset']:s['offset']+min(48,s['size'])].hex()) for s in info['sections']],
   skeleton_or_mesh_semantics_verified=False)
  assets.append(info)
 portrait=Q/f'native24-model19-v4/assets/players/p{row["local_spid"]}.png';png=portrait.read_bytes();assert png[:8]==b'\x89PNG\r\n\x1a\n';width,height=struct.unpack('>II',png[16:24])
 reports.append(dict(playerid=pid,spid=row['local_spid'],name_zh=row['name_zh'],name_en=row['name_en'],original_db_rows=row['existing_db_rows'],reserved_head_selector=row['reserved_head_selector'],
  source=row['acquired_model']['source'],provenance=row['acquired_model']['provenance'],files=assets,
  portrait=dict(path=str(portrait),sha256=sha(portrait),width=width,height=height),
  status='SOURCE_PACKAGE_AND_INSTALLED_PAYLOAD_INTEGRITY_PASS_NATIVE_PENDING',native_near_viewer_verified=False,native_far_lod_verified=False,native_match_verified=False,
  limits=['RX3 version and bounded sections prove format integrity only.','No decoded mesh, skin weights, bone hierarchy or material binding proof.','Native Mbappe type overlap does not establish compatibility.','Author supplied eyes/bump may require distinct mapping; common native eye assets were not replaced.']))
save('original-native-reference.json',reference)
report=dict(status='NINE_ORIGINALLY_ABSENT_PLAYERS_45_ASSETS_AUDITED',players=reports,
 original_archives={str(k):{x:v[x] for x in ['path','sha256']} for k,v in archives.items()},
 catalog=str(Q/'model19-v4/model_catalog24.json'),catalog_sha256=sha(Q/'model19-v4/model_catalog24.json'),decoder_source=str(parser),decoder_source_sha256=sha(parser),
 original_database=dict(archive=str(original_archive),archive_sha256=original_data0['before_sha256'],sqlite_sha256=hashlib.sha256(plain_database).hexdigest(),rows=original_db_rows,nine_player_ids_absent=True),
 production_written=False,runtime_observed=False,mesh_skeleton_material_compatibility_proven=False)
save('audit.json',report)
summary=[f"{r['name_zh']}: 5/5 sources and packaged bytes match; 0/5 original exact member paths; selector {r['reserved_head_selector']}; native pending" for r in reports]
(ROOT/'summary.txt').write_text('\n'.join(summary)+'\n\nOffline header/section checks are not geometry/skeleton/material or game-load validation.\n',encoding='utf8')
print(json.dumps(dict(status=report['status'],players=len(reports),files=sum(len(r['files']) for r in reports),source_and_package_integrity=True,original_exact_members_present=0,native_verified=False),ensure_ascii=False))
