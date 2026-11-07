"""Author a value-priced edition and fix native chain state IDs; no formal writes."""
from pathlib import Path
import copy, hashlib, json, math, os, shutil, sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;P=R/'sandbox/server';S=Path('D:/FO3ID/server')
def signature(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf-8')
source=(S/'product_packs.py').read_text('utf-8')
def change(old,new):
    global source
    assert source.count(old)==1,old[:90]
    source=source.replace(old,new)
change('import copy, contextvars, datetime, functools, hashlib, hmac, json, random','import copy, contextvars, datetime, functools, hashlib, hmac, json, random, re')
change("    extra_path=Path(h.HERE)/'gamedata/product_chain_elite.json'\n    if extra_path.exists():","    for addon_name in ('product_chain_elite.json','shop_value_products.json'):\n        extra_path=Path(h.HERE)/'gamedata'/addon_name\n        if not extra_path.exists():continue")
# Original extra loader body already has eight spaces, suitable for the for loop.
change("        cfg['chain_only_items']=list(extra.get('chain_only_items',[]))","        cfg['chain_only_items']=sorted(set(cfg.get('chain_only_items',[])) | set(extra.get('chain_only_items',[])))")
change("        cfg['newly_retired_items']=list(extra.get('retired_sale_items',[]))", "        cfg['newly_retired_items']=sorted(set(cfg.get('newly_retired_items',[])) | set(extra.get('retired_sale_items',[])))")
change("        cfg['additional_editions']=[extra['edition']]","        cfg.setdefault('additional_editions',[]).append(extra['edition'])\n        cfg.setdefault('retired_chains',[]).extend(extra.get('retired_chains',[]))\n        cfg.setdefault('value_prices',{}).update(extra.get('value_prices',{}))\n        if extra.get('valuation'):cfg['valuation']=extra['valuation']")
change("    chain_only=set(cfg.get('chain_only_items',[]))","    chain_only=set(cfg.get('chain_only_items',[]))\n    retired_chains=set(cfg.get('retired_chains',[]))\n    value_prices=cfg.get('value_prices',{})\n    value_model=None")
change("        day=datetime.date.fromisoformat(h.today_wib())","        if rule['period']=='once':return 'lifetime'\n        day=datetime.date.fromisoformat(h.today_wib())")
change("        return int(r['rounds']<t['rounds']", "        return int(not (root in retired_chains and r['stage']==0) and r['rounds']<t['rounds']")
change("        r=rules[i];label={'day':'每天','week':'每周','month':'每月'}[r['period']]", "        r=rules[i]\n        if r['period']=='once':return f'一次性限购：全账号永久共{r[\"count\"]}份；换经理或重登不刷新。'\n        label={'day':'每天','week':'每周','month':'每月'}[r['period']]")
change("        elif i in bundles:out={**out,'description':bundles[i]['description']+'<BR>'+out.get('description','')}",
       "        elif i in bundles:out={**out,'description':'礼包包含：<BR>'+'<BR>'.join(h.item_def(child)['name']+' ×'+str(count) for child,count in bundles[i]['contents'])}")
change("            root,_,_=stages[i];d=tracks[root]['packages'][str(i)]\n            out={**out,'description':d['description']+'<BR>'+'<BR>'.join(h.item_def(child)['name']+' ×'+str(count) for child,count in d['contents'])}",
       "            root,round_index,index=stages[i];d=tracks[root]['packages'][str(i)]\n            total=sum(price(step,1) for step in tracks[root]['round_steps'][round_index])\n            text=f'第{round_index+1}/{tracks[root][\"rounds\"]}轮，第{index+1}/5档。<BR>本档{price(i,1)}点券；整轮{total}点券。'\n            out={**out,'description':text+'<BR>'+'<BR>'.join(h.item_def(child)['name']+' ×'+str(count) for child,count in d['contents'])}")
change("        return out\n    def pool(i):", "        if str(i) in value_prices:\n            v=value_prices[str(i)];label={'ordinary':'普通限购','chain':'连锁优惠','once':'一次性优惠'}[v['kind']]\n            description=re.sub(r'售价\\d+点券',f'售价{price(i,1)}点券',out.get('description',''))\n            out={**out,'description':description+f'<BR>{label}；同等内容基准价{v[\"quotes\"][\"ordinary\"]}点券。'}\n            out['bunches']=[{**b,'price':price(i,b['bunch'])} for b in out.get('bunches',[])]\n        return out\n    def pool(i):")
change("    def price(i,n,value=lambda:0):\n", "    def price(i,n,value=lambda:0):\n        if str(i) in value_prices:return value_prices[str(i)]['price']*n\n        if value_model is not None and i not in stages and i in h.PACKS:\n            calculated=value_model.quote(i,'ordinary')\n            if calculated>0:return calculated*n\n")
change("            part=h.shop_entry(i,'CHAINED');part.update", "            part=h.shop_entry(i,'CHAINED',root);part.update")
change("shopid=root,_id=str(root),step=min(done,len(parts)-1)","shopid=root,_id=str(root),step=len(parts)-1 if complete else min(done,len(parts)-1)")
change("            return [chained_entry(st,root) for root in tracks]+rows", "            return [chained_entry(st,root) for root in tracks if root not in retired_chains or chain_record(st,root)['stage']>0]+rows")
change("            h._save(st)\n            return h._json({'result':True,'currency':'cash','spent':amount,'chain_round':record,", "            h._save(st)\n            rows=listing(st)\n            return h._json({'result':True,'currency':'cash','spent':amount,'chain_round':record,")
change("                st=h._state();updates={'/shop/list':listing(st)}", "                st=h._state();rows=listing(st);updates={'/shop/list':rows,'/shop/remained/limited':limited_rows(st,rows)}")
change("                'states':{str(root):{'step':record['stage'],'buy':record['rounds']<t['rounds'],'remained':int(record['rounds']<t['rounds']),'remainedperaccount':int(record['rounds']<t['rounds'])}},\n                'resources':h.coach_me_resources(st,h._default_slot(st))+[{'uri':'/shop/list','body':listing(st)}]})",
"                'states':{str(root):chain_status(st,root)},\n                'resources':h.coach_me_resources(st,h._default_slot(st))+[{'uri':'/shop/list','body':rows},{'uri':'/shop/remained/limited','body':limited_rows(st,rows)}]})")
change("    def lifecycle(coach):", "    def chain_status(st,root):\n        row=chained_entry(st,root)\n        return {key:row[key] for key in ('step','buy','remained','remainedperaccount')}\n    def limited_rows(st,rows=None):\n        rows=listing(st) if rows is None else rows\n        return [dict(shopid=row['shopid'],**{key:row[key] for key in ('step','buy','remained','remainedperaccount') if key in row}) for row in rows if 'remained' in row]\n    old_file=h.from_file\n    def from_file(path):\n        if path=='/shop/list':return h._json(listing(h._state()))\n        if path=='/shop/remained/limited':return h._json(limited_rows(h._state()))\n        return old_file(path)\n\n    def lifecycle(coach):")
change("    h.product_packs=cfg;h._product_packs_installed=True", "    h.ENDPOINTS['/shop/remained/limited']=lambda q,b:h._json(limited_rows(h._state()))\n    h.from_file=from_file\n    h.product_packs=cfg;h._product_packs_installed=True\n    if cfg.get('valuation'):\n        from pack_value import ValueModel\n        value_model=ValueModel(h,cfg['valuation']['points_per_ep'])\n        h.pack_expected_value=value_model.value\n        h.pack_value_quote=value_model.quote")
(R/'product_packs.py').write_text(source,'utf-8');(P/'product_packs.py').write_text(source,'utf-8')
shutil.copyfile(R/'pack_value.py',P/'pack_value.py')
base=json.loads((S/'gamedata/product_packs.json').read_text('utf-8'))
elite=json.loads((S/'gamedata/product_chain_elite.json').read_text('utf-8'))
classic=elite['strength_packs']['97700511']['tiers'][0]['pool']
cadence=json.loads((S/'gamedata/pack_cadence.json').read_text('utf-8'))
def ordered_pool(i):return sorted({row[0] for t in cadence['items'][str(i)]['tiers'] for row in t['pool']})
addon=dict(schema=1,edition='20261106-value-priced-v1',limits={},risk_packs={},strength_packs={},bundles={},chains={},chain_only_items=[],retired_chains=[71220101],value_prices={})
# Use the existing fixed TOP10 candidate contract for the final choice pack.
choice=copy.deepcopy(elite['strength_packs']['97610910'])
specs=[(97950008,'精选TOP100·固定+8',ordered_pool(97010100),8),
       (97950009,'精选TOP30·固定+9',ordered_pool(97010130),9),
       (97950010,'经典传奇·固定+10',classic,10),
       (97950011,'传奇TOP30·固定+11',[],11)]
for i,name,pool,grade in specs:
    addon['strength_packs'][str(i)]=dict(name=name,price=1,mode='random',grades=[0]*(grade-1)+[100],
      tiers=[dict(name=name,weight=100,pool=pool)],description=f'每包从本期冻结卡池随机获得1名球员，固定+{grade}；卡池内等概率。')
choice.update(name='传奇TOP10·自选+11',price=1)
addon['strength_packs']['97950111']=choice
for i in addon['strength_packs']:
    addon['chain_only_items'].append(int(i));addon['limits'][i]=dict(count=0,period='month')
# Build frozen top30 from actual current card ratings, not inherited rank labels.
os.environ.update(FO3_GAME='D:/FO3ID/32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
# Import the current complete server first, with no empty unpublished pack loaded.
import http_config as h
ratings=h.card_ovrs(classic)
top30=sorted(classic,key=lambda s:(-ratings[s],s))[:30]
addon['strength_packs']['97950011']['tiers'][0]['pool']=top30
root=71240101;reward_ids=[97950008,97950009,97950010,97950011,97950111]
round_steps=[list(range(root+n*5,root+(n+1)*5)) for n in range(10)]
track=dict(name='精选登顶连锁·价值版',rounds=10,steps=round_steps[0],round_steps=round_steps,packages={},prices={})
for n,steps in enumerate(round_steps):
    for k,(step,reward) in enumerate(zip(steps,reward_ids)):
        track['prices'][str(step)]=1
        track['packages'][str(step)]=dict(name=f'精选登顶连锁·第{n+1}轮第{k+1}/5档',contents=[[reward,1]],description='本轮依次购买；每档固定强化，末档自选热门传奇+11。')
addon['chains'][str(root)]=track
for i,kind,title in [(97960011,'ordinary','普通限购'),(97961011,'once','一次限购')]:
    addon['bundles'][str(i)]=dict(name=title+'·热门传奇自选+11',price=1,contents=[[97950111,1]],description='热门传奇TOP10自选包1个，固定+11；与连锁末档的卡包内容完全相同。')
    addon['limits'][str(i)]=dict(count=5 if kind=='ordinary' else 1,period='day' if kind=='ordinary' else 'once')
# Register additive products into this isolated interpreter without touching old pools.
for i,d in addon['strength_packs'].items():h.PACKS[int(i)]=(d['name'],{'all':True,'grade':len(d['grades']),'icon':'2000006'})
for section in ('bundles',):
    for i,d in addon[section].items():h.PACKAGES[int(i)]=(d['name'],'2000006',d['contents'],d['description'])
for i,d in track['packages'].items():h.PACKAGES[int(i)]=(d['name'],'2000006',d['contents'],d['description'])
old_pool,old_grades=h.pack_pool,h.pack_grades
def pool(i):
    d=addon['strength_packs'].get(str(i))
    return [(s,1) for s in d['tiers'][0]['pool']] if d else old_pool(i)
def grades(i):
    d=addon['strength_packs'].get(str(i));return list(enumerate(d['grades'],1)) if d else old_grades(i)
h.pack_pool,h.pack_grades=pool,grades
h.product_packs['strength_packs'].update(addon['strength_packs'])
from pack_value import ValueModel
unit=ValueModel(h,1)
total=sum(unit.value(i) for i in reward_ids)
# Keep this reworked round close to the reviewed 93,000-point budget, with every
# stage determined by its expected value rather than arbitrary escalating prices.
points_per_ep=93000/(.65*total);model=ValueModel(h,points_per_ep)
new_stages={i for steps in round_steps for i in steps}
all_stages={i for t in h.product_packs['chains'].values() for steps in t['round_steps'] for i in steps}|new_stages
all_ids=set(h.PACKS)|set(h.PACKAGES)|set(h.MONTHLY)
quotes={}
for i in sorted(all_ids):
    d=model.describe(i)
    if not d['expected_ep']:continue
    kind='chain' if i in all_stages or i in h.CHAIN_STEPS else 'once' if i==97961011 else 'ordinary'
    d.update(kind=kind,price=d['quotes'][kind]);quotes[str(i)]=d
# An in-progress retired high-strength round keeps its old price promise; it is
# not offered for a new round. No progress or owned inventory is migrated/reset.
old_track=base['chains']['71220101']
for steps in old_track['round_steps']:
    for i in steps:quotes.pop(str(i),None)
for step in track['prices']:track['prices'][step]=quotes[step]['price']
for i,d in addon['bundles'].items():d['price']=quotes[i]['price']
for i,d in addon['strength_packs'].items():d['price']=quotes[i]['price']
for n,steps in enumerate(round_steps):
    round_price=sum(track['prices'][str(i)] for i in steps)
    for step in steps:track['packages'][str(step)]['description']+=f'<BR>整轮{round_price}点券；连锁按同等内容基准价值约65%定价。'
addon['value_prices']=quotes
addon['valuation']=dict(points_per_ep=points_per_ep,factors=dict(ordinary=1,chain=.65,once=.45),choice_rule='max_selectable_expected_EP',reference_round_target=93000)
addon['hash']=signature(addon)
write(R/'shop_value_products.json',addon);shutil.copyfile(R/'shop_value_products.json',P/'gamedata/shop_value_products.json')
report=dict(status='VALUE_EDITION_BUILT_NOT_INSTALLED',round_price=sum(track['prices'][str(i)] for i in track['steps']),
  stages=[dict(itemid=i,reward=addon['strength_packs'][str(reward)]['name'],**quotes[str(i)]) for i,reward in zip(track['steps'],reward_ids)],
  comparison={str(i):quotes[str(i)] for i in [97960011,97961011,track['steps'][-1]]},priced_products=len(quotes),valuation=addon['valuation'])
write(R/'pricing-report.json',report)
print(json.dumps({k:v for k,v in report.items() if k not in ('stages','comparison')},ensure_ascii=True))
