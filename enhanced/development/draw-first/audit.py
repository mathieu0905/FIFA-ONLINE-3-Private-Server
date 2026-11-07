from pathlib import Path
import sys,os,json,hashlib,collections
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True;os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def audit(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&(0x1|0x2|0x40|0x200):raise RuntimeError('Protected asset write')
sys.addaudithook(audit)
import http_config as h
st=h._state();rows=h.shop_list(st);pack_rows=[]
for i in h.PACKS:
 d=h.item_def(i);pool=sorted((int(s),float(w)) for s,w in h.pack_pool(i) if w>0);grades=[(int(g),float(w)) for g,w in h.pack_grades(i) if w>0]
 pack_rows.append(dict(id=i,name=d['name'],choice=d['category']=='DRAFTPACK',pool_size=len(pool),pool_hash=hashlib.sha256(json.dumps(pool).encode()).hexdigest(),grades=grades,price=h.product_price(i,1)))
choices={x['id'] for x in pack_rows if x['choice']};cfg=h.product_packs;active={int(i) for i in cfg['chains']}-set(cfg.get('retired_chains',[]));packs={x['id']:x for x in pack_rows};chain_report=[]
for root in sorted(active):
 t=cfg['chains'][str(root)];total=choice=0
 for rr in t['round_steps']:
  for i in rr:
   for child,n in t['packages'][str(i)]['contents']:
    if child in h.PACKS:total+=n;choice+=n*(child in choices)
 chain_report.append(dict(root=root,name=t['name'],choice_packs=choice,total_packs=total,first_round=[dict(stage=i,name=t['packages'][str(i)]['name'],contents=[dict(id=child,n=n,name=h.item_def(child)['name'],choice=child in choices) for child,n in t['packages'][str(i)]['contents']]) for i in t['steps']]))
owned=[]
for c in st['coaches']:
 for where in ('items','depot'):
  for item in c.get(where,[]):
   if item['itemid'] in choices:owned.append(dict(slot=c['slot'],where=where,itemid=item['itemid'],remains=item['remains']))
visible=[r for r in rows if r.get('visible',True) and r.get('buy',True) and not isinstance(r.get('chained'),list)];on_sale_choice=[int(r['product']['itemid']) for r in visible if int(r['product']['itemid']) in choices]
report=dict(packs=pack_rows,choice_ids=sorted(choices),on_sale_choice=on_sale_choice,chains=chain_report,owned_choices=owned,product_config=cfg)
(R/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(pack_count=len(pack_rows),choice_total=len(choices),on_sale_choice=len(on_sale_choice),owned_choice_stacks=len(owned),chains=[{k:v for k,v in t.items() if k!='first_round'} for t in chain_report]),ensure_ascii=True))
for i in on_sale_choice:print(json.dumps(packs[i],ensure_ascii=True))
