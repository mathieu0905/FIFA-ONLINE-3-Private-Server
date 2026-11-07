"""Upgrade natural login/match/monthly rewards without modifying live saves."""
from pathlib import Path
import ast,copy,datetime,json,math,os,re,sys
import sale_grade8 as sale
import install as common
from prepare import S,C,R as BASE,sha,write
sys.dont_write_bytecode=True
R=BASE/'reward-upgrade';R.mkdir(exist_ok=True)
SELF='patches/reward_upgrade_preflight.py';MANIFEST='patches/reward-upgrade-installed.json';RECEIPT='patches/reward-upgrade-receipt.json'
TEMPLATE='patches/all_pack_prices_preflight.py'
def replace_assignment(source,name,value):
 tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets));lines=source.splitlines(keepends=True)
 return ''.join(lines[:node.lineno-1])+name+' = '+repr(value)+'\n'+''.join(lines[node.end_lineno:])
def build():
 def audit(event,args):
  if event=='open':
   path,mode,flags=args
   if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
    if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Reward build cannot write official files')
  if event in ('socket.bind','socket.connect'):raise PermissionError('No listeners or service requests during build')
 sys.addaudithook(audit);os.environ.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(S));sys.argv=['http_config.py']
 import http_config as h
 from product_packs import signature
 assert not (S/'gamedata/daily_rewards.json').exists(),'Preserve/reconcile explicit administrator daily table first'
 baseline={str(S/n):sha(S/n) for n in ('http_config.py','economy.py','product_packs.py','pack_value.py')}
 monthly_before=copy.deepcopy(h.MONTHLY);monthly=copy.deepcopy(h.MONTHLY)
 extras={81000001:([(h.EP_ITEM,2000000000)],[(h.EP_ITEM,500000000)]),81000002:([(98248018,1)],[(98248008,1)]),81000003:([(97950111,1)],[(97950008,1),(h.EP_ITEM,500000000)])}
 names={81000001:'BP成长月卡',81000002:'曼联传奇月卡',81000003:'高强典藏月卡'}
 descriptions={81000001:'保留原奖励；购买额外获得20亿BP，30天每天额外5亿BP。',81000002:'保留原奖励；购买额外获得曼联传奇自选+8一包，30天每天额外曼联传奇随机+8一包。',81000003:'保留原奖励；购买额外获得传奇TOP10自选+11一包，30天每天额外精选TOP100固定+8一包和5亿BP。'}
 for i,(now,daily) in extras.items():
  old=monthly[i];monthly[i]=(names[i],old[1],old[2],list(old[3])+now,list(old[4])+daily,descriptions[i]+'每位经理每月限购1份，按30天总预期BP的45%计价。未领取的日奖励不跨天累计。')
  assert all(item in monthly[i][3] for item in old[3]) and all(item in monthly[i][4] for item in old[4])
 daily=[dict(ep=ep,pack=pack,count=1) for ep,pack in zip((100000000,200000000,300000000,400000000,500000000,700000000,1000000000),(98248008,97950008,98248008,97950009,98248008,97950010,97950011))]
 http=(S/'http_config.py').read_text('utf8');http=replace_assignment(http,'MONTHLY',monthly);http=replace_assignment(http,'DAILY_DEFAULT',daily)
 old_static='if i in (EP_ITEM, ES_ITEM) or i in PACKS or i in ITEMS or i in PACKAGES})';assert http.count(old_static)==1
 http=http.replace(old_static,'if i in (EP_ITEM, ES_ITEM) or i in PACKS or i in ITEMS or i in PACKAGES or i in MONTHLY})')
 compile(http,'http_config.py','exec');(R/'http_config.py').write_text(http,'utf8')
 economy=(S/'economy.py').read_text('utf8')
 for old,new in [('DAILY_CASH=100\n','DAILY_CASH=10000\n'),('MATCH_DAILY_CAP=600\n','MATCH_DAILY_CAP=10000\n'),('60 if mg>og else 40 if mg==og else 25','1000 if mg>og else 700 if mg==og else 400')]:assert economy.count(old)==1;economy=economy.replace(old,new)
 compile(economy,'economy.py','exec');(R/'economy.py').write_text(economy,'utf8')
 # Native EP cards sample a lower-mode triangular distribution, rounded to
 # 10000 BP and clamped at lo; the previous midpoint model overstated them.
 valuation=(S/'pack_value.py').read_text('utf8');needle="            if kind=='EP_LOTTERY':return math.fsum(effect['ep'])/len(effect['ep'])";assert valuation.count(needle)==1
 helper='''def triangular_ep_value(bounds):
    lo,hi=map(int,bounds)
    if lo<0 or hi<lo:raise ValueError('Invalid EP lottery bounds')
    if lo==hi:return float(lo)
    # Sum survival probabilities at rounding thresholds in constant time.
    den=(hi-lo)**2;first=lo//10000+1;last=(hi+5000)//10000
    if last<first:return float(lo)
    threshold=first*10000-5000
    survival=den if threshold<=lo else max(0,hi-threshold)**2
    total=lo*den+(first*10000-lo)*survival
    a,b=first+1,last
    if b>=a:
        n=b-a+1;sumk=(a+b)*n//2
        sumk2=b*(b+1)*(2*b+1)//6-(a-1)*a*(2*a-1)//6
        H=hi+5000
        total+=10000*(n*H*H-20000*H*sumk+100000000*sumk2)
    return total/den

'''
 valuation=valuation.replace('class ValueModel:',helper+'class ValueModel:').replace(needle,"            if kind=='EP_LOTTERY':return triangular_ep_value(effect['ep'])");compile(valuation,'pack_value.py','exec');(R/'pack_value.py').write_text(valuation,'utf8')
 ValueModel=common.load(R/'pack_value.py','reward_value_model').ValueModel;h.MONTHLY=monthly;model=ValueModel(h,h.product_packs['valuation']['points_per_ep'])
 cfg=dict(schema=1,edition='upgraded-monthly-login-match-rewards-v1',limits={str(i):dict(count=1,period='month',scope='manager') for i in monthly},risk_packs={},strength_packs={},bundles={},chains={},value_prices={})
 rows=[];frozen_stages={int(i) for t in h.product_packs['chains'].values() for steps in t['round_steps'] for i in steps}
 for raw,previous in h.product_packs['value_prices'].items():
  i=int(raw)
  if i not in h.PACKS and i not in h.PACKAGES and i not in h.MONTHLY and not(i in h.ITEMS and h.ITEMS[i][2] in ('EP_LOTTERY','ITEM_LOTTERY')):continue
  if i in frozen_stages:continue
  if i in h.CHAIN_STEPS:
   cfg['value_prices'][raw]=copy.deepcopy(previous);rows.append(dict(id=i,name=h.item_def(i)['name'],price=h.product_price(i,1),expected_bp=previous['expected_ep'],kind=previous['kind'],legacy_stage_frozen=True));continue
  kind='once' if i in monthly else previous['kind'];q=model.describe(i);q.update(kind=kind,price=q['quotes'][kind],bp_per_point=h.product_packs['valuation']['bp_per_point']);cfg['value_prices'][raw]=q
  rows.append(dict(id=i,name=monthly[i][0] if i in monthly else h.item_def(i)['name'],price=q['price'],expected_bp=q['expected_ep'],kind=kind))
 assert len(rows)==313
 product=(S/'product_packs.py').read_text('utf8');needle="'all_pack_expected_prices.json')";assert product.count(needle)==1;product=product.replace(needle,"'all_pack_expected_prices.json','reward_upgrade_products.json')").replace("'once':'一次性优惠'","'once':'限购优惠'")
 compile(product,'product_packs.py','exec');(R/'product_packs.py').write_text(product,'utf8');cfg['hash']=signature(cfg);write(R/'reward_upgrade_products.json',cfg)
 contracts={str(i):signature(dict(pool=h.pack_pool(i),grades=h.pack_grades(i))) for i in h.PACKS};stages=set(h.CHAIN_STEPS)
 write(R/'build.json',dict(status='BUILT',baseline=baseline,daily=daily,monthly_before=monthly_before,monthly=monthly,prices=rows,daily_cash=10000,match=dict(win=1000,draw=700,loss=400,cap=10000),contracts=contracts,stage_prices={str(i):h.product_price(i,1) for i in stages},valuation=h.product_packs['valuation']))
 print(json.dumps(dict(monthly_prices=[r for r in rows if r['id'] in monthly],daily_cash=10000,match_cap=10000),ensure_ascii=True))
