from pathlib import Path
import sys,json,hashlib,statistics
sys.path.insert(0,r'D:\fifaol3\pack-reprice')
import host
h=host.h;R=Path(__file__).parent
from hot_update_runtime import compile_handlers
a=json.loads((host.S/'hot_updates/active.json').read_text('utf8'));raw=(host.S/a['code']).read_bytes();assert hashlib.sha256(raw).hexdigest()==a['sha256']
hs=compile_handlers(raw,'audit',a['routes'],allow_templates=True)
rows=json.loads(hs['/shop/list'](h,'',b'')[1]);out=[]
for r in rows:
 i=int(r['product']['itemid'])
 if i not in h.PACKS or not r.get('visible',True):continue
 pool=sorted((int(s),float(w)) for s,w in h.pack_pool(i) if w>0);ov=sorted(h.card_ovr(s)+h.GRADE_BOOST[1] for s,w in pool)
 out.append(dict(id=i,name=h.item_def(i)['name'],n=len(pool),median=statistics.median(ov),low=ov[0],p25=ov[len(ov)//4],under80=sum(v<80 for v in ov),sig=hashlib.sha256(json.dumps(pool).encode()).hexdigest(),grades=h.pack_grades(i)))
(R/'audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8');(R/'before-business.py').write_bytes(raw);(R/'active-before.json').write_text(json.dumps(a,indent=2),'utf8')
for p in out:print(p['id'],p['name'],p['n'],p['median'],p['p25'],p['under80'],p['sig'][:8])
host.close()
