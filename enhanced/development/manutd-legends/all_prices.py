"""Complete all 313 pack/box/package/monthly quotes at the installed reference ratio."""
from pathlib import Path
import copy,datetime,json,os,re,sys
import sale_grade8 as sale
import install as common
from prepare import S,C,R as BASE,sha,write
R=BASE/'all-prices';R.mkdir(exist_ok=True)
SELF='patches/all_pack_prices_preflight.py';MANIFEST='patches/all-pack-prices-installed.json';RECEIPT='patches/all-pack-prices-receipt.json'
TEMPLATE='patches/bp_price_icons_preflight.py'
def build():
 import audit_all_prices as audit
 h=audit.h;model=audit.model
 from product_packs import signature
 cfg=dict(schema=1,edition='all-313-pack-box-monthly-reference-BP-prices-v1',limits={},risk_packs={},strength_packs={},bundles={},chains={},value_prices={})
 report=[]
 for row in audit.rows:
  i=row['id'];q=model.describe(i);q.update(kind=row['kind'],price=q['quotes'][row['kind']],bp_per_point=h.product_packs['valuation']['bp_per_point']);cfg['value_prices'][str(i)]=q
  report.append(dict(row,price=q['price']))
 source=(S/'product_packs.py').read_text('utf8');needle="'bp_expected_products.json')";assert source.count(needle)==1
 source=source.replace(needle,"'bp_expected_products.json','all_pack_expected_prices.json')")
 old="""        if value_model is not None and i not in stages and i in h.PACKS:
            calculated=value_model.quote(i,'ordinary')"""
 new="""        if value_model is not None and i not in stages and (i in h.PACKS or i in h.PACKAGES or i in h.MONTHLY or (i in h.ITEMS and h.ITEMS[i][2] in ('EP_LOTTERY','ITEM_LOTTERY'))):
            kind='once' if rules.get(i,{}).get('period')=='once' and i not in chain_only else 'ordinary'
            calculated=value_model.quote(i,kind)"""
 assert source.count(old)==1;source=source.replace(old,new);compile(source,'product_packs.py','exec');(R/'product_packs.py').write_text(source,'utf8')
 cfg['hash']=signature(cfg);write(R/'all_pack_expected_prices.json',cfg)
 contracts={str(i):signature(dict(pool=h.pack_pool(i),grades=h.pack_grades(i))) for i in h.PACKS}
 stages={int(i) for t in h.product_packs['chains'].values() for steps in t['round_steps'] for i in steps}
 write(R/'build.json',dict(status='BUILT',baseline={str(S/'product_packs.py'):sha(S/'product_packs.py')},groups=audit.report['groups'],total=len(report),changed=sum(r['actual_price']!=r['price'] for r in report),rows=report,contracts=contracts,stage_prices={str(i):h.product_price(i,1) for i in stages},valuation=h.product_packs['valuation']))
 print(json.dumps(dict(total=len(report),changed=sum(r['actual_price']!=r['price'] for r in report),groups=audit.report['groups'])))
def plan():
 data=json.loads((R/'build.json').read_text('utf8'))
 for p,h in data['baseline'].items():assert sha(p)==h
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',play);assert len(matches)==1;parent_rel=matches[0].decode().replace('\\','/');assert parent_rel!=SELF
 parent=common.load(S/parent_rel,'all_price_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','all_price_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 helper=(S/TEMPLATE).read_text('utf8').replace('bp-price-icons-installed.json',MANIFEST.split('/')[-1]).replace('bp-price-icons-receipt.json',RECEIPT.split('/')[-1]).replace('bp_price_icons_preflight.py',SELF.split('/')[-1]).replace('INSTALLED_BP_PRICE_ICONS','INSTALLED_ALL_PACK_PRICES').replace('BP_PRICE_ICONS_PREFLIGHT_PASS','ALL_PACK_PRICES_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 payload=[('product_packs.py',R/'product_packs.py'),('gamedata/all_pack_expected_prices.json',R/'all_pack_expected_prices.json'),(SELF,helper.encode()),('play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))];entries=[]
 for rel,source in payload:
  target=S/rel;before=sha(target) if target.exists() else None;key=('server',rel.casefold());after=common.digest(source) if isinstance(source,bytes) else sha(source)
  if key in table:assert table[key]['sha256']==before
  else:assert not target.exists()
  table[key]=dict(root='server',relative=rel,sha256=after);entries.append(dict(root='server',relative=rel,target=target,source=source,before=before,after=after))
 comp['guards']=list(table.values());comp['files_verified']=False;comp.setdefault('ancestry',[]).append(dict(layer='all-pack-box-monthly-prices',native_status='PENDING'));comp['receipt_policies'].append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in json.loads((S/parent.RECEIPT).read_text('utf8')).items() if k!='native_status'}))
 revision='all-pack-prices-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=sha(S/parent_rel),total_priced=313,valuation=data['valuation'])
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_ALL_PACK_PRICES',revision=revision,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,b in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=b,before=None,after=common.digest(b)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=revision,prior=prior)
def apply():
 sale.R=R;sale.SELF=SELF;sale.MANIFEST=MANIFEST;sale.RECEIPT=RECEIPT;sale.plan=plan;sale.apply()
if __name__=='__main__':
 if '--apply' in sys.argv:apply()
 else:build()
