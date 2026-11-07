"""Verify the native DB/resource path using work artifacts; never publish partial facts."""
from pathlib import Path
from contextlib import closing
import importlib.util,json,shutil,sqlite3,sys,tempfile
import prepare as p
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def main():
 sys.path.insert(0,str(p.S/'tools/re'));import bigdir,refpack
 codec=load(p.S/'extract_fifadb.py','all_custom_history_codec');ordered=load(p.P.parent/'global-player-editor/ordered_big.py','all_custom_history_ordered')
 from cryptography.hazmat.primitives.ciphers import Cipher,modes
 from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
 plan=p.build_plan();before=p.sha(p.C/'data/data_0.big');db_before=p.sha(p.S/'gamedata/fifadb.sqlite');out=p.P/'resource-verification';out.mkdir(exist_ok=True)
 target=out/'fifadb.sqlite';p.apply_database(plan,target);archive=out/'data_0.big';shutil.copyfile(p.C/'data/data_0.big',archive)
 def encode(original,plain):
  decoded=bytes(codec.decrypt(original));encoder=Cipher(Blowfish(codec.KEY),modes.ECB()).encryptor();return codec.swap32(encoder.update(codec.swap32(decoded[:16]+plain[16:]))+encoder.finalize())
 main_member='data/db2/fifadb.db.db2';decoded=bytes(codec.decrypt(bigdir.read(archive,main_member)));assert b'SQLite format 3\0'+decoded[16:]==(p.S/'gamedata/fifadb.sqlite').read_bytes()
 encrypted=encode(bigdir.read(archive,main_member),target.read_bytes());ordered.replace_member(archive,main_member,refpack.refpack(encrypted),len(encrypted));changed={main_member}
 languages={}
 for lang in ('eng','chi','ind','kor','tha','vie'):
  member=f'data/db2/{lang}.db.db2';original=bigdir.read(archive,member);decoded=bytes(codec.decrypt(original));path=out/f'{lang}.sqlite';path.write_bytes(b'SQLite format 3\0'+decoded[16:])
  with closing(sqlite3.connect(path)) as db:
   with db:
    assert db.execute('select 1 from team where teamid=?',(p.CHINA_TEAM,)).fetchone() is None
    db.execute('insert into team(teamid,teamname,leagueid) values(?,?,?)',(p.CHINA_TEAM,'中国明日之星',2028))
   assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  encrypted=encode(original,path.read_bytes());ordered.replace_member(archive,member,refpack.refpack(encrypted),len(encrypted));changed.add(member);languages[lang]=dict(teamid=p.CHINA_TEAM,name='中国明日之星')
 for member in changed:
  expected=target if member==main_member else out/(member.split('/')[-1].split('.')[0]+'.sqlite')
  assert b'SQLite format 3\0'+bytes(codec.decrypt(bigdir.read(archive,member)))[16:]==expected.read_bytes()
 layout=load(p.S/'tools/check_data0_layout.py','all_custom_history_layout').inspect(archive,p.C/'data/data_0.big',changed,len(bigdir.entries(p.C/'data/data_0.big')));assert layout['status']=='PASS'
 # Full native identity/model/name checker remains required despite this change
 # not importing any native player identity or touching model files.
 checker=load(p.S/'tools/player_import/check.py','all_custom_history_checker');certificate=checker.validate(p.S,p.C,database=target,data0=archive,registry=p.S/'gamedata/custom_rosters.json',full=True);assert certificate['status']=='PLAYER_IMPORT_FULL_PASS'
 with closing(sqlite3.connect((p.S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as db:metadata=dict(db.execute('select key,value from metadata'))
 fair=load(p.S/'fair_value_model.py','all_custom_history_fair');config=json.loads(metadata['fair_model_json'])
 original_profiles=fair.catalogue_rows(p.S/'gamedata/fifadb.sqlite',config);new_profiles=fair.catalogue_rows(target,config);assert fair.profile_digest(original_profiles,config)==fair.profile_digest(new_profiles,config)
 assert p.sha(p.C/'data/data_0.big')==before and p.sha(p.S/'gamedata/fifadb.sqlite')==db_before
 report=dict(status='CORE_RESOURCE_VERIFICATION_PASS',source_plan_status=plan['status'],ready_to_install=False,full_career_review_complete=False,database_sha256=p.sha(target),big_sha256=p.sha(archive),changed_members=sorted(changed),layout=layout,languages=languages,full_player_import=certificate,fair_value_profile_unchanged=True,formal_files_written=False,GUI_used=False,native_match_verified=False)
 p.source.write(out/'verification.json',report);print(json.dumps({k:report[k] for k in ('status','source_plan_status','ready_to_install','fair_value_profile_unchanged','formal_files_written')}))
if __name__=='__main__':main()
