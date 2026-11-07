"""Build an incremental, exact-source-bound season19 payload for installation."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,shutil,sqlite3,sys,time
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
WORK=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
sys.path[:0]=[str(S),str(S/'tools/re'),str(S/'player_editor'),str(WORK/'work/roster_extension')]
import bigdir,extract_fifadb
from ordered_big import replace_member
from refpack import refpack
from cryptography.hazmat.primitives.ciphers import Cipher,modes
try:from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish
from prepare_roster import digest
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),'utf-8')
def encrypt(p):
 e=Cipher(Blowfish(extract_fifadb.KEY),modes.ECB()).encryptor()
 return extract_fifadb.swap32(e.update(extract_fifadb.swap32(p))+e.finalize())
def main(out):
 out=Path(out).resolve();assert not out.exists();out.mkdir(parents=True)
 spec=read(R/'roster-audit.json');assert spec['count']==88 and not spec['issues']
 cards=spec['cards'];assert len({r['base_playerid'] for r in cards})==88
 source_files={'database':S/'gamedata/fifadb.sqlite','data0':C/'data/data_0.big','registry':S/'gamedata/custom_rosters.json','roster':S/'responses/static_roster.json','cadence':S/'gamedata/pack_cadence.json','catalogue':S/'gamedata/pack_catalogue.json'}
 sources={k:dict(path=str(p),sha256=sha(p)) for k,p in source_files.items()}
 registry=read(source_files['registry']);roster=read(source_files['roster'])
 assert not any(r['id']==19 for r in registry['seasons'])
 assert not any(19 in r['value'] for r in roster['seasons'])
 original=source_files['data0'];member='data/db2/fifadb.db.db2'
 decoded=bytes(extract_fifadb.decrypt(bigdir.read(original,member)))
 assert b'SQLite format 3\0'+decoded[16:]==source_files['database'].read_bytes()
 print('双端基线一致；开始添加88张独立新卡',flush=True)
 target=out/'fifadb.sqlite';shutil.copyfile(source_files['database'],target)
 with sqlite3.connect(target) as db:
  db.row_factory=sqlite3.Row
  assert db.execute('select count(*) from players where spid/1000000=19').fetchone()[0]==0
  before=db.execute('select count(*) from players').fetchone()[0]
  for card in cards:
   row=dict(db.execute('select * from players where spid=?',(card['template_spid'],)).fetchone());assert digest(row)==card['source_row_sha256']
   spid=19000000+card['base_playerid'];row.update(card['fo3_overrides'],spid=spid)
   row['potential']=max(row['potential'],row['overallrating'])
   assert row['playerid']==card['base_playerid'] and 1<=row['overallrating']<=99
   db.execute('insert into players('+','.join(row)+') values('+','.join('?' for _ in row)+')',list(row.values()))
   for table in ('permid','permcn','permkr','permth','permvn','permsg'):db.execute('insert into '+table+'(spid,licensed,transferable) values(?,1,1)',(spid,))
  db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  db.execute('attach database ? as old',(str(source_files['database']),))
  tables=[r[0] for r in db.execute("select name from main.sqlite_master where type='table'")]
  counts={}
  for table in tables:
   assert not db.execute('select * from old.'+table+' except select * from main.'+table+' limit 1').fetchone(),table
   n=db.execute('select count(*) from main.'+table).fetchone()[0]-db.execute('select count(*) from old.'+table).fetchone()[0]
   assert n==(88 if table in ('players','permid','permcn','permkr','permth','permvn','permsg') else 0),(table,n)
   counts[table]=n
 print('旧数据库全部行保持；开始压缩客户端资源',flush=True)
 plain=target.read_bytes();encoded=encrypt(decoded[:16]+plain[16:]);assert bytes(extract_fifadb.decrypt(encoded))[16:]==plain[16:]
 packed=refpack(encoded);print('压缩完成',len(packed),flush=True)
 newbig=out/'data_0.big';shutil.copyfile(original,newbig);replace_member(newbig,member,packed,len(encoded))
 assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(bigdir.read(newbig,member)))[16:]==plain
 oldbytes=original.read_bytes();newbytes=newbig.read_bytes();oldentries=bigdir.entries(original);newentries=bigdir.entries(newbig)
 assert len(oldentries)==len(newentries)==271
 assert all(a[1]+a[2]<=b[1] for a,b in zip(newentries,newentries[1:]))
 for a,b in zip(oldentries,newentries):
  assert a[0]==b[0]
  if a[0]!=member:assert oldbytes[a[1]:a[1]+a[2]]==newbytes[b[1]:b[1]+b[2]]
 registry['seasons'].append(dict(id=19,label='怀旧神兽',source_seasons=sorted({r['template_season'] for r in cards}),cards=[19000000+r['base_playerid'] for r in cards]))
 for card in cards:
  registry['cards'].append(dict(fo3_spid=19000000+card['base_playerid'],base_playerid=card['base_playerid'],name_zh=card['name_zh'],name_en=card['name_en'],season_id=19,template_spid=card['template_spid'],template_label=card['template_label'],import_version=spec['version'],mapping_rule='FO3 historical identity/model and traits; role-preserving attribute lift to UL range',source_url=next((r.get('source_url') or (r.get('sources') or r.get('source_urls') or [None])[0] for r in card['research'] if r.get('source_url') or r.get('sources') or r.get('source_urls')),'local:verified-FO3-template')))
 roster['seasons'].append(dict(season='$FC_CUSTOM_SEASON_19',value=[19],open='2013-01-01T00:00:00.000Z',close='2099-12-31T00:00:00.000Z'))
 write(out/'custom_rosters.json',registry);write(out/'static_roster.json',roster)
 face_dir=out/'portraits';face_dir.mkdir();portraits=[]
 cache=C/'_cache/games/fo3id/externalAssets/players'
 for card in cards:
  pid=card['base_playerid'];donors=[cache/f'p{card["template_spid"]}.png',cache/f'p{pid}.png',R/'downloaded-portraits'/f'p{pid}.png']
  donor=next((p for p in donors if p.is_file() and p.read_bytes().startswith(b'\x89PNG')),None)
  if donor:
   name=f'p{19000000+pid}.png';shutil.copyfile(donor,face_dir/name);portraits.append(dict(name=name,donor=str(donor),sha256=sha(donor)))
  else:portraits.append(dict(name=f'p{19000000+pid}.png',missing=True))
 for k,p in source_files.items():assert sha(p)==sources[k]['sha256'],'Concurrent source changed: '+k
 result=dict(status='BUILT_NOT_INSTALLED',season=19,count=88,groups=spec['groups'],source_files=sources,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()},table_delta=counts,old_rows_exact=True,non_target_big_members_exact=270,portraits=portraits,native_verified=False,state_shop_replaced=False)
 write(out/'manifest.json',result)
 print(json.dumps(dict(status=result['status'],count=88,before=before,after=before+88,portraits=len([r for r in portraits if not r.get('missing')]),missing=[r['name'] for r in portraits if r.get('missing')]),ensure_ascii=False),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();main(a.out)
