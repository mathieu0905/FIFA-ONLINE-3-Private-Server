"""Build a fresh, additive chain edition from current code; no formal writes/listener."""
from pathlib import Path
import sys,os,json,hashlib,copy,sqlite3,math
sys.dont_write_bytecode=True
R=Path(__file__).parent;S=Path(r'D:\FO3ID\server');P=R/'checks-runtime/server';OUT=R/'payload';OUT.mkdir(exist_ok=True)
def signature(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def write(path,d):path.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def audit(event,args):
 if event=='open':
  path,mode,flags=args
  if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
   if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Build writes restricted to task temporary files')
sys.addaudithook(audit)
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
import http_config as h
cfg=h.product_packs;market=set(h.market_spids());ratings=h.card_ovrs(market)
retired={int(c['fo3_spid']) for c in json.loads((P/'gamedata/custom_rosters.json').read_text('utf8')).get('retired_cards',[])}
classic=cfg['strength_packs']['97700511']['tiers'][0]['pool']
pools={'classic':classic,'og':cfg['strength_packs']['97819000']['tiers'][0]['pool'],
 'moments':cfg['strength_packs']['97819084']['tiers'][0]['pool'],'icon':[s for s in market if s//1000000==12],
 'top100':cfg['strength_packs']['97950008']['tiers'][0]['pool']}
for name,pool in pools.items():
 eligible=set(pool)&market-retired
 assert eligible,name
 pools[name]=sorted(eligible,key=lambda s:(-ratings[s],s))
with sqlite3.connect('file:'+str(P/'gamedata/fifadb.sqlite').replace('\\','/')+'?mode=ro',uri=True) as db:
 search={s:dict(team=t,league=l,name=' '.join(str(x or '') for x in (en,ind))) for s,t,l,en,ind in db.execute('SELECT p.spid,p.teamid,p.leagueid,e.full,i.full FROM players p LEFT JOIN nameseng e ON e.playerid=p.playerid LEFT JOIN namesind i ON i.playerid=p.playerid')}
addon=dict(schema=1,edition='20261106-balanced-quality-chains-v2',limits={},risk_packs={},strength_packs={},bundles={},chains={},
 chain_only_items=[],retired_chains=sorted(map(int,cfg['chains'])),value_prices={},
 design=dict(points_per_yuan=100,premium_round_points=[400000,500000],chain_discount=.65,
             price_rule='same current player-value EP coefficient for every new pack; choice uses maximum selectable value; fixed grade only; round price is sum of contents',
             existing_inventory_unchanged=True,unfinished_legacy_rounds_preserved=True))
coefficient=cfg['valuation']['points_per_ep'];pack_id=98100000;pack_cache={};values={};units={}
def pack(group,top,grade,choice=False):
 global pack_id
 pool=pools[group][:top] if top else pools[group];key=(group,tuple(pool),grade,choice)
 if key in pack_cache:return pack_cache[key]
 pack_id+=1;i=pack_id
 assert i not in h.PACKS and i not in h.ITEMS and i not in h.PACKAGES
 labels={'classic':'经典传奇','og':'怀旧神兽','moments':'传奇时刻','icon':'ICON传奇精选','top100':'精选球星'}
 scope=f'TOP{len(pool)}' if top else f'{len(pool)}人池'
 name=f'臻选新期·{labels[group]}{scope}·'+('自选' if choice else '固定')+f'+{grade}'
 ep=max(h.player_value_price(s,grade) for s in pool) if choice else sum(h.player_value_price(s,grade) for s in pool)/len(pool)
 ordinary=max(300,math.ceil(ep*coefficient/100)*100);chain=max(200,math.ceil(ep*coefficient*.65/100)*100);once=max(100,math.ceil(ep*coefficient*.45/100)*100)
 assert once<chain<ordinary
 season_text={'classic':'EL/UL/CEL/MUL/WL等经典传奇','og':'19赛季怀旧神兽','moments':'84赛季传奇时刻','icon':'12赛季ICON传奇精选','top100':'本期冻结精选赛季球星'}[group]
 desc=[f'每包获得1名{season_text}球员，固定+{grade}。',f'卡池{len(pool)}张赛季卡；TOP按当前等级1、+1原生能力排序，同分按卡编号；同人不同赛季分别占位。',
       f'从本期冻结{len(pool)}张卡中自选1张；取消不消耗。' if choice else '卡池内逐张等概率随机；不保证指定球员。',
       '新期连锁专属奖励，不单独售卖。']
 d=dict(name=name,price=ordinary,mode='choice' if choice else 'random',grades=[0]*(grade-1)+[100],
        tiers=[dict(name=season_text,weight=100,pool=pool)],search={str(s):search[s] for s in pool} if choice else {},description='<BR>'.join(desc))
 addon['strength_packs'][str(i)]=d;addon['chain_only_items'].append(i);addon['limits'][str(i)]=dict(count=0,period='once')
 addon['value_prices'][str(i)]=dict(expected_ep=ep,standard_points=ep*coefficient,quotes=dict(ordinary=ordinary,chain=chain,once=once),kind='ordinary',price=ordinary)
 pack_cache[key]=i;values[i]=ep;units[i]=chain
 return i
specs=[
 (71250101,'精选进阶连锁·臻选新期',False,[(pack('top100',100,9),2),(pack('classic',30,10),1),(pack('classic',30,11),1),(pack('classic',10,10,True),1),(pack('classic',10,11,True),1)]),
 (71250201,'经典传奇登顶·臻选新期',True,[(pack('classic',30,11),2),(pack('classic',10,12,True),1),(pack('classic',10,12),2),(pack('classic',10,13),2),(pack('classic',10,14,True),2)]),
 (71250301,'怀旧神兽典藏·臻选新期',True,[(pack('og',30,10),1),(pack('og',0,11),1),(pack('og',30,11),1),(pack('og',0,12),1),(pack('og',10,12,True),1)]),
 (71250401,'传奇时刻收藏·臻选新期',True,[(pack('moments',60,3),1),(pack('moments',30,3),1),(pack('moments',30,4),1),(pack('moments',10,4,True),1),(pack('moments',10,5,True),1)]),
 (71250501,'五档全自选·臻选新期',True,[(pack('classic',10,12,True),1),(pack('icon',10,13,True),1),(pack('classic',10,14,True),1),(pack('moments',10,4,True),1),(pack('og',10,12,True),1)]),
]
summary=[]
for root,name,premium,rewards in specs:
 assert root not in h.CHAINED
 steps=[list(range(root+n*5,root+(n+1)*5)) for n in range(10)]
 costs=[units[i]*n for i,n in rewards];ep=sum(values[i]*n for i,n in rewards);total=sum(costs)
 assert all(a<b for a,b in zip(costs,costs[1:])),costs
 if premium:assert 400000<=total<=500000,(name,total)
 track=dict(name=name,rounds=10,steps=steps[0],round_steps=steps,packages={},prices={})
 for round_index,stage_ids in enumerate(steps):
  for k,(step,(reward,count),cost) in enumerate(zip(stage_ids,rewards,costs)):
   assert step not in h.PACKS and step not in h.PACKAGES and step not in h.ITEMS
   track['prices'][str(step)]=cost
   track['packages'][str(step)]=dict(name=f'{name}·第{round_index+1}轮第{k+1}/5档',contents=[[reward,count]],description=f'本档{cost}点券；整轮{total}点券（按100点券=1元，约{total/100:g}元）。<BR>每档均为固定强化精品；最多10轮，按顺序购买。')
   v=addon['value_prices'][str(reward)];q={kind:v['quotes'][kind]*count for kind in ['ordinary','chain','once']}
   addon['value_prices'][str(step)]=dict(expected_ep=values[reward]*count,standard_points=values[reward]*count*coefficient,quotes=q,kind='chain',price=cost)
 addon['chains'][str(root)]=track
 summary.append(dict(root=root,name=name,premium=premium,prices=costs,round_points=total,round_yuan=total/100,expected_ep=ep,
                     points_per_expected_ep=total/ep,cards=sum(n for i,n in rewards),stages=[dict(pack=i,count=n,name=addon['strength_packs'][str(i)]['name']) for i,n in rewards]))
rates=[t['points_per_expected_ep'] for t in summary];assert max(rates)/min(rates)<1.015
addon['hash']=signature(addon);write(OUT/'chain_rebalance_products.json',addon)
source=(S/'product_packs.py').read_text('utf8')
old="for addon_name in ('product_chain_elite.json','shop_value_products.json'):";assert source.count(old)==1
source=source.replace(old,"for addon_name in ('product_chain_elite.json','shop_value_products.json','chain_rebalance_products.json'):")
old="visible=i not in retired,forceenable=False";assert source.count(old)==1
source=source.replace(old,"visible=i not in retired and i not in chain_only,forceenable=False")
old="chainedproductname=t['name']+f'（第{min(r[\"rounds\"]+1,t[\"rounds\"])}/{t[\"rounds\"]}轮）',";assert source.count(old)==1
source=source.replace(old,"chainedproductname=('旧期续购·' if root in retired_chains else '')+t['name']+f'（第{min(r[\"rounds\"]+1,t[\"rounds\"])}/{t[\"rounds\"]}轮）',")
old="out={**out,'description':text+'<BR>'+'<BR>'.join(h.item_def(child)['name']+' ×'+str(count) for child,count in d['contents'])}";assert source.count(old)==1
source=source.replace(old,old+"\n            if root in retired_chains:out['description']='旧期未完成轮次：原价格与奖励保留；可选择不续购，新期连锁独立上架。<BR>'+out['description']")
compile(source,'product_packs.py','exec');(OUT/'product_packs.py').write_text(source,encoding='utf8')
write(R/'summary.json',dict(status='BUILD_PASS',chains=summary,ratio_spread=max(rates)/min(rates),new_packs=len(addon['strength_packs']),legacy_configs_unchanged=True))
# Only copied runtime files change here; no HTTP service is created.
(P/'product_packs.py').write_text(source,encoding='utf8');write(P/'gamedata/chain_rebalance_products.json',addon)
print(json.dumps(dict(status='BUILD_PASS',round_points=[t['round_points'] for t in summary],new_packs=len(addon['strength_packs']),ratio_spread=max(rates)/min(rates))))
