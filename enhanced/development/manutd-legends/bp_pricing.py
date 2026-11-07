"""Explicit BP/cash anchor; frozen issued odds and unfinished chain contracts."""
from pathlib import Path
import copy,json,math,os,sys,re,datetime
import sale_grade8 as sale
import install as common
from prepare import S,C,sha,write
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent/'bp-pricing';R.mkdir(exist_ok=True)
SELF='patches/bp_expected_price_preflight.py';MANIFEST='patches/bp-expected-price-installed.json';RECEIPT='patches/bp-expected-price-receipt.json'
TEMPLATE_SELF='patches/manutd_grade8_preflight.py'
TEMPLATE_MANIFEST='manutd-grade8-installed.json';TEMPLATE_RECEIPT='manutd-grade8-receipt.json'
REFERENCE_ROOT=71250401
REFERENCE_ROUND_POINTS=500000
def build():
 def audit(event,args):
  if event=='open':
   path,mode,flags=args
   if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
    if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Build cannot write outside its resources')
  if event in ('socket.bind','socket.connect'):raise PermissionError('Build cannot start or contact services')
 sys.addaudithook(audit)
 os.environ.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(S));sys.argv=['http_config.py']
 import http_config as h
 valuation_source=(S/'pack_value.py').read_text('utf8')
 valuation_source=valuation_source.replace('import functools, math','import functools, math\nfrom decimal import Decimal, ROUND_CEILING')
 old_quote="""        standard=max(3,math.ceil(value*self.points_per_ep))
        chain=min(standard-1,max(2,math.ceil(value*self.points_per_ep*FACTORS['chain'])))
        once=min(chain-1,max(1,math.ceil(value*self.points_per_ep*FACTORS['once'])))"""
 new_quote="""        # Decimal prevents exact boundary quotes such as 123500 gaining a point
        # from a binary floating-point tail before ceiling.
        base=Decimal(str(value))*Decimal(str(self.points_per_ep))
        ceiling=lambda factor:int((base*Decimal(str(factor))).to_integral_value(rounding=ROUND_CEILING))
        standard=max(3,ceiling(1))
        chain=min(standard-1,max(2,ceiling(FACTORS['chain'])))
        once=min(chain-1,max(1,ceiling(FACTORS['once'])))"""
 assert valuation_source.count(old_quote)==1
 valuation_source=valuation_source.replace(old_quote,new_quote);compile(valuation_source,'pack_value.py','exec');(R/'pack_value.py').write_text(valuation_source,'utf8')
 ValueModel=common.load(R/'pack_value.py','bp_decimal_model').ValueModel
 from product_packs import signature
 old=h.product_packs
 reference=old['chains'][str(REFERENCE_ROOT)]
 reference_bp=math.fsum(h.pack_expected_value(i) for i in reference['steps'])
 coefficient=REFERENCE_ROUND_POINTS/(reference_bp*.65);bp_per_point=1/coefficient
 model=ValueModel(h,coefficient)
 cfg=dict(schema=1,edition='reference-moments-round-500000-points-v1',limits={},risk_packs={},strength_packs={},bundles={},chains={},value_prices={},retired_chains=[],valuation=dict(points_per_ep=coefficient,bp_per_point=bp_per_point,factors=dict(ordinary=1,chain=.65,once=.45),choice_rule='maximum_selectable_BP',reference='human requested reference chain whole round 500000 points',reference_root=REFERENCE_ROOT,reference_new_root=REFERENCE_ROOT+100000,reference_round_expected_bp=reference_bp,reference_round_target=REFERENCE_ROUND_POINTS,reference_discount=.65,reference_round_rounding='largest remainder apportions five stages to exactly 500000',bp_unit='same credited BP as player_value_price and coach EP balance'))
 retired=set(old.get('retired_sale_items',[]));stages={int(i) for t in old['chains'].values() for steps in t['round_steps'] for i in steps}
 report=[];contracts={}
 for i in h.PACKS:
  contracts[str(i)]=signature(dict(pool=h.pack_pool(i),grades=h.pack_grades(i)))
 for i in sorted(set(h.PACKS)|set(h.PACKAGES)):
  if i in retired or i in stages:continue
  rules=old['limits'].get(str(i),{});kind='once' if rules.get('period')=='once' and i not in old.get('chain_only_items',[]) else 'ordinary'
  d=model.describe(i)
  if d['expected_ep']<=0:continue
  d.update(kind=kind,price=d['quotes'][kind],bp_per_point=bp_per_point)
  cfg['value_prices'][str(i)]=d
  report.append(dict(id=i,name=h.item_def(i)['name'],expected_bp=d['expected_ep'],old_price=h.product_price(i,1),price=d['price'],kind=kind))
 roots=[]
 for root,t in old['chains'].items():
  if int(root) in old.get('retired_chains',[]):continue
  newroot=int(root)+100000;assert newroot not in h.CHAINED
  track=copy.deepcopy(t);track['name']=t['name']+'·BP统一价';track['steps']=[i+100000 for i in t['steps']];track['round_steps']=[[i+100000 for i in steps] for steps in t['round_steps']];track['prices']={};track['packages']={}
  for steps in t['round_steps']:
   for i in steps:
    ni=i+100000;assert ni not in h.PACKAGES and ni not in h.PACKS
    package=copy.deepcopy(t['packages'][str(i)]);package['name']+='·BP统一价'
    quote=model.describe(i);quote.update(kind='chain',price=quote['quotes']['chain'],bp_per_point=bp_per_point)
    track['prices'][str(ni)]=quote['price'];track['packages'][str(ni)]=package;cfg['value_prices'][str(ni)]=quote
  if int(root)==REFERENCE_ROOT:
   from decimal import Decimal,ROUND_FLOOR
   for steps in track['round_steps']:
    weights=[Decimal(str(model.value(i-100000))) for i in steps];total_weight=sum(weights)
    exact=[Decimal(REFERENCE_ROUND_POINTS)*w/total_weight for w in weights]
    allocated=[int(v.to_integral_value(rounding=ROUND_FLOOR)) for v in exact]
    extra=REFERENCE_ROUND_POINTS-sum(allocated)
    order=sorted(range(len(steps)),key=lambda j:(-(exact[j]-allocated[j]),steps[j]))
    for j in order[:extra]:allocated[j]+=1
    assert sum(allocated)==REFERENCE_ROUND_POINTS
    for i,price in zip(steps,allocated):
     track['prices'][str(i)]=price;quote=cfg['value_prices'][str(i)];quote.update(price=price,round_apportioned=True);quote['quotes']['chain']=price
  total=sum(track['prices'][str(i)] for i in track['steps'])
  for p in track['packages'].values():p['description']=f'参考传奇时刻收藏连锁整轮500000点券的预期BP比例，连锁65%计价；本轮共{total}点券；固定原卡池和强化规则。'
  cfg['chains'][str(newroot)]=track;cfg['retired_chains'].append(int(root));roots.append(dict(old_root=int(root),root=newroot,name=track['name'],round_price=total,steps=[dict(id=i,price=track['prices'][str(i)],contents=track['packages'][str(i)]['contents']) for i in track['steps']]))
 source=(S/'product_packs.py').read_text('utf8');needle="'manutd_grade8_products.json')";assert source.count(needle)==1
 text=source.replace(needle,"'manutd_grade8_products.json','bp_expected_products.json')");compile(text,'product_packs.py','exec');(R/'product_packs.py').write_text(text,'utf8')
 cfg['hash']=signature(cfg);write(R/'bp_expected_products.json',cfg)
 write(R/'build.json',dict(status='BUILT',baseline={str(S/n):sha(S/n) for n in ('product_packs.py','pack_value.py')},bp_per_point=bp_per_point,reference_round_expected_bp=reference_bp,reference_root=REFERENCE_ROOT,reference_round_target=REFERENCE_ROUND_POINTS,products=report,chains=roots,issued_pack_contracts=contracts,old_chain_prices={str(i):h.product_price(i,1) for i in sorted(stages)},previous_coefficient=old['valuation']['points_per_ep'],new_coefficient=coefficient,retired_roots=cfg['retired_chains']))
 print(json.dumps(dict(bp_per_point=bp_per_point,reference_round_expected_bp=reference_bp,priced_products=len(report),examples=[x for x in report if x['id'] in (97310084,98248008,98248018)],chains=roots),ensure_ascii=True))
