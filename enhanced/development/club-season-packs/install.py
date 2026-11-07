"""Install native registered products only while the user's game is closed."""
from pathlib import Path
import copy,datetime,json,os,re,shutil,subprocess,sys,time
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');sys.path.insert(0,str(R.parent/'manutd-legends'))
import install as tx
SELF='patches/club_season_packs_preflight.py';MANIFEST='patches/club-season-packs-installed.json';RECEIPT='patches/club-season-packs-receipt.json'
def read(p):return json.loads(Path(p).read_text('utf8'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tx.body(v))
def game_running():return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9};exit 0'],env=tx.env(),creationflags=subprocess.CREATE_NO_WINDOW).returncode!=0
def deferred():
 result=dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',formal_files_written=False,services_restarted=False);write(R/'deferred.json',result);print(json.dumps(result,ensure_ascii=False))
def plan():
 build=read(R/'build.json');tests=read(R/'tests.json');assert tests['status']=='PASS' and tests.get('weekly_fixed_pack_limit_enforced')==2
 assert tests['new_products']==[p['id'] for p in build['products']]
 assert tests['hot_revision']==read(S/'hot_updates/active.json')['revision'],'Business hot package changed; retest against latest'
 for p,h in build['baseline'].items():assert tx.sha(p)==h,('Rebuild required',p)
 for name,h in build['outputs'].items():assert tx.sha(R/name)==h
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(matches)==1;parentrel=matches[0].decode().replace('\\','/');parent=tx.load(S/parentrel,'season_pack_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));table={(r['root'],r['relative'].casefold()):r for r in comp['guards']};assert len(table)==len(comp['guards'])
 helper=(S/parentrel).read_text('utf8').replace(parent.MANIFEST,MANIFEST).replace(parent.RECEIPT,RECEIPT).replace(parent.SELF,SELF).replace(read(S/parent.RECEIPT)['status'],'INSTALLED_CLUB_SEASON_PACKS').replace(prior['status'],'CLUB_SEASON_PACKS_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 revision='club-season-packs-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');doc='docs/工程经验与修改边界.txt'
 note='\n\nFO3-CLUB-SEASON-PACKS（2026-11-07，'+revision+'，实机PENDING）\n用户要求曼联传奇/神童赛季卡包，并改为随机强化等级为主、少量固定包。冻结48主季67人及18神童40人，不混入49/55重复版本；各有+8～12（50/25/15/8/2%）、+10～15（50/25/12/7/4/2%）和每周3包固定+10，球员逐卡等概率且与强化独立；随机档每日100/30包。不销售自选新包或低于+8的新包。预期BP按当前持久市场价格及各强化档真实系数联合加权，沿用现行500000点券连锁参考校准所得1点券=175519.5 BP普通包比例，Decimal上取整冻结新售价；市场价格后续正常波动，旧商品/概率/报价/连锁及已持有权益均保持。\n仅注册6个新SKU和现有原生图标映射，不替换客户端资源；使用现有注册引擎、STATE_LOCK、库存序列/HMAC/开包回执和ABI2动态热路由。新增SKU注册不属于当前在线ABI，因此仅在检测游戏自然关闭后停服安装，游玩中直接延期且不要求退出，不绕过stop-server保护，不在线重跑install hooks。保持现有draw_first_full_20261107_02热包不变，恢复后核验watcher/ABI/revision/error。\n临时存档购买扣款、6包开包/重放、299种旧包池/强化/类别保持及联合预期值计价通过；未用真实余额购买、未发测试资产。共同双锁、最新父层guard/回执策略、停服新快照与备份/CAS；state/shop及市场现价不写。证据D:/fifaol3/club-season-packs；原生商城展示与真实购买待用户实机验收。\n'
 note=note.replace('不替换客户端资源','仅追加6款原生风格图标，旧图标不变').replace('保持现有draw_first_full_20261107_02热包不变','保持安装时实际最新业务热包不变')
 payload=[('server','product_packs.py',R/'product_packs.py'),('server','gamedata/club_season_products.json',R/'club_season_products.json'),('server','gamedata/all_item_icon_manifest.json',R/'all_item_icon_manifest.json'),('server',doc,(S/doc).read_bytes()+note.encode('utf8')),('server',SELF,helper.encode('utf8')),('server','play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))];entries=[]
 for prefix in ('games/fo3id','cdn'):
  for image in (R/'icons').glob('*.png'):payload.append(('client',f'_cache/{prefix}/externalAssets/shop/{image.name}',image))
 for root,rel,source in payload:
  target=(S if root=='server' else C)/rel;before=tx.sha(target) if target.exists() else None;after=tx.digest(source) if isinstance(source,bytes) else tx.sha(source);key=(root,rel.casefold())
  if key in table:assert table[key]['sha256']==before,('Guard changed',rel)
  else:assert not target.exists()
  table[key]=dict(root=root,relative=rel,sha256=after);entries.append(dict(root=root,relative=rel,target=target,source=source,before=before,after=after))
 comp.update(guards=list(table.values()),files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='club-season-surprise-packs',native_status='PENDING'));policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in read(S/parent.RECEIPT).items() if k!='native_status'})
 if not any(r['relative']==policy['relative'] for r in comp.setdefault('receipt_policies',[])):comp['receipt_policies'].append(policy)
 manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parentrel,parent_preflight_sha256=tx.sha(S/parentrel),build_sha256=tx.sha(R/'build.json'));mb=tx.body(manifest);rb=tx.body(dict(status='INSTALLED_CLUB_SEASON_PACKS',revision=revision,manifest_sha256=tx.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,data in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=data,before=None,after=tx.digest(data)))
 entries.sort(key=lambda r:r['relative']=='play-local.bat');return dict(entries=entries,revision=revision,prior=prior)
