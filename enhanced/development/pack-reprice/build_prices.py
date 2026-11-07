from pathlib import Path
import sys,json,math,hashlib,functools,collections,copy
import host
R=host.R;S=host.S;h=host.h
from hot_update_runtime import compile_handlers
active=json.loads((S/'hot_updates/active.json').read_text('utf8'));raw=(S/active['code']).read_bytes();assert hashlib.sha256(raw).hexdigest()==active['sha256']
handlers=compile_handlers(raw,'current',active['routes'],allow_templates=True);ns=handlers['/shop/list'].__globals__
rows=json.loads(handlers['/shop/list'](h,'',b'')[1]);volume=ns['volume_data']()
stages={int(i) for t in volume.values() for i in t['packages']};needed={int(r['product']['itemid']) for r in rows if r.get('visible',True)}
for t in volume.values():
 for p in t['packages'].values():needed.update(i for i,n in p['contents'])
unit={};proof={};BP_PER_POINT=175519.5
def median(rows):
 rows=sorted(rows);total=math.fsum(w for v,w in rows);at=0
 for v,w in rows:
  at+=w
  if at>=total/2:return v
 raise ValueError('Empty pricing pool')
@functools.lru_cache(None)
def card(i,g):return h.player_value_price(i,g)
def price(i,trail=()):
 if i in unit:return unit[i]
 if i in trail:raise ValueError('Recursive bundle')
 trail=trail+(i,)
 if i==h.EP_ITEM:return 1/BP_PER_POINT
 if i==h.ES_ITEM:return .02
 old=h.product_price(i,1);reason={}
 if i in h.PACKS:
  grades=[(g,w) for g,w in h.pack_grades(i) if w>0];floor=min(g for g,w in grades);pool=[(int(s),float(w)) for s,w in h.pack_pool(i) if w>0]
  choice=h.item_def(i).get('category')=='DRAFTPACK';values=[(card(s,floor),w) for s,w in pool]
  base=max(v for v,w in values) if choice else median(values)
  factor=.70 if choice else .35;cap=100000 if choice else 50000 if floor>=11 else 20000
  rule=h.product_packs.get('limits',{}).get(str(i),{})
  if rule.get('period')=='once':factor*=.45
  calculated=max(3,min(cap,math.ceil(base/BP_PER_POINT*factor)))
  reason=dict(kind='choice' if choice else 'random',base_grade=floor,bonus=any(g>floor for g,w in grades),base_bp=base,pool_size=len(pool),pool_signature=hashlib.sha256(json.dumps(sorted(pool)).encode()).hexdigest(),factor=factor,cap=cap,calculated=calculated,grades=grades)
 elif i in h.PACKAGES:
  value=math.fsum(n*price(c,trail) for c,n in h.PACKAGES[i][2]);calculated=max(1,math.ceil(value*.9));reason=dict(kind='bundle',content_price=value,discount=.9)
 elif i in h.MONTHLY:
  _,_,days,now,daily,_=h.MONTHLY[i];value=math.fsum(n*price(c,trail) for c,n in now)+days*math.fsum(n*price(c,trail) for c,n in daily)
  calculated=max(1,math.ceil(value*.6));reason=dict(kind='monthly',content_price=value,discount=.6,days=days)
 elif i in h.ITEMS and h.ITEMS[i][2] in ('EP_LOTTERY','ITEM_LOTTERY'):
  effect=h.ITEMS[i][3]
  if h.ITEMS[i][2]=='EP_LOTTERY':base=effect['ep'][0]/BP_PER_POINT
  else:base=median([(price(p,trail) if isinstance(p,int) else p[1]/BP_PER_POINT,w) for w,p in effect['prizes']])
  calculated=max(1,min(20000,math.ceil(base*.35)));reason=dict(kind='lottery',base_price=base)
 else:return old
 # Existing bargains remain bargains; this is a downward correction, not a tax
 # on previously cheap items or a change to their contents.
 final=min(old,calculated);unit[i]=final
 proof[str(i)]=dict(name=h.item_def(i)['name'],old=old,price=final,**reason)
 return final
try:
 for i in sorted(needed-stages):price(i)
 new_volume=copy.deepcopy(volume)
 for root,t in new_volume.items():
  for raw,p in t['packages'].items():
   before=p['price'];total=math.fsum(n*price(c) for c,n in p['contents']);after=min(before,max(1,math.ceil(total*.65)))
   p['price']=after;t['prices'][raw]=after;unit[int(raw)]=after
   proof[raw]=dict(name=p['name'],kind='chain',old=before,price=after,content_price=total,discount=.65)
 data=dict(schema=1,policy='guaranteed-grade-player-median-v1',bp_per_point=BP_PER_POINT,prices={str(k):v for k,v in unit.items()},proof=proof)
 (R/'pricing.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
 (R/'volume-before.json').write_text(json.dumps(volume,ensure_ascii=False,indent=2),encoding='utf8');(R/'volume-after.json').write_text(json.dumps(new_volume,ensure_ascii=False,indent=2),encoding='utf8')
 (R/'before-business.py').write_bytes(raw if isinstance(raw,bytes) else (S/active['code']).read_bytes())
 (R/'baseline.json').write_text(json.dumps(dict(active=active,source_sha256=active['sha256'],inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [S/'product_packs.py',S/'pack_value.py',S/'economy.py',S/'gamedata/club_season_products.json']}),indent=2),encoding='utf8')
 summary=dict(items=len(proof),decreases=sum(v['price']<v['old'] for v in proof.values()),increases=sum(v['price']>v['old'] for v in proof.values()),manutd=[proof.get(str(i)) for i in (98448081,98448082,98448010)],chains=[dict(root=root,prices=[t['prices'][str(i)] for i in t['steps']],total=sum(t['prices'][str(i)] for i in t['steps'])) for root,t in new_volume.items()])
 (R/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=True))
finally:host.close()
