"""Additive elite-chain release; never rewrite the already issued product config."""
from pathlib import Path
import copy,hashlib,json,os,shutil,sys
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');P=R/'sandbox/server'
R.mkdir(parents=True,exist_ok=True);P.mkdir(parents=True,exist_ok=True)
for source in [*S.glob('*.py'),*S.glob('*.json')]:shutil.copyfile(source,P/source.name)
for name in ('gamedata','responses','admin','tools'):shutil.copytree(S/name,P/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.bak*','*.log','migration-backups','replays'))
base=json.loads((S/'gamedata/product_packs.json').read_text(encoding='utf8'))
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.dont_write_bytecode=True;sys.path.insert(0,str(P));sys.argv=['http_config.py']
import http_config as h
market=h.market_spids();ratings=h.card_ovrs(market)
retired_cards={int(card['fo3_spid']) for card in json.loads((S/'gamedata/custom_rosters.json').read_text(encoding='utf8')).get('retired_cards',[])}
mainstream=sorted(spid for spid in market if spid//1000000 in (13,22,23,24,91) and ratings[spid]+h.GRADE_BOOST[1]>=85 and spid not in retired_cards)
classic=sorted(spid for spid in base['strength_packs']['97500900']['tiers'][0]['pool'] if ratings[spid]+h.GRADE_BOOST[1]>=85 and spid not in retired_cards)
assert mainstream and classic and 30037576 in classic
addon=dict(schema=1,edition='20261106-elite-chains-v1',limits={},strength_packs={},risk_packs={},bundles={},chains={},chain_only_items=[97700511,97610910])
addon['retired_sale_items']=[97300011,97300012,97400020,97400100]
safe_risk=97310012
safe=copy.deepcopy(base['risk_packs']['97300012'])
safe.update(name='主流强者包·+6～+11',tiers=[dict(name='主流精英',weight=75,pool=mainstream),dict(name='经典传奇',weight=25,pool=classic)])
safe['description']='每包获得1名基础+1能力85以上的球员，强化随机+6～+11。<BR>主流精英75%：CP（队长）、LP（忠诚）、CC（洲际冠军）、WB（世界最佳）、现役精选。<BR>经典传奇25%：EL（欧洲传奇）、UL（终极传奇）、CEL（欧洲联赛传奇）、MUL（曼联传奇）、WL（世界传奇）。<BR>不含普通年份卡及84赛季（传奇时刻）。<BR>强化+6/7/8/9/10/11概率为30/28/25/10/6/1%，没有最高强化保底。'
addon['risk_packs'][str(safe_risk)]=safe
addon['limits'][str(safe_risk)]=copy.deepcopy(base['limits']['97300012'])
shock=copy.deepcopy(base['risk_packs']['97300011'])
shock.update(name='纯传奇大罗冲击·+6～+11',tiers=[dict(name='经典传奇',weight=95,pool=[s for s in classic if s!=30037576]),dict(name='传奇大罗',weight=5,pool=[30037576])])
shock['description']='每包保证获得1名经典传奇球员，基础+1能力85以上，强化随机+6～+11。<BR>经典传奇95%、UL（终极传奇）大罗5%；不含普通球员、年份卡、冷门国家传奇或传奇时刻。<BR>包含EL（欧洲传奇）、UL（终极传奇）、CEL（欧洲联赛传奇）、MUL（曼联传奇）、WL（世界传奇）。<BR>强化+6/7/8/9/10/11概率为30/28/25/10/6/1%。<BR>大罗+11总概率0.05%，无大罗或最高强化保底。'
addon['risk_packs']['97310011']=shock;addon['limits']['97310011']=copy.deepcopy(base['limits']['97300011'])
registry=json.loads((S/'gamedata/custom_rosters.json').read_text(encoding='utf8'))
moments=sorted({int(card['fo3_spid']) for card in registry['cards'] if int(card['fo3_spid'])//1000000==84})
assert len(moments)==123
moments_id=97310084
assert str(moments_id) not in base['limits']
addon['risk_packs'][str(moments_id)]=dict(name='传奇时刻·随机固定+1',price=600000,grades=[100],mode='random',
    tiers=[dict(name='传奇时刻',weight=100,pool=moments)],
    description='从123名传奇时刻赛季球员中随机获得1名，固定+1。<BR>售价600000点券，每经理每周限购1包。')
addon['limits'][str(moments_id)]=dict(count=1,period='week',scope='manager')
for old,new in ((97400020,97410020),(97400100,97410100)):
    bundle=copy.deepcopy(base['bundles'][str(old)])
    bundle['name']='主流强者二十包礼包' if old==97400020 else '主流强者百包礼包'
    bundle['description']=bundle['description'].replace('大起大落包','主流强者包').replace('大罗冲击包','新版大罗冲击包')
    bundle['contents']=[[safe_risk if child==97300012 else 97310011 if child==97300011 else child,count] for child,count in bundle['contents']]
    bundle['description']+='\n<BR>本版所含冒险包排除84传奇时刻；不提供时刻卡。'
    addon['bundles'][str(new)]=bundle;addon['limits'][str(new)]=copy.deepcopy(base['limits'][str(old)])
legend=copy.deepcopy(base['strength_packs']['97500900']);legend.update(name='纯传奇合集·固定+11',price=240000,grades=[0]*10+[100],mode='random')
legend['tiers'][0]['pool']=classic
legend['description']='连锁专属：每包随机获得1名固定+11传奇球员。<BR>包含赛季：EL（欧洲传奇）、UL（终极传奇）、CEL-A/B（欧洲联赛传奇）、MUL（曼联传奇）、WL（世界传奇）。<BR>冻结卡池内等概率；保证传奇与+11，不保证指定球员。'
for key in ('min_grade','max_grade','probability_mode','probability_formula'):legend.pop(key,None)
choice=copy.deepcopy(base['strength_packs']['97600910']);choice.update(name='纯传奇TOP10·自选+11',price=1200000,grades=[0]*10+[100],mode='choice')
choice['description']='连锁专属：从本期冻结的10名传奇候选中任选1名，固定+11。<BR>TOP10按本期原生等级1、+1能力排名。<BR>背包使用后选人，确认后消耗；取消不消耗。'
addon['strength_packs']={'97700511':legend,'97610910':choice}
for itemid in addon['chain_only_items']:addon['limits'][str(itemid)]=dict(count=0,period='month')
offers=[(71230101,'传奇登顶连锁',[
    (18000,[[97500900,2],[97500093,1]]),
    (42000,[[97500900,5],[97300012,10]]),
    (88000,[[97600910,1],[97500900,10]]),
    (168000,[[97700511,1],[97500900,15]]),
    (288000,[[97610910,1],[97700511,2],[97500900,20]])]),
    (71230201,'百包冒险连锁',[
    (6000,[[97300012,20]]),
    (18000,[[97300011,20],[97300012,30]]),
    (48000,[[97300011,50],[97300012,50]]),
    (108000,[[97300011,100],[97300012,100],[97700511,1]]),
    (228000,[[97300011,200],[97300012,300],[97700511,2]])])]
summary=[]
offers=[(root,'传奇百包连锁' if root==71230201 else title,[(price,[[97310011 if child in (97300011,97300012,97500900,97500093) else child,count] for child,count in contents]) for price,contents in stages]) for root,title,stages in offers]
for root,title,stages in offers:
    stages=[(price,list({child:sum(n for other,n in contents if other==child) for child,_ in contents}.items())) for price,contents in stages]
    rounds=[list(range(root+r*5,root+(r+1)*5)) for r in range(10)]
    track=dict(name=title,rounds=10,steps=rounds[0],round_steps=rounds,packages={},prices={})
    for r,steps in enumerate(rounds):
        for k,(itemid,(price,contents)) in enumerate(zip(steps,stages)):
            total=sum(n for _,n in contents)
            track['prices'][str(itemid)]=price
            track['packages'][str(itemid)]=dict(name=f'{title}·第{r+1}轮第{k+1}档',contents=contents,
                description=f'第{k+1}/5档，内含{total}个卡包；本轮须依次购买。<BR>整轮共{sum(p for p,_ in stages)}点券，最多10轮。<BR>本连锁独立进度，奖励不占其它商品购买次数。')
    addon['chains'][str(root)]=track
    summary.append(dict(name=title,round_price=sum(p for p,_ in stages),round_packs=sum(n for _,items in stages for _,n in items),stages=[dict(price=p,contents=items) for p,items in stages]))
def sig(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
nostalgia_path=Path(r'D:\fifaol3\nostalgic-season\nostalgia-product-addon.json')
if nostalgia_path.exists():
    nostalgia=json.loads(nostalgia_path.read_text(encoding='utf8'))
    assert nostalgia['hash']==sig({key:value for key,value in nostalgia.items() if key!='hash'})
    for section in ('limits','risk_packs','strength_packs','bundles','chains'):
        assert not (set(addon[section]) & set(nostalgia[section]))
        addon[section].update(nostalgia[section])
    addon['chain_only_items']+=nostalgia['chain_only_items']
    addon['source_editions']=[nostalgia['edition']]
addon['hash']=sig(addon)
(R/'product_chain_elite.json').write_text(json.dumps(addon,ensure_ascii=False,separators=(',',':')),encoding='utf8')
source=(S/'product_packs.py').read_text(encoding='utf8')
anchor="    risks={int(k):v for k,v in {**cfg['risk_packs'],**cfg.get('strength_packs',{})}.items()}"
assert source.count(anchor)==1
source=source.replace(anchor,"""    extra_path=Path(h.HERE)/'gamedata/product_chain_elite.json'
    if extra_path.exists():
        extra=json.loads(extra_path.read_text(encoding='utf8'))
        if extra['hash']!=signature({k:v for k,v in extra.items() if k!='hash'}):raise ValueError('Invalid elite-chain signature')
        for section in ('limits','risk_packs','strength_packs','bundles','chains'):
            if set(cfg.get(section,{})) & set(extra.get(section,{})):raise ValueError('Elite issue cannot replace existing products')
            cfg[section]={**cfg.get(section,{}),**extra.get(section,{})}
        cfg['chain_only_items']=list(extra.get('chain_only_items',[]))
        cfg['additional_editions']=[extra['edition']]
        cfg['retired_sale_items']=sorted(set(cfg.get('retired_sale_items',[])) | set(extra.get('retired_sale_items',[])))
        cfg['newly_retired_items']=list(extra.get('retired_sale_items',[]))
    chain_only=set(cfg.get('chain_only_items',[]))
"""+anchor,1)
assert source.count('        if i in retired:return 0')==1 and source.count('        if i in retired:return {},True')==1
source=source.replace('        if i in retired:return 0','        if i in retired or i in chain_only:return 0',1).replace('        if i in retired:return {},True','        if i in retired or i in chain_only:return {},True',1)
assert source.count('        elif i in rules:')==1
source=source.replace('        elif i in rules:','        elif i in rules and i not in chain_only:',1)
source=source.replace('旧版+1卡包已停售；背包中已持有的仍按原规则开启。','旧版商品已停售；已持有的卡包或礼包仍按原规则兑现。')
anchor='        if i in retired:\n'
assert source.count(anchor)==1
source=source.replace(anchor,anchor+"            if i in cfg.get('newly_retired_items',[]):out={**out,'name':'旧版·'+out['name']}\n",1)
old="        rule=rules[i];record=(st.get('product_purchase_counts') or {}).get(str(i)) or {}"
assert source.count(old)==1
source=source.replace(old,"        rule=rules[i];owner=h.my_coach(st) if rule.get('scope')=='manager' else st\n        record=(owner.get('product_purchase_counts') or {}).get(str(i)) or {}",1)
old="            st.setdefault('product_purchase_counts',{})[str(i)]={'period':p,'used':used+context['bunch'],'rule_version':cfg['edition']}"
assert source.count(old)==1
source=source.replace(old,"            owner=h.my_coach(st) if rules[i].get('scope')=='manager' else st\n            owner.setdefault('product_purchase_counts',{})[str(i)]={'period':p,'used':used+context['bunch'],'rule_version':cfg['edition']}",1)
old="            rows.append({'spid':s,'grade':8,'price':h.player_value_price(s,8),'expandme':'player'})"
assert source.count(old)==1
source=source.replace(old,"            grade=next(g for g,w in enumerate(d['grades'],1) if w)\n            rows.append({'spid':s,'grade':grade,'price':h.player_value_price(s,grade),'expandme':'player'})",1)
from nonce_patch import apply as apply_nonce
source=apply_nonce(source)
(R/'product_packs.py').write_text(source,encoding='utf8')
shutil.copyfile(R/'product_packs.py',P/'product_packs.py');shutil.copyfile(R/'product_chain_elite.json',P/'gamedata/product_chain_elite.json')
(R/'chain-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
(R/'publication-graph.json').write_text(json.dumps(dict(old_rights_preserved=[97300011,97300012,97400020,97400100],retire_new_purchase_only=addon['retired_sale_items'],successors={'97300011':97310011,'97300012':97310012,'97400020':97410020,'97400100':97410100},new_chain_roots=list(addon['chains']),minimum_new_regular_base_ability=85,new_risk_tiers=[dict(name=t['name'],weight=t['weight'],pool_count=len(t['pool']),moments=sum(spid//1000000==84 for spid in t['pool'])) for t in safe['tiers']],classic_chain_moments_probability=0,nostalgia_moments_per_round=1,nostalgia_max_rounds=10,only_controlled_moments_sku=moments_id,moments_price=600000,moments_limit=addon['limits'][str(moments_id)],moments_grade=1,old_base_file_sha256=hashlib.sha256((S/'gamedata/product_packs.json').read_bytes()).hexdigest()),ensure_ascii=False,indent=2),encoding='utf8')
(R/'baseline.json').write_text(json.dumps({name:hashlib.sha256((S/name).read_bytes()).hexdigest() for name in ('product_packs.py','gamedata/product_packs.json')},indent=2),encoding='utf8')
print(json.dumps(dict(status='OFFLINE_CANDIDATE',chains=summary),ensure_ascii=True))
