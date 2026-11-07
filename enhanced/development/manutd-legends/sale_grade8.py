"""Standalone MUL +8 sales and original moment standalone price; preserve issued odds."""
from pathlib import Path
import copy,datetime,json,math,os,re,shutil,subprocess,sys,time
sys.dont_write_bytecode=True
import install as common
from prepare import S,C,sha,write
R=Path(__file__).resolve().parent/'sale-grade8';R.mkdir(exist_ok=True)
SELF='patches/manutd_grade8_preflight.py';MANIFEST='patches/manutd-grade8-installed.json';RECEIPT='patches/manutd-grade8-receipt.json'
def build():
 # Import installed production code without starting a listener or writing assets.
 def audit(event,args):
  if event=='open':
   path,mode,flags=args
   if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
    if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Build write outside task resources')
  if event in ('socket.bind','socket.connect'):raise PermissionError('Build cannot start/contact services')
 sys.addaudithook(audit)
 os.environ.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(S));sys.argv=['http_config.py']
 import http_config as h
 import product_packs
 cfg=dict(schema=1,edition='MUL-fixed8-and-moments-original-price-v1',limits={},risk_packs={},strength_packs={},bundles={},chains={},value_prices={},retired_sale_items=[97500048,98248001,98248002])
 coefficient=h.product_packs['valuation']['points_per_ep'];report=[]
 for old,i in ((98248001,98248008),(98248002,98248018)):
  assert i not in h.PACKS and i not in h.ITEMS and i not in h.PACKAGES
  d=copy.deepcopy(h.product_packs['strength_packs'][str(old)]);d['name']=d['name'].replace('+1','+8');d['grades']=[0]*7+[100]
  d['description']=d['description'].replace('固定+1','固定+8').replace('1级、+1强化、主位置88～92','未强化基础卡在1级、+1时主位置88～92；本包固定+8额外提高12点，即100～104')
  pool=d['tiers'][0]['pool'];values=[h.player_value_price(s,8) for s in pool];expected=max(values) if d['mode']=='choice' else sum(values)/len(values)
  standard=max(3,math.ceil(expected*coefficient));chain=min(standard-1,max(2,math.ceil(expected*coefficient*.65)));once=min(chain-1,max(1,math.ceil(expected*coefficient*.45)))
  d['price']=standard;cfg['strength_packs'][str(i)]=d;cfg['limits'][str(i)]=copy.deepcopy(h.product_packs['limits'][str(old)])
  cfg['value_prices'][str(i)]=dict(expected_ep=expected,standard_points=expected*coefficient,quotes=dict(ordinary=standard,chain=chain,once=once),kind='ordinary',price=standard)
  report.append(dict(id=i,name=d['name'],price=standard,grade=8,cards=len(pool)))
 # The explicitly authored rare-season sale was 600000; generic valuation had
 # overridden it to 1397. Restore only its standalone quote, not chain contracts.
 moment=h.product_packs['risk_packs']['97310084'];intended=moment['price'];assert intended==600000
 quote=copy.deepcopy(h.product_packs['value_prices']['97310084']);old_price=h.product_price(97310084,1)
 quote.update(price=intended,standard_points=intended,quotes=dict(ordinary=intended,chain=390000,once=270000),kind='ordinary',pricing_basis='restore original standalone rarity price; chain-only rewards and existing chain prices are separate')
 cfg['value_prices']['97310084']=quote
 source=(S/'product_packs.py').read_text('utf8');old="'manutd_legends_products.json')";assert source.count(old)==1
 updated=source.replace(old,"'manutd_legends_products.json','manutd_grade8_products.json')");compile(updated,'product_packs.py','exec');(R/'product_packs.py').write_text(updated,'utf8')
 cfg['hash']=product_packs.signature(cfg);write(R/'manutd_grade8_products.json',cfg)
 write(R/'build.json',dict(status='BUILT',baseline={str(S/'product_packs.py'):sha(S/'product_packs.py')},products=report,moment=dict(id=97310084,previous=old_price,restored=intended,grade=1,weekly_count=1),retired=cfg['retired_sale_items'],issued_odds_unchanged=True,chain_prices_unchanged=True))
 print(json.dumps(dict(products=report,moment_before=old_price,moment_after=intended),ensure_ascii=True))
