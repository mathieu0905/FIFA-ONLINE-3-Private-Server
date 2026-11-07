"""Add missing United servants using current native identities; preserve all live assets."""
from pathlib import Path
import contextlib,copy,datetime,json,math,re,shutil,sqlite3,struct,subprocess,sys,time,urllib.request
sys.dont_write_bytecode=True
import organize_seasons as util
from prepare import S,C,R as BASE,sha,write,STATS
common=util.common;codec=util.codec
R=BASE/'service-expansion';R.mkdir(exist_ok=True)
SELF='patches/manutd_service_preflight.py';MANIFEST='patches/manutd-service-installed.json';RECEIPT='patches/manutd-service-receipt.json'
DATA='''201535|瓦拉内|93|5
200145|卡塞米罗|93|10
203263|马奎尔|91|5
41236|伊布拉希莫维奇|94|25
178088|马塔|92|18
191202|马蒂奇|92|10
176944|费莱尼|91|14
178224|埃尔南德斯|92|25
189681|拉斐尔|91|3
169588|埃文斯|91|5
189881|斯莫林|91|5
194957|菲尔·琼斯|90|5
143001|特维斯|93|25
5419|迈克尔·欧文|93|25
121944|施魏因施泰格|92|14
189358|香川真司|91|18
211300|马夏尔|92|27
207494|林加德|90|18
237238|麦克托米奈|91|14
209297|弗雷德|90|14
221660|林德洛夫|90|5
179813|卡瓦尼|93|25
222481|布兰科|92|5
52241|拉尔森|92|25
152908|阿什利·扬|91|7
186146|维尔贝克|91|25'''
PERMS=('permid','permcn','permkr','permth','permvn','permsg')
def read(p):return json.loads(Path(p).read_text('utf8'))
def top():
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1
 rel=matches[0].decode().replace('\\','/');return play,matches[0],rel,common.load(S/rel,'manutd_service_parent')