def plan():
 data=json.loads((R/'build.json').read_text('utf8'))
 for path,digest in data['baseline'].items():assert sha(path)==digest,'Build baseline changed'
 assert not (S/'gamedata/daily_rewards.json').exists()
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',play);assert len(matches)==1;parent_rel=matches[0].decode().replace('\\','/');assert parent_rel!=SELF
 parent=common.load(S/parent_rel,'reward_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','reward_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 helper=(S/TEMPLATE).read_text('utf8').replace('all-pack-prices-installed.json',MANIFEST.split('/')[-1]).replace('all-pack-prices-receipt.json',RECEIPT.split('/')[-1]).replace('all_pack_prices_preflight.py',SELF.split('/')[-1]).replace('INSTALLED_ALL_PACK_PRICES','INSTALLED_REWARD_UPGRADE').replace('ALL_PACK_PRICES_PREFLIGHT_PASS','REWARD_UPGRADE_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 payload=[(n,R/n) for n in ('http_config.py','economy.py','product_packs.py','pack_value.py')]+[('gamedata/reward_upgrade_products.json',R/'reward_upgrade_products.json'),(SELF,helper.encode()),('play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))];entries=[]
 for rel,source in payload:
  target=S/rel;before=sha(target) if target.exists() else None;key=('server',rel.casefold());after=common.digest(source) if isinstance(source,bytes) else sha(source)
  if key in table:assert table[key]['sha256']==before
  else:assert not target.exists()
  table[key]=dict(root='server',relative=rel,sha256=after);entries.append(dict(root='server',relative=rel,target=target,source=source,before=before,after=after))
 comp['guards']=list(table.values());comp['files_verified']=False;comp.setdefault('ancestry',[]).append(dict(layer='upgraded-daily-match-monthly-rewards',native_status='PENDING'));comp['receipt_policies'].append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in json.loads((S/parent.RECEIPT).read_text('utf8')).items() if k!='native_status'}))
 revision='reward-upgrade-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel))
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_REWARD_UPGRADE',revision=revision,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,body in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=body,before=None,after=common.digest(body)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=revision,prior=prior)
def apply():
 sale.R=R;sale.SELF=SELF;sale.MANIFEST=MANIFEST;sale.RECEIPT=RECEIPT;sale.plan=plan;sale.apply()
if __name__=='__main__':
 if '--apply' in sys.argv:apply()
 else:build()
