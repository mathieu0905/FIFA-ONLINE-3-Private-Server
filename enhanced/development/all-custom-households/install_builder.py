"""Fresh direct-install artifacts for the verified subset explicitly authorized by user.

Unmapped clubs remain pending: never assign guessed IDs or publish the old
resource-verification artifact. This builds fresh against the current production.
"""
from pathlib import Path
from collections import defaultdict
from contextlib import closing
import ast,datetime,gzip,hashlib,importlib.util,json,shutil,sqlite3,sys
import prepare as p
P,S,C=p.P,p.S,p.C
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def write(path,data):p.source.write(path,data)
def jsonbody(data):return (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def main():
 out=P/('build-install-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));out.mkdir()
 watched=[S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/custom_rosters.json',S/'server_display_zh.json',S/'responses/static_roster.json',S/'play-local.bat',S/'http_config.py',S/'fair_value_model.py',S/'tools/player_import/check.py',P/'club-mapping.json',P/'prepare.py',Path(__file__)]
 baseline={str(f):p.sha(f) for f in watched};plan=p.build_plan();active={c['base_playerid'] for c in p.source.read(S/'gamedata/custom_rosters.json')['cards']};mapping=p.source.read(P/'club-mapping.json')
 sys.path.insert(0,str(S/'tools/re'));import bigdir,refpack
 codec=load(S/'extract_fifadb.py','install_household_codec');ordered=load(P.parent/'global-player-editor/ordered_big.py','install_household_ordered')
 parser=load(P.parent/'club-history/collect.py','install_household_nexon');wiki=load(P/'wiki_careers.py','install_household_wiki')
 member='data/ui/localization/TEAMNAMES_ENG.json';labels=json.loads(bigdir.read(C/'data/ui/localization/eng.big',member));ea_leagues={}
 for file in (p.source.SRC).glob('ea-*.json'):
  for r in p.source.read(file).get('items',[]):
   if r.get('team') and r.get('gender',{}).get('id')==0:
    tid=str(r['team']['id']);labels.setdefault(tid,r['team']['label'])
    if r.get('league'):ea_leagues[int(tid)]=r['league']['id']
 labels[str(p.CHINA_TEAM)]='中国明日之星'
 old=defaultdict(list)
 with closing(sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
  for pid,_,tid,j,e,l in db.execute('select * from playerhistory order by playerid,ordernum'):old[pid].append((tid,j,e,l))
 incoming=defaultdict(set);source_hashes={};deferred=[];verified_wiki={}
 for file in (p.source.SRC/'wiki').glob('*.json'):
  if not file.stem.isdigit() or int(file.stem) not in active:continue
  r=p.source.read(file)
  if r.get('status')!='OK':continue
  raw=gzip.decompress(Path(r['raw_file']).read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256']
  dob,career,_=wiki.parse(raw);assert career==r['career'] and dob==r['source_dob'],file
  if dob!=r['expected_dob']:assert r.get('identity_review'),file
  verified_wiki[r['playerid']]=r;source_hashes[str(file)]=p.sha(file)
 for row in mapping['resolved']:
  pid=row['playerid'];tid=int(row['teamid'])
  if pid not in active or pid not in verified_wiki:continue
  fields=('club_name','wiki_title','joinedyear','endyear','loan','youth','source_field')
  assert any(all(row.get(k)==x.get(k) for k in fields) for x in verified_wiki[pid]['career']),row
  if row['basis']=='independent career alignment' or str(tid) not in labels:
   deferred.append(row);continue
  incoming[pid].add((tid,row['joinedyear'],row['endyear'],row['loan']))
 links={r['playerid']:r for r in p.source.read(p.source.SRC/'identity-links.json')}
 for file in (p.source.SRC/'careers').glob('*.json'):
  r=p.source.read(file);pid=r['playerid']
  if r.get('status')!='OK' or pid not in active:continue
  raw=gzip.decompress(Path(r['raw_file']).read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256'] and parser.parse(raw.decode('utf-8-sig'))==r['career'],file
  assert int(r['source_spid'])%1000000==links[pid]['source_playerid'];source_hashes[str(file)]=p.sha(file)
  for spell in r['career']:
   tid=mapping['korean'].get(spell['club_ko'])
   if tid is not None and str(tid) in labels:incoming[pid].add((int(tid),spell['joinedyear'],spell['endyear'],spell['loan']))
 for r in plan['china_current_clubs']:
  if r['before']>0:incoming[r['spid']%1000000].add((r['before'],-1,-1,0))
 changes=[]
 for pid,rows in sorted(incoming.items()):
  known={r[0] for r in old[pid]};added=sorted({r for r in rows if r[0] not in known},key=lambda r:(r[1],r[0],r[2],r[3]))
  if added:changes.append(dict(playerid=pid,before=old[pid],after=old[pid]+added,added_clubs=sorted({r[0] for r in added})))
 plan.update(history_changes=changes,status='READY_VERIFIED_SUBSET_SOURCE_REVIEW_REMAINS',unverified_rows_excluded=deferred,source_record_hashes=source_hashes)
 write(out/'plan.json',plan);dbpath=out/'fifadb.sqlite';p.apply_database(plan,dbpath)
 archive=out/'data_0.big';shutil.copyfile(C/'data/data_0.big',archive)
 from cryptography.hazmat.primitives.ciphers import Cipher,modes
 from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
 def replace_db(member,path):
  original=bytes(codec.decrypt(bigdir.read(archive,member)));plain=path.read_bytes();encoder=Cipher(Blowfish(codec.KEY),modes.ECB()).encryptor();encrypted=codec.swap32(encoder.update(codec.swap32(original[:16]+plain[16:]))+encoder.finalize());ordered.replace_member(archive,member,refpack.refpack(encrypted),len(encrypted));assert b'SQLite format 3\0'+bytes(codec.decrypt(bigdir.read(archive,member)))[16:]==plain
 mainmember='data/db2/fifadb.db.db2';assert b'SQLite format 3\0'+bytes(codec.decrypt(bigdir.read(archive,mainmember)))[16:]==(S/'gamedata/fifadb.sqlite').read_bytes();replace_db(mainmember,dbpath);changed={mainmember}
 needed={r[0] for change in changes for r in change['after'] if r[0] in change['added_clubs']}|{p.CHINA_TEAM};lang_changes={}
 for lang in ('eng','chi','ind','kor','tha','vie'):
  name=f'data/db2/{lang}.db.db2';raw=bytes(codec.decrypt(bigdir.read(archive,name)));f=out/f'{lang}.sqlite';f.write_bytes(b'SQLite format 3\0'+raw[16:]);added=[]
  with closing(sqlite3.connect(f)) as db:
   with db:
    for tid in sorted(needed):
     if not db.execute('select 1 from team where teamid=?',(tid,)).fetchone():db.execute('insert into team(teamid,teamname,leagueid) values(?,?,?)',(tid,labels[str(tid)],ea_leagues.get(tid,2028)));added.append(tid)
    assert db.execute('select teamname from team where teamid=?',(p.CHINA_TEAM,)).fetchone()==('中国明日之星',)
   assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  replace_db(name,f);changed.add(name);lang_changes[lang]=added
 layout=load(S/'tools/check_data0_layout.py','install_household_layout').inspect(archive,C/'data/data_0.big',changed,len(bigdir.entries(C/'data/data_0.big')));assert layout['status']=='PASS';write(out/'layout.json',layout)
 payloads=[dict(root='server',relative='gamedata/fifadb.sqlite',source=str(dbpath)),dict(root='client',relative='data/data_0.big',source=str(archive))]
 # Keep the user's existing strength ordering: place only the new 25U season
 # by mean native positional ability, preserving every pre-existing entry/order.
 roster=p.source.read(S/'responses/static_roster.json');ucl=[r for r in roster['seasons'] if r.get('value')==[856]]
 if ucl:
  assert len(ucl)==1
  tree=ast.parse((S/'http_config.py').read_text('utf8'));weights=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLE_WEIGHTS' for t in n.targets));roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split();scores=defaultdict(list);fields=sorted(set().union(*(set(v) for v in weights.values())))
  with closing(sqlite3.connect(dbpath)) as db:
   db.row_factory=sqlite3.Row
   for row in db.execute('select spid,preferredposition1,'+','.join(fields)+' from players'):
    if 0<=row['preferredposition1']<len(roles):scores[row['spid']//1000000].append(sum(row[k]*v for k,v in weights[roles[row['preferredposition1']]].items())//100)
  def strength(entry):
   values=[n for sid in entry.get('value',[]) for n in scores.get(sid,[])]
   return sum(values)/len(values) if values else None
  previous=list(roster['seasons']);others=[r for r in previous if r.get('value')!=[856]];new_score=strength(ucl[0]);assert new_score is not None
  index=next((i for i,r in enumerate(others) if strength(r) is not None and new_score>strength(r)),len(others));roster['seasons']=others[:index]+ucl+others[index:]
  write(out/'static_roster.json',roster);write(out/'season-placement.json',dict(season=856,mean_native_primary=new_score,inserted_index=index,old_seasons_preserved=True,old_season_order_preserved=True,before=previous,after=roster['seasons']));payloads.append(dict(root='server',relative='responses/static_roster.json',source=str(out/'static_roster.json')))
 localized=[]
 for lang in ('eng','chi','ind','kor','tha','vie'):
  localized.append(('client',f'data/ui/localization/{lang}.big'))
  for rel in (f'patches/language_{lang}.big',):
   if (S/rel).exists():localized.append(('server',rel))
  for prefix in ('_cache/games/fo3id/externalAssets','_cache/cdn/externalAssets'):
   rel=f'{prefix}/language_{lang}.big'
   if (C/rel).exists():localized.append(('client',rel))
 for n,(root,rel) in enumerate(localized):
  original=(S if root=='server' else C)/rel;baseline[str(original)]=p.sha(original);target=out/f'localization-{n}.big';shutil.copyfile(original,target)
  members=[e[0] for e in bigdir.entries(target) if '/TEAMNAMES_' in e[0]]
  if not members:
   # External LANGUAGESTRING packages contain UI strings, not team-name
   # dictionaries. They must stay byte-identical, including installer hashes.
   assert all('/LANGUAGESTRING_' in e[0] for e in bigdir.entries(target)),rel
   continue
  for name in members:
   values=json.loads(bigdir.read(target,name));before=dict(values)
   for tid in sorted(needed):values.setdefault(str(tid),labels[str(tid)])
   values[str(p.CHINA_TEAM)]='中国明日之星';assert all(values[k]==v for k,v in before.items())
   body=jsonbody(values);ordered.replace_member(target,name,refpack.refpack(body),len(body));assert json.loads(bigdir.read(target,name))==values
  payloads.append(dict(root=root,relative=rel,source=str(target)))
 display=p.source.read(S/'server_display_zh.json');names=display['names_by_id']['TEAMNAMES_CHI.json']
 for tid in needed:names.setdefault(str(tid),labels[str(tid)])
 names[str(p.CHINA_TEAM)]='中国明日之星';write(out/'server_display_zh.json',display);payloads.append(dict(root='server',relative='server_display_zh.json',source=str(out/'server_display_zh.json')))
 checker=load(S/'tools/player_import/check.py','install_household_checker');cert=checker.validate(S,C,database=dbpath,data0=archive,full=True);assert cert['status']=='PLAYER_IMPORT_FULL_PASS';write(out/'player-import-validation.json',cert);payloads.append(dict(root='server',relative='gamedata/player-import-validation.json',source=str(out/'player-import-validation.json')))
 fair=load(S/'fair_value_model.py','install_household_fair')
 with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as db:config=json.loads(dict(db.execute('select key,value from metadata'))['fair_model_json'])
 assert fair.profile_digest(fair.catalogue_rows(dbpath,config),config)==fair.profile_digest(fair.catalogue_rows(S/'gamedata/fifadb.sqlite',config),config)
 for file,expected in baseline.items():assert p.sha(file)==expected,('Fresh baseline changed; rebuild',file)
 for record in payloads:record['sha256']=p.sha(record['source'])
 write(out/'payloads.json',payloads);write(out/'baseline.json',baseline)
 coverage=dict(registered_cards=plan['registered_cards'],identities=plan['identities'],enabled_history_cards=len(plan['history_permissions']),china_current_clubs=len(plan['china_current_clubs']),changed_players=len(changes),new_player_club_eligibilities=sum(len(r['added_clubs']) for r in changes),rows_before=sum(map(len,old.values())),rows_after=sum(map(len,old.values()))+sum(len(r['after'])-len(r['before']) for r in changes),source_record_count=len(source_hashes),pending_identities=len(plan['source_issues']),unmapped_clubs=len(plan['unresolved_clubs']),club_ids_registered_in_language_tables=sorted(needed),language_table_additions=lang_changes,all_original_club_eligibilities_preserved=True,all_card_attributes_unchanged=True,fair_value_profile_unchanged=True,unknown_club_ids_created=False,unverified_rows_excluded=len(deferred))
 write(out/'coverage-report.json',coverage);write(out/'player-changes.json',changes);write(out/'build-result.json',dict(status='BUILT_FOR_DIRECT_INSTALL',database_sha256=p.sha(dbpath),big_sha256=p.sha(archive),verified_subset=True,full_career_review_complete=False));write(P/'install-build-current.json',dict(build=str(out)))
 print(json.dumps(dict(build=str(out),coverage=coverage),ensure_ascii=True),flush=True)
if __name__=='__main__':main()
