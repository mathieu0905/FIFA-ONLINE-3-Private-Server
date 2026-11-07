import sys,json,pathlib,collections,os
os.environ.update(FO3_MAX_GRADE="20",FO3_LANGUAGE="chi")
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\FO3ID\server')
def audit(event,args):
 if event=='open' and isinstance(args[0],str) and pathlib.Path(args[0]).name in ('state.json','shop.json') and args[2]& (0x1|0x2|0x40|0x200):raise RuntimeError('Asset write prohibited')
sys.addaudithook(audit)
import http_config as h
rows=[]
for kind,cat in [('pack',h.PACKS),('item',h.ITEMS),('package',h.PACKAGES),('monthly',h.MONTHLY)]:
 for i in cat:
  d=h.item_def(i)
  rows.append(dict(id=i,kind=kind,definition=d))

for i in (h.EP_ITEM,h.ES_ITEM,h.LR_TICKET,1000090):
 if i not in {r['id'] for r in rows}: rows.append(dict(id=i,kind='item',definition=h.item_def(i)))
p=pathlib.Path(r'D:\fifaol3\item-icons\catalogue.json');p.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
assets=pathlib.Path(h.ASSETS)/'externalAssets/shop'
missing=[r for r in rows if not (assets/(str(r['definition'].get('itemicon'))+'.png')).is_file()]
print(json.dumps(dict(count=len(rows),kinds=dict(collections.Counter(r['kind'] for r in rows)),unique_icons=len(set(str(r['definition'].get('itemicon')) for r in rows)),missing=len(missing),missing_examples=[(r['id'],r['definition'].get('name'),r['definition'].get('itemicon')) for r in missing[:10]]),ensure_ascii=False))
