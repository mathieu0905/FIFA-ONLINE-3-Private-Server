from pathlib import Path
import sys,os,json,copy,math,zlib,base64
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True;os.environ.update(FO3_MAX_GRADE='20',FO3_LANGUAGE='chi')
import market_price_store
market_price_store.MarketPriceStore.flush=lambda self,e:0
import http_config as h
cfg=h.product_packs;retired=set(cfg.get('retired_chains',[]));plan={};summary=[];targets=[5,10,20,30,45];fillers=[97010006,97500900,97010006,97819084,97500900]
for pos,(key,t) in enumerate((k,v) for k,v in cfg['chains'].items() if int(k) not in retired):
 new=copy.deepcopy(t);filler=fillers[pos];fp=math.ceil(h.product_price(filler,1)*0.65)
 for rr in t['round_steps']:
  previous=0
  for k,i in enumerate(rr):
   old=t['packages'][str(i)];units=sum(n for child,n in old['contents']);base=h.product_price(i,1);factor=[0,1,2,4,8][k]
   while True:
    premium=units*factor;amount=base*factor+(targets[k]-premium)*fp
    if amount>=previous*1.6:break
    factor+=1
    assert units*factor<targets[k]
   contents=[[child,n*factor] for child,n in old['contents'] if factor]+[[filler,targets[k]-premium]]
   assert all(h.item_def(child)['category']=='PLAYERPACK' and n>0 for child,n in contents)
   p=new['packages'][str(i)];p.update(contents=contents,count=targets[k],price=amount,original_price=base,factor=factor,premium_count=premium,filler_count=targets[k]-premium)
   p['label']=['入门连抽','进阶连抽','豪华补给','海量抽卡','终极盛宴'][k];p['name']=f'{k+1}档·{p["label"]}·{p["count"]}包'
   new['prices'][str(i)]=amount;previous=amount
 plan[key]=new
 summary.append(dict(root=int(key),name=t['name'],filler=filler,filler_name=h.item_def(filler)['name'],counts=targets,prices=[new['prices'][str(i)] for i in t['steps']],premium_counts=[new['packages'][str(i)]['premium_count'] for i in t['steps']],total=sum(new['prices'][str(i)] for i in t['steps'])))
(R/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8');(R/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
encoded=base64.b64encode(zlib.compress(json.dumps(plan,ensure_ascii=False,separators=(',',':')).encode())).decode()
(R/'data_function.py').write_text("def volume_data():\n    import json,zlib,base64\n    return json.loads(zlib.decompress(base64.b64decode("+repr(encoded)+")))\n",encoding='utf8')
print(json.dumps(summary,ensure_ascii=True))
