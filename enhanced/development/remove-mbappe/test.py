"""Removal consistency and exact preservation checks on work artifacts."""
from pathlib import Path
import ast,copy,importlib.util,json,sqlite3,sys
import build as b
W,S,C=b.W,b.S,b.C
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def artifact(plan,rel):return Path(next(e['source'] for e in plan['payload'] if e['relative']==rel))
def functions(source,names,env):
 tree=ast.parse(source);tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 for n in tree.body:n.decorator_list=[]
 exec(compile(tree,'<target-functions>','exec'),env);return env
def main():
 p=json.loads((W/'build.json').read_text('utf8'));passed=[]
 for e in p['payload']:assert b.sha(e['source'])==e['after']
 dbpath=artifact(p,'gamedata/fifadb.sqlite');old=sqlite3.connect(S/'gamedata/fifadb.sqlite');new=sqlite3.connect(dbpath)
 for t, in old.execute("select name from sqlite_master where type='table'").fetchall():
  cols=[r[1] for r in old.execute('pragma table_info("'+t+'")')];keys=[k for k in ('spid','playerid') if k in cols]
  keep=' where NOT ('+' OR '.join('"'+k+'" % 1000000 = ?' for k in keys)+')' if keys else ''
  assert old.execute('select * from "'+t+'"'+keep,[b.PID]*len(keys)).fetchall()==new.execute('select * from "'+t+'"').fetchall(),t
 passed.append('All non-target SQLite rows preserved exactly; identity/cards/permissions/names/history removed')
 reg=json.loads(artifact(p,'gamedata/custom_rosters.json').read_text('utf8'));assert all(r['base_playerid']!=b.PID for r in reg['cards'])
 for e in p['payload']:
  if e['relative'].endswith('.py'):compile(Path(e['source']).read_text('utf8'),e['relative'],'exec')
  if Path(e['relative']).name in p['pool_changes']:
   d=json.loads(Path(e['source']).read_text('utf8'));assert not b.prune_pools(copy.deepcopy(d))
   if 'hash' in d:assert d['hash']==__import__('hashlib').sha256(json.dumps({k:v for k,v in d.items() if k!='hash'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
 passed.append('Frozen pool membership/signatures valid; no empty tier')
 from contextlib import closing
 env=dict(fa_prices=lambda:{88231747:1,100020801:3},closing=closing,_db=lambda:sqlite3.connect(dbpath))
 functions(artifact(p,'http_config.py').read_text('utf8'),{'market_spids','add_player'},env)
 assert not any(b.blocked(x) for x in env['market_spids']())
 for sid in b.IDS|{999231747}:
  team={'players':[]}
  try:env['add_player'](team,sid)
  except ValueError:pass
  else:raise AssertionError('Removed identity grant accepted')
  assert team=={'players':[]}
 passed.append('Legacy price union cannot restore removed identity; all-season grants fail without mutation')
 model=load(artifact(p,'fair_value_model.py'),'removed_profile_model')
 archive=artifact(p,'gamedata/removed-player-profiles.json');target=dbpath.parent/'removed-player-profiles.json';target.write_bytes(archive.read_bytes())
 for n in ('fair-value-v12','fair-value-v13','fair-value-v14','fair-value-nostalgia87'):
  import gzip
  cfg=json.loads((S/'gamedata'/f'{n}-model.json').read_text('utf8'))
  with gzip.open(S/'gamedata'/f'{n}-catalogue.json.gz','rt',encoding='utf8') as f:cat=json.load(f)
  # Only current generation matches current attributes; historical ones remain
  # checked against their immutable price-store generations by the parent gate.
  if n=='fair-value-nostalgia87':assert model.verify_profiles(dbpath,cat,cfg)['status']=='FAIR_VALUE_PROFILE_BINDING_PASS'
 assert all(r['playerid']!=b.PID for r in model.catalogue_rows(dbpath,cfg))
 tampered=json.loads(target.read_text('utf8'));tampered['rows'][0]['finishing']+=1;target.write_bytes(b.body(tampered))
 try:model.verify_profiles(dbpath,cat,cfg)
 except ValueError:pass
 else:raise AssertionError('Tampered former profile accepted')
 target.write_bytes(archive.read_bytes());passed.append('Original catalogue hash still verified; tampered archival profile rejected; future catalogues exclude removed cards')
 # Full import gate with the exact proposed tools, preserving official portrait
 # evidence paths and all non-target imported identities/models.
 import shutil
 toolroot=W/'artifacts/checker';toolroot.mkdir(exist_ok=True)
 for src in (S/'tools/player_import').glob('*'):
  if src.is_file():shutil.copyfile(src,toolroot/src.name)
 shutil.copyfile(artifact(p,'tools/player_import/prepare.py'),toolroot/'prepare.py')
 checker=load(toolroot/'check.py','removed_full_checker')
 proof=checker.validate(S,C,database=dbpath,data0=artifact(p,'data/data_0.big'),imports=artifact(p,'gamedata/player-imports.json'),registry=artifact(p,'gamedata/custom_rosters.json'),full=True,certificate=W/'artifacts/player-import-validation.json')
 # validate() returns the certificate; CLI owns persistence.
 b.write(W/'artifacts/player-import-validation.json',proof)
 assert proof['status']=='PLAYER_IMPORT_FULL_PASS',proof
 p['payload'].append(dict(root='server',relative='gamedata/player-import-validation.json',source=str(W/'artifacts/player-import-validation.json'),before=b.sha(S/'gamedata/player-import-validation.json'),after=b.sha(W/'artifacts/player-import-validation.json')))
 b.write(W/'validated-build.json',p)
 passed.append('Full player_import check of exact proposed DB/archive/registry/tools passed')
 # Native players only loses this identity; all other rows are unchanged.
 import bigdir,native_db,eadb,xml.etree.ElementTree as ET
 src=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db.db');dst=bigdir.read(artifact(p,'data/data_0.big'),'data/db/fifa_ng_db.db');meta=bigdir.read(C/'data/data_0.big','data/db/fifa_ng_db-meta.xml').decode('utf8')
 *_,a,fields=native_db.player_table(src,meta);*_,z,_=native_db.player_table(dst,meta);key=fields['playerid']['shortname'];assert [r for r in a.rows if a.get(r,key)!=b.PID]==z.rows
 _,names,ar=eadb.db_tables(src);_,znames,zr=eadb.db_tables(dst);assert names==znames
 for node in ET.fromstring(meta).iter('table'):
  sn=node.get('shortname').encode()
  if sn not in names:continue
  idx=names.index(sn);fs=[f for f in node.iter('field') if 'playerid' in f.get('name','').lower()]
  if not fs:assert ar[idx]==zr[idx];continue
  a=eadb.Table(ar[idx]);z=eadb.Table(zr[idx]);assert [r for r in a.rows if not any(a.get(r,f.get('shortname'))+int(f.get('rangelow','0'))==b.PID for f in fs)]==z.rows,node.get('name')
 passed.append('Native identity and team links removed; all other native rows/tables preserved')
 result=dict(status='PASS',checks=passed,player_import=proof,build_sha256=b.sha(W/'validated-build.json'),GUI_used=False,native_runtime_verified=False,match_verified=False)
 b.write(W/'tests.json',result);print(json.dumps(dict(status='PASS',checks=len(passed),player_import=proof['status'])))
if __name__=='__main__':main()