def plan():
 build=json.loads((R/'build.json').read_text('utf8'))
 for p,h in build['baseline'].items():assert sha(p)==h,'Source changed, rebuild needed'
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',play);assert len(matches)==1
 parent_rel=matches[0].decode().replace('\\','/');assert parent_rel=='patches/manutd_legends_preflight.py','Parent changed; adapt explicitly'
 parent=common.load(S/parent_rel,'mul8_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','mul8_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 helper=(S/parent_rel).read_text('utf8').replace('manutd-legends-installed.json','manutd-grade8-installed.json').replace('manutd-legends-receipt.json','manutd-grade8-receipt.json').replace('manutd_legends_preflight.py','manutd_grade8_preflight.py').replace('INSTALLED_MANUTD_LEGENDS','INSTALLED_MANUTD_GRADE8').replace('MANUTD_LEGENDS_PREFLIGHT_PASS','MANUTD_GRADE8_PREFLIGHT_PASS')
 compile(helper,SELF,'exec')
 payload=[('product_packs.py',R/'product_packs.py'),('gamedata/manutd_grade8_products.json',R/'manutd_grade8_products.json'),(SELF,helper.encode()),('play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))]
 entries=[]
 for rel,source in payload:
  target=S/rel;before=sha(target) if target.exists() else None;key=('server',rel.casefold());after=common.digest(source) if isinstance(source,bytes) else sha(source)
  if key in table:assert table[key]['sha256']==before
  else:assert not target.exists()
  table[key]=dict(root='server',relative=rel,sha256=after);entries.append(dict(root='server',relative=rel,target=target,source=source,before=before,after=after))
 comp['guards']=list(table.values());comp['files_verified']=False;comp.setdefault('ancestry',[]).append(dict(layer='MUL-fixed8-sale-and-original-moment-price',native_status='PENDING'))
 policy=dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in json.loads((S/parent.RECEIPT).read_text('utf8')).items() if k!='native_status'})
 comp['receipt_policies'].append(policy)
 rev='manutd-grade8-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 manifest=dict(schema=1,revision=rev,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel))
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_MANUTD_GRADE8',revision=rev,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,b in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=b,before=None,after=common.digest(b)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat')
 return dict(entries=entries,revision=rev,prior=prior)
def apply():
 with common.locks():
  p=plan();was=bool(common.listening());stopped=False
  try:
   if was:
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(S/'stop-server.ps1')],env=common.env(),check=True,creationflags=subprocess.CREATE_NO_WINDOW);stopped=True
    deadline=time.monotonic()+12
    while common.listening():
     if time.monotonic()>deadline:raise RuntimeError('Listeners still active')
     time.sleep(.2)
   protected={str(S/'gamedata'/n):sha(S/'gamedata'/n) for n in ('state.json','shop.json','fifadb.sqlite','custom_rosters.json','product_packs.json','product_chain_elite.json','shop_value_products.json','chain_rebalance_products.json','manutd_legends_products.json')}
   snap=R/'fresh-stop-snapshot'/p['revision'];snap.mkdir(parents=True)
   for n in ('state.json','shop.json'):shutil.copyfile(S/'gamedata'/n,snap/n)
   def verify():
    common.load(S/SELF,'mul8_installed').preflight(S,C)
    for path,h in protected.items():assert sha(path)==h,('Protected file changed',path)
   backup=S/'backups'/p['revision'];common.commit(p['entries'],backup,verify)
   result=dict(status='INSTALLED',revision=p['revision'],backup=str(backup),protected=protected,preflight=common.load(S/SELF,'mul8_final').preflight(S,C),top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),state_shop_written=False,client_files_written=False,composition_api='compose_manifest(server=None,client=None)',native_status='PENDING',hashes={str(t):sha(t) for t in (S/SELF,S/MANIFEST,S/RECEIPT,S/'play-local.bat')})
   write(R/'installed.json',result)
  finally:
   if was and stopped:common.restart()
  result['services_restored']=common.listening()==[443,8088,28002] if was else 'previously_stopped';write(R/'installed.json',result)
  descriptor=common.R.parent/'root-current-top.json';d=json.loads(descriptor.read_text('utf8'));d.update(status='OBSERVED_MUL_GRADE8_SALE_INSTALL',observed_at=datetime.datetime.now().astimezone().isoformat(),top_preflight=result['top_preflight'],top_manifest=result['top_manifest'],top_receipt=result['top_receipt'],files=result['hashes'],handoff=str(R/'installed.json'),preflight=result['preflight'],receipt_record=json.loads((S/RECEIPT).read_text('utf8')),state_shop_written=False,services_restored=result['services_restored'],GUI_status='No GUI or client exit; server-only reload authorized by human');common.atomic(common.body(d),descriptor)
  print(json.dumps(result))
if __name__=='__main__':
 if '--apply' in sys.argv:apply()
 else:build()
