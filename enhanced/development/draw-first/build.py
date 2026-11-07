from pathlib import Path
import sys,os,json,hashlib,copy
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
sys.path.insert(0,str(S));sys.dont_write_bytecode=True
os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
def protected(event,args):
 if event=='open' and isinstance(args[0],str) and Path(args[0]).name in ('state.json','shop.json') and args[2]&0x243:raise RuntimeError('Protected asset write')
sys.addaudithook(protected)
import market_price_store
market_price_store.MarketPriceStore.flush=lambda self,events:0
import http_config as h
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
st=h._state();rows=h.shop_list(st);sale={int(r['product']['itemid']) for r in rows if r.get('visible',True) and not isinstance(r.get('chained'),list)}
cfg=h.product_packs
choices={i for i in h.PACKS if h.item_def(i)['category']=='DRAFTPACK'}
stages={int(i) for t in cfg['chains'].values() for i in t['packages']}
affected=set(choices)
while True:
 more={i for i,p in h.PACKAGES.items() if i not in stages and any(child in affected for child,n in p[2])}
 if more<=affected:break
 affected|=more
mapping={old:98310001+k for k,old in enumerate(sorted(affected))}
assert not set(mapping.values())&(set(h.PACKS)|set(h.PACKAGES)|set(h.ITEMS)|set(h.MONTHLY))
spec=dict(schema=1,mapping={str(k):v for k,v in mapping.items()},sale_ids=sorted(sale&affected),packs={},bundles={})
for old,new in mapping.items():
 name=h.item_def(old)['name'].replace('自选','随机').replace('旧版·','')+'·抽卡版'
 if old in choices:
  pool=h.pack_pool(old);total=sum(w for s,w in pool);grades=h.pack_grades(old);gs=[0]*max(g for g,w in grades)
  for g,w in grades:gs[g-1]=w
  spec['packs'][str(new)]=dict(name=name,description=f'随机抽取1名球员；卡池共{len(pool)}人，强化分布与对应原包相同。不能指定球员。<BR>'+('固定强化+'+str(next(g for g,w in grades if w)) if sum(w>0 for g,w in grades)==1 else '强化等级按原包概率随机抽取。'),mode='random',tiers=[dict(name='原池随机',weight=w/total,pool=[s]) for s,w in pool],grades=gs,price=h.product_price(old,1))
 else:
  spec['bundles'][str(new)]=dict(name=name,description='抽卡版礼包；内含随机卡包，具体内容见明细。',contents=[[mapping.get(i,i),n] for i,n in h.PACKAGES[old][2]],price=h.product_price(old,1))
spec['hash']=hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();write(R/'draw_first_rules.json',spec)
src=(S/'product_packs.py').read_text('utf8');anchor="    chain_only=set(cfg.get('chain_only_items',[]))"
assert src.count(anchor)==1
src=src.replace(anchor,"    from draw_first import prepare\n    prepare(h,cfg)\n"+anchor)
src+='\n    from draw_first import finish\n    finish(h,cfg,value_model)\n'
(R/'product_packs.py').write_text(src,encoding='utf8')
write(R/'legacy.json',dict(packs={str(i):dict(pool=h.pack_pool(i),grades=h.pack_grades(i),category=h.item_def(i)['category']) for i in choices},bundles={str(i):h.PACKAGES[i] for i in affected-choices}))
inputs=[S/'product_packs.py',S/'gamedata/shop.json',S/'gamedata/pack_catalogue.json']+[S/'gamedata'/n for n in ('product_packs.json','product_chain_elite.json','shop_value_products.json','chain_rebalance_products.json','manutd_legends_products.json','manutd_grade8_products.json','bp_expected_products.json','all_pack_expected_prices.json','reward_upgrade_products.json')]
write(R/'build.json',dict(baseline={str(p):sha(p) for p in inputs if p.exists()},choices=len(choices),bundles=len(affected-choices),sale_ids=spec['sale_ids'],mapping=spec['mapping']))
print(json.dumps(dict(choices=len(choices),bundles=len(affected-choices),new_sale=len(spec['sale_ids']))))

