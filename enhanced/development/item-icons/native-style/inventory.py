import sys,os,json,hashlib
from pathlib import Path
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi');sys.path.insert(0,r'D:\FO3ID\server');sys.dont_write_bytecode=True
import http_config as h
r=Path(r'D:\fifaol3\item-icons\native-style');rows=[]
def grades(i,trail=()):
 if i in trail:return []
 if i in h.PACKS:return sorted({int(g) for g,w in h.pack_grades(i) if w>0})
 if i in h.PACKAGES:contents=h.PACKAGES[i][2]
 elif i in h.MONTHLY:contents=h.MONTHLY[i][3]+h.MONTHLY[i][4]
 else:return []
 return sorted({g for child,n in contents for g in grades(child,trail+(i,)) if n>0})
for kind,table in [('pack',h.PACKS),('item',h.ITEMS),('package',h.PACKAGES),('monthly',h.MONTHLY)]:
 for i in table:
  d=h.item_def(i);row=dict(id=i,kind=kind,definition=d,grades=grades(i))
  if kind=='pack':row['filter']=h.PACKS[i][1]
  rows.append(row)
for i in (h.EP_ITEM,h.ES_ITEM,h.LR_TICKET,1000090):
 if i not in {v['id'] for v in rows}:rows.append(dict(id=i,kind='item',definition=h.item_def(i),grades=[]))
(r/'catalogue.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(items=len(rows),packs=sum(x['kind']=='pack' for x in rows),grade_signatures=len({tuple(x['grades']) for x in rows}))))
