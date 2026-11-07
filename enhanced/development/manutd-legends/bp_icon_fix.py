"""Bind new chain stages to their unchanged reward edition's installed icons."""
import copy,json,re,datetime
import bp_pricing as bp
import sale_grade8 as sale
import install as common
from prepare import S,C,sha,write
R=bp.R/'icon-extension';R.mkdir(exist_ok=True)
SELF='patches/bp_price_icons_preflight.py';MANIFEST='patches/bp-price-icons-installed.json';RECEIPT='patches/bp-price-icons-receipt.json'
def plan():
 play=(S/'play-local.bat').read_bytes();matches=re.findall(rb'patches[\\/][a-z_]+_preflight\.py',play);assert len(matches)==1 and matches[0].decode().replace('\\','/')==bp.SELF
 parent=common.load(S/bp.SELF,'bp_icons_parent');prior=parent.preflight(S,C);comp=copy.deepcopy(parent.compose_manifest(S,C));validator=common.load(S/'patches/startup_market_preflight.py','bp_icons_validator');validator.verify_manifest(comp,S,C);table=validator.table(comp['guards'])
 path=S/'gamedata/all_item_icon_manifest.json';icons=json.loads(path.read_text('utf8'));cfg=json.loads((S/'gamedata/bp_expected_products.json').read_text('utf8'));before=copy.deepcopy(icons['items']);added=[]
 for track in cfg['chains'].values():
  for raw,d in track['packages'].items():
   i=int(raw);old=str(i-100000);assert raw not in icons['items'];row=copy.deepcopy(icons['items'][old]);row.update(itemid=i,name=d['name'],pricing_edition_parent_itemid=int(old));icons['items'][raw]=row;added.append(i)
 assert all(icons['items'][i]==d for i,d in before.items()) and len(added)==250
 helper=(S/bp.SELF).read_text('utf8').replace(bp.MANIFEST.split('/')[-1],MANIFEST.split('/')[-1]).replace(bp.RECEIPT.split('/')[-1],RECEIPT.split('/')[-1]).replace(bp.SELF.split('/')[-1],SELF.split('/')[-1]).replace('INSTALLED_BP_EXPECTED_PRICE','INSTALLED_BP_PRICE_ICONS').replace('BP_EXPECTED_PRICE_PREFLIGHT_PASS','BP_PRICE_ICONS_PREFLIGHT_PASS');compile(helper,SELF,'exec')
 payload=[('gamedata/all_item_icon_manifest.json',common.body(icons)),(SELF,helper.encode()),('play-local.bat',play.replace(matches[0],SELF.replace('/','\\').encode()))];entries=[]
 for rel,source in payload:
  target=S/rel;old=sha(target) if target.exists() else None;key=('server',rel.casefold());new=common.digest(source)
  if key in table:assert table[key]['sha256']==old
  else:assert not target.exists()
  table[key]=dict(root='server',relative=rel,sha256=new);entries.append(dict(root='server',relative=rel,target=target,source=source,before=old,after=new))
 comp['guards']=list(table.values());comp['files_verified']=False;comp.setdefault('ancestry',[]).append(dict(layer='BP-chain-icon-aliases',native_status='PENDING'));comp['receipt_policies'].append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in json.loads((S/parent.RECEIPT).read_text('utf8')).items() if k!='native_status'}))
 rev='bp-price-icons-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');manifest=dict(schema=1,revision=rev,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=bp.SELF,parent_preflight_sha256=sha(S/bp.SELF),existing_icons_exact=len(before),new_price_stage_aliases=added)
 mb=common.body(manifest);rb=common.body(dict(status='INSTALLED_BP_PRICE_ICONS',revision=rev,manifest_sha256=common.digest(mb),state_shop_replaced=False,native_status='PENDING'))
 for rel,b in ((MANIFEST,mb),(RECEIPT,rb)):
  assert not (S/rel).exists();entries.append(dict(root='server',relative=rel,target=S/rel,source=b,before=None,after=common.digest(b)))
 entries.sort(key=lambda e:e['relative']=='play-local.bat');return dict(entries=entries,revision=rev,prior=prior)
if __name__=='__main__':
 sale.R=R;sale.SELF=SELF;sale.MANIFEST=MANIFEST;sale.RECEIPT=RECEIPT;sale.plan=plan;sale.apply()
 common.restart()
 result=json.loads((R/'installed.json').read_text('utf8'));result['services_restored']=common.listening()==[443,8088,28002];write(R/'installed.json',result)
 original=json.loads((bp.R/'installed.json').read_text('utf8'));original.update(services_restored=result['services_restored'],final_top=result['top_preflight'],icon_extension=str(R/'installed.json'));write(bp.R/'installed.json',original)