def main():
 if game_running():deferred();return
 with tx.locks():
  if game_running():deferred();return
  coord=read(R.parent/'coordination-current.json');assert not coord.get('current_unhanded_writers') and not coord.get('next_formal_writer')
  p=plan()
  if game_running():deferred();return
  running=bool(tx.listening());stopped=False
  try:
   if running:
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=tx.env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
    deadline=time.monotonic()+15
    while tx.listening():
     if time.monotonic()>deadline:raise RuntimeError('Listeners remain')
     time.sleep(.2)
   tx.closed();snap=R/'fresh-stop-snapshot'/p['revision'];snap.mkdir(parents=True);protected={str(path):tx.sha(path) for path in (S/'gamedata').glob('*.json') if path.name!='all_item_icon_manifest.json'}
   hot_before=read(S/'hot_updates/active.json');protected[str(S/'hot_updates/active.json')]=tx.sha(S/'hot_updates/active.json')
   protected[str(S/'gamedata/npc-market-prices.sqlite')]=tx.sha(S/'gamedata/npc-market-prices.sqlite')
   for name in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/name,snap/name)
   def verify():
    tx.load(S/SELF,'season_packs_installed').preflight(S,C)
    for name,digest in protected.items():assert tx.sha(name)==digest,('Protected file changed',name)
   backup=S/'backups'/p['revision'];tx.commit(p['entries'],backup,verify);result=dict(status='INSTALLED_NATIVE_PENDING',revision=p['revision'],backup=str(backup),protected=protected,hot_revision_expected=hot_before['revision'],top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',preflight=tx.load(S/SELF,'season_packs_final').preflight(S,C),hashes={str(path):tx.sha(path) for path in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat')},state_shop_written=False,native_ui_verified=False);write(R/'installed.json',result)
  finally:
   if running and stopped and not game_running():tx.restart()
  result['services_restored']=tx.listening()==[443,8088,28002];write(R/'installed.json',result)
  descriptor=read(R.parent/'root-current-top.json');descriptor.update(status='INSTALLED_CLUB_SEASON_PACKS_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),top_preflight=result['top_preflight'],top_manifest=result['top_manifest'],top_receipt=result['top_receipt'],files=result['hashes'],preflight=result['preflight'],handoff=str(R/'installed.json'),composition_available=True,function_signatures=dict(preflight='server=None,client=None',compose_manifest='server=None,client=None'),services_restored=result['services_restored'],state_shop_written=False,native_verified=False,match_verified=False);tx.atomic(tx.body(descriptor),R.parent/'root-current-top.json');print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
