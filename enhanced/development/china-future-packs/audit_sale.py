import json
import host
try:
 h=host.h;out=[]
 rows=json.loads((host.R/'live-sale-audit.json').read_text('utf8'))
 for row in rows:
  i=row['itemid']
  if i not in h.PACKS:continue
  pool=list(h.pack_pool(i));grades=[g for g,w in h.pack_grades(i) if w>0]
  seasons=sorted({s//1000000 for s,w in pool})
  out.append(dict(itemid=i,name=row['name'],category=row['category'],minimum=min(grades),maximum=max(grades),seasons=seasons,pool_size=len(pool),upgrade=min(grades)<8 and seasons!=[84]))
 (host.R/'grade-sale-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
 print(json.dumps(dict(on_sale_pack_count=len(out),need_upgrade=[{k:v for k,v in row.items() if k not in ['seasons']} for row in out if row['upgrade']],exempt=[x for x in out if x['seasons']==[84]]),ensure_ascii=True))
finally:host.close()