def plan():
 data=json.loads((R/'build.json').read_text('utf8'))
 for p,h in data['baseline'].items():assert sha(p)==h
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',play);assert len(matches)==1;parent_rel=matches[0].decode().replace('\\','/');assert parent_rel!=SELF
 parent=common.load(S/parent_rel,'bp_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','bp_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 # Reuse our verified strict guard implementation, while inheriting the actual
 # latest parent's full composition (including later icon-only installations).
 helper=(S/TEMPLATE_SELF).read_text('utf8').replace(TEMPLATE_MANIFEST,MANIFEST.split('/')[-1]).replace(TEMPLATE_RECEIPT,RECEIPT.split('/')[-1]).replace(TEMPLATE_SELF.split('/')[-1],SELF.split('/')[-1]).replace('INSTALLED_MANUTD_GRADE8','INSTALLED_BP_EXPECTED_PRICE').replace('MANUTD_GRADE8_PREFLIGHT_PASS','BP_EXPECTED_PRICE_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 payload=[('product_packs.py',R/'product_packs.py'),('pack_value.py',R/'pack_value.py'),('gamedata/bp_expected_products.json',R/'bp_expected_products.json'),(SELF,helper.encode()),('play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))];entries=[]
 for rel,source in payload:
  target=S/rel;before=sha(target) if target.exists() else None;key=('server',rel.casefold());after=common.digest(source) if isinstance(source,bytes) else sha(source)
  if key in table:assert table[key]['sha256']==before
  else:assert not target.exists()
  table[key]=dict(root='server',relative=rel,sha256=after);entries.append(dict(root='server',relative=rel,target=target,source=source,before=before,after=after))
 comp['guards']=list(table.values());comp['files_verified']=False;comp.setdefault('ancestry',[]).append(dict(layer='explicit-BP-expected-pricing',native_status='PENDING'))
 comp['receipt_policies'].append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in json.loads((S/parent.RECEIPT).read_text('utf8')).items() if k!='native_status'}))
 rev='bp-expected-price-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');manifest=dict(schema=1,revision=rev,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel))
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_BP_EXPECTED_PRICE',revision=rev,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,b in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=b,before=None,after=common.digest(b)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=rev,prior=prior)
def apply():
 # Same tested transaction, fresh asset snapshot and supervised service recovery.
 sale.R=R;sale.SELF=SELF;sale.MANIFEST=MANIFEST;sale.RECEIPT=RECEIPT;sale.plan=plan;sale.apply()
if __name__=='__main__':
 if '--apply' in sys.argv:apply()
 else:build()
