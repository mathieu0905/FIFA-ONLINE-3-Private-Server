"""Inventory all pack-bearing sale types against the agreed live valuation."""
from pathlib import Path
import sys,os,json,collections
from prepare import S,C,R,write
OUT=R/'all-prices';OUT.mkdir(exist_ok=True);sys.dont_write_bytecode=True
def audit(event,args):
 if event=='open':
  path,mode,flags=args
  if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
   if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Audit cannot write official files')
 if event=='socket.bind':raise PermissionError('Audit cannot start services')
 if event=='socket.connect':
  address=args[1]
  if not isinstance(address,tuple) or address[0] not in ('127.0.0.1','::1') or address[1] not in (443,8088):raise PermissionError('Audit permits only local read-only verification connections')
sys.addaudithook(audit)
os.environ.update(FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0');sys.path.insert(0,str(S));sys.argv=['http_config.py']
import http_config as h
from pack_value import ValueModel
model=ValueModel(h,h.product_packs['valuation']['points_per_ep'])
stages={int(i) for t in h.product_packs['chains'].values() for steps in t['round_steps'] for i in steps}
groups=dict(pack=set(h.PACKS),package=set(h.PACKAGES)-stages,monthly=set(h.MONTHLY),lottery={i for i,d in h.ITEMS.items() if d[2] in ('EP_LOTTERY','ITEM_LOTTERY')})
rows=[];errors=[]
for group,ids in groups.items():
 for i in sorted(ids):
  d=h.item_def(i);rule=h.product_packs['limits'].get(str(i),{})
  kind='once' if (rule.get('period')=='once' or (i in h.MONTHLY and rule.get('count')==1)) and i not in h.product_packs.get('chain_only_items',[]) else 'ordinary';expected=model.value(i);quote=model.quote(i,kind);price=h.product_price(i,1)
  legacy_stage=i in h.CHAIN_STEPS
  if legacy_stage:quote=price
  bunches=d.get('bunches',[]);mismatches=[b for b in bunches if b['price']!=h.product_price(i,b['bunch'])]
  row=dict(id=i,name=d['name'],group=group,expected_bp=expected,kind=kind,expected_price=quote,actual_price=price,retired=i in h.product_packs.get('retired_sale_items',[]),legacy_stage_frozen=legacy_stage,bunch_mismatches=mismatches,bunches=bunches)
  rows.append(row)
  if price!=quote or mismatches:errors.append(row)
report=dict(groups={k:len(v) for k,v in groups.items()},total=len(rows),mismatches=len(errors),rows=rows,errors=errors)
output='audit-after.json' if os.environ.get('FO3_PRICE_AUDIT_AFTER')=='1' else 'audit-before.json'
write(OUT/output,report);print(json.dumps(dict(groups=report['groups'],total=len(rows),mismatches=len(errors)),ensure_ascii=True))
