"""Build only touched resources from fresh live files, never a second server."""
from pathlib import Path
import hashlib,json,shutil,sqlite3,sys,datetime,math
sys.dont_write_bytecode=True
from prepare import S,C,R,prepare,sha,write,digest
sys.path[:0]=[str(S),str(S/'tools/re'),str(S/'player_editor')]
import bigdir,extract_fifadb
from ordered_big import replace_member
from refpack import refpack
from cryptography.hazmat.primitives.ciphers import Cipher,modes
try:from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
except ImportError:from cryptography.hazmat.primitives.ciphers.algorithms import Blowfish
def main():
 spec=prepare();out=R/('build-'+datetime.datetime.now().strftime('%H%M%S-%f'));out.mkdir()
 paths=dict(database=S/'gamedata/fifadb.sqlite',data0=C/'data/data_0.big',registry=S/'gamedata/custom_rosters.json',product=S/'product_packs.py')
 baseline={str(p):sha(p) for p in paths.values()};original=paths['data0'];member='data/db2/fifadb.db.db2'
 decoded=bytes(extract_fifadb.decrypt(bigdir.read(original,member)))
 assert b'SQLite format 3\0'+decoded[16:]==paths['database'].read_bytes(),'Dual DB baseline differs'
 target=out/'fifadb.sqlite';shutil.copyfile(paths['database'],target);wanted={c['fo3_spid'] for c in spec['cards']};added={c['fo3_spid'] for c in spec['cards'] if not c['existing']}
 with sqlite3.connect(target) as db:
  db.row_factory=sqlite3.Row
  for card in spec['cards']:
   old=db.execute('select * from players where spid=?',(card['template_spid'],)).fetchone();assert digest(dict(old))==card['source_row_sha256']
   row=card['row'];cols=list(row)
   if card['existing']:db.execute('update players set '+','.join(k+'=?' for k in cols if k!='spid')+' where spid=?',[row[k] for k in cols if k!='spid']+[row['spid']])
   else:
    db.execute('insert into players('+','.join(cols)+') values('+','.join('?' for _ in cols)+')',list(row.values()))
    for table in ('permid','permcn','permkr','permth','permvn','permsg'):db.execute('insert into '+table+' values(?,1,1)',(row['spid'],))
  db.commit();assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  db.execute('attach database ? as old',(str(paths['database']),));tables=[r[0] for r in db.execute("select name from main.sqlite_master where type='table'")]
  deltas={}
  for table in tables:
   where=' where spid/1000000<>48' if table=='players' else ''
   assert not db.execute('select * from old.'+table+where+' except select * from main.'+table+where+' limit 1').fetchone(),table
   delta=db.execute('select count(*) from main.'+table).fetchone()[0]-db.execute('select count(*) from old.'+table).fetchone()[0]
   assert delta==(len(added) if table in ('players','permid','permcn','permkr','permth','permvn','permsg') else 0),(table,delta)
   if table not in ('players','permid','permcn','permkr','permth','permvn','permsg'):
    assert not db.execute('select * from main.'+table+' except select * from old.'+table+' limit 1').fetchone(),table
   deltas[table]=delta
  assert {r[0] for r in db.execute('select spid from players where spid/1000000=48')}==wanted
 print('41 MUL cards verified; packing client database',flush=True)
 raw=target.read_bytes();enc=Cipher(Blowfish(extract_fifadb.KEY),modes.ECB()).encryptor();encoded=extract_fifadb.swap32(enc.update(extract_fifadb.swap32(decoded[:16]+raw[16:]))+enc.finalize())
 assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(encoded))[16:]==raw
 packed=refpack(encoded);big=out/'data_0.big';shutil.copyfile(original,big);replace_member(big,member,packed,len(encoded))
 assert b'SQLite format 3\0'+bytes(extract_fifadb.decrypt(bigdir.read(big,member)))[16:]==raw
 oldentries=bigdir.entries(original);entries=bigdir.entries(big);a=original.read_bytes();b=big.read_bytes();assert len(entries)==len(oldentries)
 assert all(x[1]+x[2]<=y[1] for x,y in zip(entries,entries[1:]))
 for x,y in zip(oldentries,entries):
  assert x[0]==y[0]
  if x[0]!=member:assert a[x[1]:x[1]+x[2]]==b[y[1]:y[1]+y[2]]
 reg=json.loads(paths['registry'].read_text('utf8'));assert not any(x['id']==48 for x in reg['seasons'])
 reg['seasons'].append(dict(id=48,label='MUL · 曼联传奇',cards=sorted(wanted),source_seasons=sorted({c['template_spid']//1000000 for c in spec['cards']})))
 for c in spec['cards']:
  assert not any(x['fo3_spid']==c['fo3_spid'] for x in reg['cards'])
  reg['cards'].append({k:v for k,v in c.items() if k not in ('row','source_row_sha256') }|dict(import_version='manutd-legends-88-92-v1',mapping_rule='historical FO3 identity; position-profile affine stats; level1 grade1 OVR 88..92',source_url='local:FO3-identity-and-model'))
 write(out/'custom_rosters.json',reg)
 # Add a new product edition; existing sold card-pack pools remain byte-for-byte.
 product=paths['product'].read_text('utf8');old="'chain_rebalance_products.json')";assert product.count(old)==1
 (out/'product_packs.py').write_text(product.replace(old,"'chain_rebalance_products.json','manutd_legends_products.json')"),'utf8')
 catalog=json.loads((S/'gamedata/product_packs.json').read_text('utf8'));search={str(c['fo3_spid']):dict(team=c['row']['teamid'],league=c['row']['leagueid'],name=c['name_en']+' '+c['name_zh']) for c in spec['cards']}
 cfg=dict(schema=1,edition='manutd-legends-88-92-v1',limits={},risk_packs={},strength_packs={},bundles={},chains={},value_prices={})
 for i,choice in [(98248001,False),(98248002,True)]:
  cfg['limits'][str(i)]=dict(count=100 if not choice else 10,period='day')
  cfg['strength_packs'][str(i)]=dict(name='MUL曼联传奇·41人扩充版·'+('自选+1' if choice else '随机+1'),price=1,mode='choice' if choice else 'random',grades=[100],tiers=[dict(name='48赛季MUL曼联传奇',weight=100,pool=sorted(wanted))],search=search if choice else {},description='每包获得1名48赛季MUL曼联传奇球员，固定+1；本期冻结41人。<BR>能力口径：1级、+1强化、主位置88～92，不含球队套与教练加成。<BR>'+('从41人中自选1人，取消不消耗。' if choice else '41张卡逐张等概率，每张1/41，无指定球员保底。'))
 write(out/'products-unpriced.json',cfg)
 faces=out/'portraits';faces.mkdir();portraits=[];cache=C/'_cache/games/fo3id/externalAssets/players'
 for c in spec['cards']:
  spid=c['fo3_spid'];pid=c['base_playerid'];donors=[cache/f'p{spid}.png',cache/f'p{c["template_spid"]}.png',cache/f'p{pid}.png']
  donors+=sorted(cache.glob('p*'+str(pid)+'.png'))+[R/'downloaded-portraits'/f'p{pid}.png']
  donor=next((p for p in donors if p.is_file() and p.read_bytes().startswith(b'\x89PNG')),None)
  if donor is None:
   portraits.append(dict(name=f'p{spid}.png',missing=True,playerid=pid));continue
  name=f'p{spid}.png';shutil.copyfile(donor,faces/name);portraits.append(dict(name=name,sha256=sha(donor),donor=str(donor)))
 for p,h in baseline.items():assert sha(p)==h,'Concurrent input changed; rebuild: '+p
 write(out/'build.json',dict(status='BUILT',spec=spec,baseline=baseline,table_deltas=deltas,non_target_members_exact=len(entries)-1,portraits=portraits))
 write(R/'latest-build.json',dict(path=str(out)));print(str(out),flush=True)
if __name__=='__main__':main()
