"""New-SKU additive product payload; integration belongs to the shared shop owner."""
from pathlib import Path
import copy,hashlib,json
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');design=json.loads((R/'chain-design.json').read_text('utf-8'))
random_id,fixed_id,moment_id=97819000,97819011,97819084;root=71231901
prices=[18000,42000,88000,168000,288000];quantities=[5,8,10,12,15]
def product(name,pool,grades,description,price):return dict(name=name,price=price,mode='random',grades=grades,tiers=[dict(name=name,weight=100,pool=pool)],description=description)
pool=design['pool'];moments=design['bonus_cards_per_round'][1]['pool']
items={str(random_id):product('怀旧神兽·+8～+12随机',pool,[0]*7+[40,27,20,10,3],'每包随机获得1名怀旧神兽球员，仅含19赛季88人。<BR>强化+8/+9/+10/+11/+12概率：40%/27%/20%/10%/3%。<BR>每包独立抽取，+12不是保底。',12000),
 str(fixed_id):product('怀旧神兽·固定+11',pool,[0]*10+[100],'每轮末档保底：随机获得1名19赛季怀旧神兽球员，固定+11。<BR>仅含本期冻结88人，不保证指定球员。',240000),
 str(moment_id):product('怀旧连锁·传奇时刻固定+1',moments,[100],f'每轮末档额外获得1名传奇时刻球员，固定+1。<BR>仅含84赛季本期冻结{len(moments)}人；随机等概率。<BR>本连锁共10轮，全部完成最多获得10包。',600000)}
rounds=[list(range(root+r*5,root+(r+1)*5)) for r in range(10)]
track=dict(name='怀旧神兽连锁',rounds=10,steps=rounds[0],round_steps=rounds,prices={},packages={})
for round_index,steps in enumerate(rounds):
 for stage,(sid,q,price) in enumerate(zip(steps,quantities,prices)):
  contents=[[random_id,q]]+([[fixed_id,1],[moment_id,1]] if stage==4 else [])
  rewards=f'怀旧神兽随机包×{q}'
  if stage==4:rewards+='、怀旧神兽固定+11包×1、传奇时刻固定+1包×1'
  text=f'第{round_index+1}/10轮，第{stage+1}/5档。<BR>{rewards}。<BR>本档{price}点券；整轮{sum(prices)}点券。<BR>每轮共50个怀旧随机包；+8/+9/+10/+11/+12概率40%/27%/20%/10%/3%。<BR>加末档保底，每轮平均约6张+11、1.5张+12；平均产出不是每轮承诺，+12无保底。'
  track['prices'][str(sid)]=price;track['packages'][str(sid)]=dict(name=f'怀旧神兽连锁·第{round_index+1}轮第{stage+1}档',contents=contents,description=text)
addon=dict(schema=1,edition='nostalgia-chain-19-v1',limits={str(i):dict(count=0,period='month') for i in (random_id,fixed_id,moment_id)},risk_packs={},strength_packs=items,bundles={},chains={str(root):track},chain_only_items=[random_id,fixed_id,moment_id])
def signature(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
addon['hash']=signature(addon)
old=json.loads((S/'gamedata/product_packs.json').read_text('utf-8'))
issued=set()
for section in ('limits','risk_packs','strength_packs','bundles','chains'):issued|=set(map(int,old.get(section,{})))
for chain in old['chains'].values():issued|=set(map(int,chain['packages']))
new=set((random_id,fixed_id,moment_id))|{s for row in rounds for s in row}
assert not new&issued and len(new)==53
for row in rounds:
 contents=[x for sid in row for x in track['packages'][str(sid)]['contents']]
 assert sum(n for i,n in contents if i==random_id)==50
 assert sum(n for i,n in contents if i==fixed_id)==1 and sum(n for i,n in contents if i==moment_id)==1
assert len({s for row in rounds for s in row})==50
for item in items.values():assert sum(item['grades'])==100
assert set(items[str(random_id)]['tiers'][0]['pool'])==set(pool)
(R/'nostalgia-product-addon.json').write_text(json.dumps(addon,ensure_ascii=False,indent=2),'utf-8')
report=dict(status='ADDITIVE_SHOP_PAYLOAD_NOT_INSTALLED',random_item=random_id,fixed11_item=fixed_id,moment1_item=moment_id,chain_root=root,rounds=10,stages=5,round_price=sum(prices),random_per_round=50,fixed11_per_round=1,moment1_per_round=1,expected11_per_round=6,expected12_per_round=1.5,all_new_skus_collision_checked=True,probability_signature=addon['hash'],price_policy='Proposed existing classic-chain five-stage ladder; shared shop owner may adjust before first publication.',production_written=False)
(R/'chain-addon-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report,ensure_ascii=True))