def build():
 out=R/('build-'+datetime.datetime.now().strftime('%H%M%S-%f'));out.mkdir();sources=[S/'gamedata/fifadb.sqlite',C/'data/data_0.big',S/'gamedata/custom_rosters.json',S/'responses/static_roster.json']
 baseline={str(p):sha(p) for p in sources};w=util.weights();member='data/db2/fifadb.db.db2';decoded=bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(sources[1],member)))
 assert b'SQLite format 3\0'+decoded[16:]==sources[0].read_bytes()
 shutil.copyfile(sources[0],out/'fifadb.sqlite');(out/'portraits').mkdir();cards=[];donors=[]
 with sqlite3.connect(out/'fifadb.sqlite') as db:
  db.row_factory=sqlite3.Row
  for line in DATA.splitlines():
   pid,zh,target,pos=line.split('|');pid,target,pos=int(pid),int(target),int(pos);spid=48000000+pid
   assert not db.execute('select 1 from players where spid=?',(spid,)).fetchone(),spid
   rows=[dict(row) for row in db.execute('select * from players where playerid=? and spid>=1000000 and spid%1000000=? and spid/1000000 not in (12,13,18,19,84)',(pid,pid))]
   assert rows,('No historical native source',pid)
   rows=[row for row in rows if 0<=row['skillmoves']<=4];assert rows,('No valid source skill-code',pid)
   source=max(rows,key=lambda row:(row['overallrating'],row['spid']));row=dict(source)
   assert not (row['headclasscode']==1 and row['headtypecode']>=30001),'Do not borrow a reserved modern model selector'
   row.update(spid=spid,teamid=11,leagueid=13,historyopen=1,preferredposition1=pos)
   positions=list(dict.fromkeys([pos]+[source['preferredposition'+str(i)] for i in range(1,5) if source['preferredposition'+str(i)]>=0]))[:4]
   row.update({'preferredposition'+str(i):positions[i-1] if len(positions)>=i else -1 for i in range(1,5)})
   choices=[]
   for shift in range(-80,81):
    stats={k:min(99,max(1,row[k]+shift)) for k in STATS};value=util.primary({**row,**stats},w)
    choices.append(((abs(value+5-target),sum(v in (1,99) for v in stats.values()),abs(shift)),stats,value,shift))
   _,stats,value,shift=min(choices,key=lambda x:x[0]);assert value+5==target
   row.update(stats,overallrating=value,potential=max(value,row['potential']))
   cols=list(row);db.execute('insert into players('+','.join(cols)+') values('+','.join('?' for _ in cols)+')',list(row.values()))
   for table in PERMS:db.execute('insert into '+table+' values(?,1,1)',(spid,))
   en=db.execute('select full_eng from nameseng where playerid=?',(pid,)).fetchone()[0]
   names=db.execute('select short from nameschi where playerid=?',(pid,)).fetchone();assert names and not names[0].casefold().startswith('shortname'),(pid,names)
   cache=C/'_cache/games/fo3id/externalAssets/players';other=C/'_cache/cdn/externalAssets/players'
   candidates=[cache/f'p{source["spid"]}.png',cache/f'p{pid}.png',other/f'p{source["spid"]}.png',other/f'p{pid}.png']
   candidates+=sorted(cache.glob('p*'+str(pid)+'.png'))+sorted(other.glob('p*'+str(pid)+'.png'))
   downloads=R/'portrait-sources';downloads.mkdir(exist_ok=True);candidates.append(downloads/f'p{pid}.png')
   donor=next((p for p in candidates if p.is_file() and p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')),None)
   if donor is None:
    url=f'https://fco.dn.nexoncdn.co.kr/live/externalAssets/common/players/p{pid}.png'
    with urllib.request.urlopen(url,timeout=20) as response:image=response.read(2*1024*1024)
    assert image.startswith(b'\x89PNG\r\n\x1a\n');width,height=struct.unpack('>II',image[16:24]);assert 16<=width<=2048 and 16<=height<=2048
    donor=downloads/f'p{pid}.png';donor.write_bytes(image);write(downloads/f'p{pid}.json',dict(playerid=pid,url=url,sha256=sha(donor),width=width,height=height))
   face=out/'portraits'/f'p{spid}.png';shutil.copyfile(donor,face);donors.append(dict(spid=spid,source=str(donor),sha256=sha(face)))
   cards.append(dict(fo3_spid=spid,base_playerid=pid,name_zh=zh,name_en=en,season_id=48,template_spid=source['spid'],display_plus1_ovr=target,base_ovr=value,stat_shift=shift,row=row,import_version='manutd-service-90-94-v1',mapping_rule='Authentic existing FO3 identity/model; primary position level1 grade1 OVR 90..94',source_url='local:FO3-native-identity-and-model'))
  db.commit();db.execute('attach database ? as old',(str(sources[0]),))
  for table, in db.execute("select name from main.sqlite_master where type='table'").fetchall():
   assert not db.execute('select * from old.'+table+' except select * from main.'+table+' limit 1').fetchone(),('Old row changed',table)
   count=db.execute('select count(*) from main.'+table).fetchone()[0]-db.execute('select count(*) from old.'+table).fetchone()[0]
   assert count==(len(cards) if table in ('players',)+PERMS else 0),(table,count)
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
  count=db.execute('select count(*) from players where spid/1000000 in (48,49,55)').fetchone()[0]
  registry=read(sources[2]);oldreg=copy.deepcopy(registry);entry=next(e for e in registry['seasons'] if e['id']==48)
  entry['cards']=sorted(set(entry['cards'])|{c['fo3_spid'] for c in cards});entry['source_seasons']=sorted(set(entry.get('source_seasons',[]))|{c['template_spid']//1000000 for c in cards})
  registry['cards'] += [{k:v for k,v in c.items() if k!='row'} for c in cards];write(out/'custom_rosters.json',registry)
  roster=read(sources[3]);oldroster=copy.deepcopy(roster);scores=[]
  for i,e in enumerate(roster['seasons']):
   values=[util.primary(dict(row),w)+5 for row in db.execute('select * from players where spid/1000000 in ('+','.join('?' for _ in e['value'])+')',e['value'])];assert values
   scores.append(dict(entry=e,mean=sum(values)/len(values),peak=max(values),old_index=i))
  scores.sort(key=lambda x:(-x['mean'],-x['peak'],x['old_index']));roster['seasons']=[x['entry'] for x in scores]
  assert sorted(map(lambda e:json.dumps(e,sort_keys=True),roster['seasons']))==sorted(map(lambda e:json.dumps(e,sort_keys=True),oldroster['seasons']))
  assert len([e for e in roster['seasons'] if 48 in e['value']])==1
  write(out/'static_roster.json',roster)
 big=out/'data_0.big';shutil.copyfile(sources[1],big);raw=(out/'fifadb.sqlite').read_bytes();encrypted=util.encrypted_sqlite(decoded,raw)
 codec.replace_member(big,member,codec.refpack(encrypted),len(encrypted));assert b'SQLite format 3\0'+bytes(codec.extract_fifadb.decrypt(codec.bigdir.read(big,member)))[16:]==raw
 a=sources[1].read_bytes();b=big.read_bytes();oldentries=codec.bigdir.entries(sources[1]);entries=codec.bigdir.entries(big);assert len(oldentries)==len(entries)
 for x,y in zip(oldentries,entries):
  assert x[0]==y[0]
  if x[0]!=member:assert a[x[1]:x[1]+x[2]]==b[y[1]:y[1]+y[2]],x[0]
 # Compute only the new cards' one-time seeds, using the current selected market model.
 sys.path.insert(0,'D:/fifaol3/npc-peer-market/expanded-training');from expanded_value_model import ExpandedValueModel
 modelpath=Path('D:/fifaol3/npc-peer-market/highend-training/results/selected-model.json.gz');model=ExpandedValueModel(modelpath)
 seeds=[[c['fo3_spid'],min(5_600_000_000_000_000,max(1,round(math.exp(model.log_predict(c['row'])))//1000))] for c in cards]
 write(out/'price-seeds.json',dict(schema=1,model_sha256=sha(modelpath),source_database_sha256=sha(out/'fifadb.sqlite'),rows=seeds,policy='One-time additive initial prices; old prices and events unchanged'))
 checker=common.load(S/'tools/player_import/check.py','manutd_service_checker')
 certificate=checker.validate(S,C,database=out/'fifadb.sqlite',data0=big,registry=out/'custom_rosters.json',portraits=out/'portraits',full=True)
 assert certificate['status']=='PLAYER_IMPORT_FULL_PASS'
 portrait_hashes={}
 for path,digest in certificate['portrait_hashes'].items():
  p=Path(path)
  if p.is_relative_to(out/'portraits'):
   for prefix in ('games/fo3id','cdn'):portrait_hashes[str(C/f'_cache/{prefix}/externalAssets/players/{p.name}')]=digest
  else:portrait_hashes[path]=digest
 certificate['portrait_hashes']=portrait_hashes;write(out/'player-import-validation.json',certificate)
 for path,digest in baseline.items():assert sha(path)==digest,('Concurrent source changed; rebuild',path)
 report=dict(status='BUILT_SEMANTICS_PASS',baseline=baseline,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()},cards=[{k:v for k,v in c.items() if k!='row'} for c in cards],new_cards=len(cards),total_man_united_cards=count,main_season_cards=len(entry['cards']),portraits=donors,original_rows_preserved=True,all_other_big_members_preserved=True,legacy_issued_pack_config_unchanged=True,native_semantic_status=certificate['status'],native_ui_verified=False,match_verified=False)
 write(out/'build.json',report);write(R/'latest-build.json',dict(path=str(out)));print(json.dumps(dict(status=report['status'],new_cards=len(cards),total=count,build=str(out)),ensure_ascii=True),flush=True)
 return out
def plan(out,market):
 data=read(out/'build.json')
 for path,digest in data['baseline'].items():assert sha(path)==digest,('Rebuild required',path)
 for name,digest in data['outputs'].items():assert sha(out/name)==digest
 play,match,parent_rel,parent=top();prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','manutd_service_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 helper=(S/parent_rel).read_text('utf8');parent_name=Path(parent_rel).stem;parent_manifest=Path(parent.MANIFEST).name;parent_receipt=Path(parent.RECEIPT).name
 helper=helper.replace(parent_manifest,Path(MANIFEST).name).replace(parent_receipt,Path(RECEIPT).name).replace(parent_name,Path(SELF).stem)
 old_status=read(S/parent.RECEIPT)['status'];helper=helper.replace(old_status,'INSTALLED_MANUTD_SERVICE').replace(prior['status'],'MANUTD_SERVICE_PREFLIGHT_PASS')
 extra="""    import sqlite3
    seed=json.loads((server/'gamedata/manutd-service-price-seeds.json').read_text('utf8'))
    with sqlite3.connect((server/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        for spid,price in seed['rows']:
            assert db.execute('select initial_price,model_sha256 from seeds where spid=?',(spid,)).fetchone()==(price,seed['model_sha256'])
            assert db.execute('select basis_price from prices where spid=?',(spid,)).fetchone()[0]>0
"""
 marker="    return dict(status='MANUTD_SERVICE_PREFLIGHT_PASS'";assert helper.count(marker)==1;helper=helper.replace(marker,extra+marker);compile(helper,SELF,'exec')
 revision='manutd-service-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');docrel='docs/工程经验与修改边界.txt'
 note='\n\nFO3-MU-SERVICE（2026-11-07，'+revision+'，原生实机PENDING）\n用户要求补瓦拉内、卡塞米罗，核查其它遗漏，并明确马奎尔、卢克肖、埃雷拉和暗黑四天王均可收录。卢克肖/埃雷拉/纳尼/瓦伦西亚原卡保持；新增26名曼联效力球员到48季，主池41→67、合并筛选53→79，90～94为1级+1主位置口径。全部沿用现有真实playerid/原生身份及历史卡模型，不伪造新人身份；新卡按原技能分布平移校准，所有旧卡数据逐行相同。data0仅UI SQLite单成员替换，其它成员含EA原生库/模型/Lua/六语名字原压缩字节保持。\n注册表只追加新卡，筛选条目不删不增，按现值平均能力降序；全部旧商品/已发卡包池/概率/报价冻结，未把扩充强塞进已售卡包。新增卡市场初价依现行神经模型一次性预测，停服后对最新价格库仅追加26个seeds/prices，已有价格、成交事件、元数据精确保留。完整player_import语义检查通过后同步更新有效证书与双份真实头像。按最新父层/共同双锁/本次停服新快照备份与CAS安装，继承全部guard及receipt policy，不写state/shop，不自动退出或启动游戏。\n证据D:/fifaol3/manutd-legends/service-expansion；接口/SQLite/资源和语义验证不是游戏内市场或比赛验收。\n'
 payload=[('server','gamedata/fifadb.sqlite',out/'fifadb.sqlite'),('client','data/data_0.big',out/'data_0.big'),('server','gamedata/custom_rosters.json',out/'custom_rosters.json'),('server','responses/static_roster.json',out/'static_roster.json'),('server','gamedata/manutd-service-price-seeds.json',out/'price-seeds.json'),('server','gamedata/player-import-validation.json',out/'player-import-validation.json'),('server','gamedata/npc-market-prices.sqlite',market),('server',docrel,(S/docrel).read_bytes()+note.encode('utf8')),('server',SELF,helper.encode('utf8')),('server','play-local.bat',play.replace(match,SELF.replace('/','\\').encode()))]
 for prefix in ('games/fo3id','cdn'):
  for face in (out/'portraits').glob('*.png'):payload.append(('client',f'_cache/{prefix}/externalAssets/players/{face.name}',face))
 entries=[]
 for root,rel,source in payload:
  target=(S if root=='server' else C)/rel;before=sha(target) if target.exists() else None;after=common.digest(source) if isinstance(source,bytes) else sha(source);key=(root,rel.casefold())
  if key in table:assert table[key]['sha256']==before
  elif target.exists():assert rel=='gamedata/npc-market-prices.sqlite' or (root=='client' and '/players/' in rel)
  if rel!='gamedata/npc-market-prices.sqlite':table[key]=dict(root=root,relative=rel,sha256=after)
  entries.append(dict(root=root,relative=rel,target=target,source=source,before=before,after=after))
 comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='manutd-service26-90-94',native_status='PENDING'))
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(p['relative']==policy['relative'] for p in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),build_sha256=sha(out/'build.json'),mutable_files=['gamedata/npc-market-prices.sqlite'])
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_MANUTD_SERVICE',revision=revision,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,body in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=body,before=None,after=common.digest(body)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=revision,prior=prior)
def fresh_market(out):
 target=out/'fresh-market.sqlite';source=S/'gamedata/npc-market-prices.sqlite'
 if target.exists():target.rename(out/('fresh-market-attempt-'+datetime.datetime.now().strftime('%H%M%S-%f')+'.sqlite'))
 with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(target) as db:src.backup(db)
 seed=read(out/'price-seeds.json')
 with sqlite3.connect(target.as_uri(),uri=True) as db:
  stamp=time.time()
  for spid,price in seed['rows']:
   db.execute('insert into seeds values(?,?,?,?)',(spid,price,seed['model_sha256'],stamp));db.execute('insert into prices values(?,?,?,?,null)',(spid,float(price),price,stamp))
  db.commit();db.execute('attach database ? as old',(source.as_uri()+'?mode=ro',))
  for table in ('metadata','seeds','prices','price_events'):assert not db.execute('select * from old.'+table+' except select * from main.'+table).fetchone(),table
  assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
 return target
def install(out):
 with common.locks():
  common.closed();_,_,_,parent=top();parent.preflight(S,C)
  for path,digest in read(out/'build.json')['baseline'].items():assert sha(path)==digest,('Rebuild required',path)
  was_running=bool(common.listening());stopped=False
  try:
   if was_running:
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=common.env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
    deadline=time.monotonic()+15
    while common.listening():
     if time.monotonic()>deadline:raise RuntimeError('Listeners remain')
     time.sleep(.2)
   common.closed();market=fresh_market(out);p=plan(out,market);backup=S/'backups'/p['revision'];snap=R/'fresh-stop-snapshot'/p['revision'];snap.mkdir(parents=True)
   protected={str(x):sha(x) for x in (S/'gamedata').glob('*.json') if x.name not in ('custom_rosters.json','player-import-validation.json')}
   for name in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/name,snap/name)
   def verify():
    common.load(S/SELF,'manutd_service_installed').preflight(S,C)
    for path,digest in protected.items():assert sha(path)==digest,('Protected changed',path)
   common.commit(p['entries'],backup,verify)
   result=dict(status='INSTALLED_NATIVE_PENDING',revision=p['revision'],backup=str(backup),protected=protected,preflight=common.load(S/SELF,'manutd_service_final').preflight(S,C),state_shop_written=False,native_verified=False,build=str(out),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',hashes={str(x):sha(x) for x in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat',S/'gamedata/fifadb.sqlite',C/'data/data_0.big')});write(R/'installed.json',result)
  finally:
   if was_running and stopped:common.restart()
  result['services_restored']=common.listening()==[443,8088,28002] if was_running else 'previously_stopped';write(R/'installed.json',result)
  descriptor=BASE.parent/'root-current-top.json';d=read(descriptor);d.update(status='INSTALLED_MANUTD_SERVICE_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),top_preflight=result['top_preflight'],top_manifest=result['top_manifest'],top_receipt=result['top_receipt'],files=result['hashes'],preflight=result['preflight'],handoff=str(R/'installed.json'),receipt_record=read(S/RECEIPT),services_restored=result['services_restored'],state_shop_written=False,native_verified=False,match_verified=False);common.atomic(common.body(d),descriptor)
  print(json.dumps(dict(status=result['status'],revision=p['revision'],services_restored=result['services_restored'])),flush=True)
if __name__=='__main__':
 if '--install' in sys.argv:install(Path(read(R/'latest-build.json')['path']))
 else:build()
