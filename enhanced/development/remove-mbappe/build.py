"""Prepare removal from current official inputs, without writing official files."""
from pathlib import Path
import copy,hashlib,json,shutil,sqlite3,sys,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent; S=Path('D:/FO3ID/server'); C=Path('D:/FO3ID/32795')
sys.path[:0]=[str(S),str(S/'tools/re'),str(S/'tools/player_import')]
import bigdir,eadb,native_db,ordered_big,refpack,extract_fifadb as codec
from cryptography.hazmat.primitives.ciphers import Cipher,modes
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
IDS={231747,13231747,88231747,300231747};PID=231747
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def body(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def write(p,x):Path(p).write_bytes(body(x))
def blocked(v):
 try:return int(v)%1000000==PID
 except (ValueError,TypeError):return False
def seal(data):
 e=Cipher(Blowfish(codec.KEY),modes.ECB()).encryptor();b=codec.swap32(e.update(codec.swap32(data))+e.finalize());return refpack.refpack(b),len(b)
def cleanse_database(db):
 deleted={}
 for t, in db.execute("select name from sqlite_master where type='table'").fetchall():
  cols=[r[1] for r in db.execute('pragma table_info("'+t+'")')]
  keys=[k for k in ('spid','playerid') if k in cols]
  if not keys:continue
  cond=' OR '.join('"'+k+'" % 1000000 = ?' for k in keys)
  n=db.execute('delete from "'+t+'" where '+cond,[PID]*len(keys)).rowcount
  if n:deleted[t]=n
 db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
 return deleted
def prune_pools(x,path='',changes=None):
 if changes is None:changes=[]
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='pool' and isinstance(v,list) and all(isinstance(a,int) for a in v):
    new=[a for a in v if not blocked(a)]
    if new!=v:
     assert new,('Removal would empty product',path);changes.append(dict(path=path+'/'+k,removed=len(v)-len(new)));x[k]=new
   else:prune_pools(v,path+'/'+k,changes)
 elif isinstance(x,list):
  for i,v in enumerate(x):prune_pools(v,path+'/'+str(i),changes)
 return changes
def main():
 out=W/'artifacts';out.mkdir(exist_ok=True);baseline={};payload=[];report={}
 def stage(root,relative,data):
  src=(S if root=='server' else C)/relative; baseline[str(src)]=sha(src) if src.exists() else None
  target=out/(str(len(payload))+'-'+Path(relative).name);target.write_bytes(data)
  payload.append(dict(root=root,relative=relative,source=str(target),before=baseline[str(src)],after=sha(target)))
 original=S/'gamedata/fifadb.sqlite';baseline[str(original)]=sha(original);dbpath=out/'fifadb.sqlite';shutil.copyfile(original,dbpath)
 db=sqlite3.connect(dbpath);db.row_factory=sqlite3.Row
 archived=[dict(r) for r in db.execute('select * from players where playerid=?',(PID,))]
 assert {r['spid'] for r in archived}==IDS
 report['deleted_ui_rows']=cleanse_database(db);db.close()
 stage('server','gamedata/fifadb.sqlite',dbpath.read_bytes())
 # Exact former profiles keep immutable economic/trade evidence verifiable;
 # they never participate in game queries or future catalogue generation.
 stage('server','gamedata/removed-player-profiles.json',body(dict(schema=1,playerids=[PID],rows=archived)))
 reg=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'))
 oldcards=reg['cards'];reg['cards']=[r for r in oldcards if r['base_playerid']!=PID]
 reg['removed_players']=reg.get('removed_players',[])+[dict(playerid=PID,spids=sorted(IDS),reason='User requested removal from gameplay')]
 for season in reg['seasons']:
  for k,v in season.items():
   if isinstance(v,list) and all(isinstance(a,int) for a in v):season[k]=[a for a in v if not blocked(a)]
  if 'card_count' in season:season['card_count']=sum(1 for r in reg['cards'] if r['fo3_spid']//1000000==season['id'])
 stage('server','gamedata/custom_rosters.json',body(reg))
 policy=json.loads((S/'gamedata/player-imports.json').read_text('utf8'))
 for k,v in policy.items():
  if isinstance(v,list):policy[k]=[r for r in v if not (isinstance(r,int) and r==PID) and not (isinstance(r,dict) and (r.get('playerid')==PID or blocked(r.get('spid'))))]
 policy['native_template_playerid']=20801
 stage('server','gamedata/player-imports.json',body(policy))
 # Change the codec's row-layout template to another existing native identity.
 path=S/'tools/player_import/prepare.py';src=path.read_text('utf8');assert src.count('template=t.find(key,231747)')==1
 stage('server','tools/player_import/prepare.py',src.replace('template=t.find(key,231747)','template=t.find(key,20801)').encode('utf8'))
 # Stop fa_prices' legacy union from admitting removed identities; new grants
 # must also fail closed even if an old SKU or stale admin request names them.
 path=S/'http_config.py';src=path.read_text('utf8')
 assert src.count('return frozenset(own | set(fa_prices()))')==1
 src=src.replace('return frozenset(own | set(fa_prices()))','return frozenset(s for s in own | set(fa_prices()) if int(s) % 1000000 != 231747)')
 at='    with closing(_db()) as c:\n        r = c.execute("SELECT playerid FROM players WHERE spid = ?", (int(spid),)).fetchone()'
 assert src.count(at)==1
 src=src.replace(at,'    if int(spid) % 1000000 == 231747:\n        raise ValueError("Player removed from gameplay")\n'+at)
 stage('server','http_config.py',src.encode('utf8'))
 path=S/'fair_value_model.py';src=path.read_text('utf8')
 # Verification may merge only these exact 4 archived profiles; original
 # catalogue/profile digests still have to match, without changing history.
 at='def profile_digest(rows,config):';assert src.count(at)==1
 helper='''def verified_catalogue_rows(database,config):
 rows=catalogue_rows(database,config)
 archive=Path(database).parent/'removed-player-profiles.json'
 if archive.exists():
  packet=json.loads(archive.read_text('utf8'))
  former=packet['rows'];expected={231747,13231747,88231747,300231747}
  if packet.get('schema')!=1 or packet.get('playerids')!=[231747] or {r['spid'] for r in former}!=expected or len(former)!=4 or any(r['playerid']!=231747 for r in former):raise ValueError('Invalid removed-player profile archive')
  if any(r['playerid']==231747 or r['spid'] in expected for r in rows):raise ValueError('Removed player reintroduced into gameplay database')
  rows+=former
 return sorted(rows,key=lambda r:r['spid'])

'''
 src=src.replace(at,helper+at)
 src=src.replace(' rows=catalogue_rows(database,config)\n if profile_digest',' rows=verified_catalogue_rows(database,config)\n if profile_digest')
 stage('server','fair_value_model.py',src.encode('utf8'))
 path=S/'fair_value_store.py';src=path.read_text('utf8');src=src.replace('catalogue_rows,verify_profiles','catalogue_rows,verified_catalogue_rows,verify_profiles');assert 'verified_catalogue_rows' in src
 assert src.count('rows=catalogue_rows(self.source,self.model)')==1
 src=src.replace('rows=catalogue_rows(self.source,self.model)','rows=verified_catalogue_rows(self.source,self.model)')
 stage('server','fair_value_store.py',src.encode('utf8'))
 # Only pool contents change. Retain probability tier weights, enhancement
 # distribution, limits, prices, HMAC keys and completed transaction receipts.
 report['pool_changes']={}
 for path in (S/'gamedata').glob('*.json'):
  if path.name in ('state.json','shop.json'):continue
  try:d=json.loads(path.read_text('utf-8-sig'))
  except (ValueError,UnicodeError):continue
  changes=prune_pools(d)
  if changes:
   if isinstance(d,dict) and 'hash' in d:d['hash']=hashlib.sha256(json.dumps({k:v for k,v in d.items() if k!='hash'},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
   stage('server','gamedata/'+path.name,body(d));report['pool_changes'][path.name]=changes
 archive=C/'data/data_0.big';baseline[str(archive)]=sha(archive);replacements={}
 member='data/db2/fifadb.db.db2';raw=bytes(codec.decrypt(bigdir.read(archive,member)))
 replacements[member]=seal(raw[:16]+dbpath.read_bytes()[16:])
 report['deleted_language_rows']={}
 for lang in ('eng','chi','ind','kor','tha','vie'):
  member=f'data/db2/{lang}.db.db2';raw=bytes(codec.decrypt(bigdir.read(archive,member)))
  lc=sqlite3.connect(':memory:');lc.deserialize(b'SQLite format 3\0'+raw[16:]);report['deleted_language_rows'][lang]=cleanse_database(lc)
  replacements[member]=seal(raw[:16]+lc.serialize()[16:]);lc.close()
 member='data/db/fifa_ng_db.db';raw=bigdir.read(archive,member);meta=bigdir.read(archive,'data/db/fifa_ng_db-meta.xml').decode('utf8')
 _,_,_,idx,t,fields=native_db.player_table(raw,meta);key=fields['playerid']['shortname'];before=t.rows[:];t.find(key,20801)
 t.rows=[r for r in before if t.get(r,key)!=PID];assert len(before)-len(t.rows)==1
 native=native_db.rebuild(raw,idx,t)
 report['native_removed']={'players':1}
 for node in ET.fromstring(meta).iter('table'):
  fs=[f for f in node.iter('field') if 'playerid' in f.get('name','').lower()]
  if not fs or node.get('name')=='players':continue
  _,names,raws=eadb.db_tables(native)
  if node.get('shortname').encode() not in names:continue
  ni=names.index(node.get('shortname').encode());nt=eadb.Table(raws[ni]);original=nt.rows[:]
  nt.rows=[r for r in original if not any(nt.get(r,f.get('shortname'))+int(f.get('rangelow','0'))==PID for f in fs)]
  if len(nt.rows)!=len(original):
   report['native_removed'][node.get('name')]=len(original)-len(nt.rows);native=native_db.rebuild(native,ni,nt)
 replacements[member]=(refpack.refpack(native),len(native))
 result=ordered_big.rebuild(archive,out/'data_0.big',replacements);report['archive']=result
 payload.append(dict(root='client',relative='data/data_0.big',source=str(out/'data_0.big'),before=baseline[str(archive)],after=sha(out/'data_0.big')))
 assert all((sha(p) if Path(p).exists() else None)==v for p,v in baseline.items()),'Official baseline moved; rebuild'
 report.update(status='BUILT',payload=payload,baseline=baseline,gameplay_spids_removed=sorted(IDS),native_identity_removed=True)
 write(W/'build.json',report);print(json.dumps(dict(status=report['status'],files=len(payload),pool_files=list(report['pool_changes'])),ensure_ascii=True))
if __name__=='__main__':main()
