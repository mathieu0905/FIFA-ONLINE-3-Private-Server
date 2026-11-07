"""Build a new product policy without modifying any installed files."""
from pathlib import Path
import copy,hashlib,json,os,secrets,shutil,sys
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');P=R/'sandbox/server'
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf8');P.mkdir(parents=True,exist_ok=True)
for p in [*S.glob('*.py'),*S.glob('*.json')]:shutil.copyfile(p,P/p.name)
for n in ('gamedata','responses','admin','tools'):shutil.copytree(S/n,P/n,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.bak*','*.log','migration-backups','replays'))
os.environ.update(FO3_GAME=r'D:\FO3ID\32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
sys.path.insert(0,str(P));sys.argv=['http_config.py']
import http_config as h
def sig(c):return hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
cfg=dict(schema=1,edition='20261106-independent-products-v1',token_key=secrets.token_hex(32),limits={},risk_packs={},bundles={},chains={})
special={97010004:(20,'week'),97010005:(10,'week'),97010100:(20,'week'),97010130:(10,'week'),97010110:(10,'week'),97010007:(10,'month')}
for i in sorted(set(h.PACKS)|set(h.PACKAGES)|set(h.MONTHLY)):
    if i in h.CHAIN_STEPS or h.pack_cadence.policy(i)[1]:continue
    if i in h.pack_cadence.items:
        n,period=special.get(i,(100,'day'))
    elif str(i) in h.pack_catalogue['items']:
        d=h.pack_catalogue['items'][str(i)]
        n,period=(20,'week') if d['mode']=='choice' else (20,'day') if d['supply']=='legend_day' else (100,'day')
    else:n,period=(20,'day') if i in h.PACKAGES or i in h.MONTHLY else (100,'day')
    cfg['limits'][str(i)]=dict(count=n,period=period)
registry=json.loads((S/'gamedata/custom_rosters.json').read_text(encoding='utf8'))
retired_cards={int(card['fo3_spid']) for card in registry.get('retired_cards',[])}
cfg['excluded_retired_cards']=sorted(retired_cards)
market=set(h.market_spids())-retired_cards;ratings=h.card_ovrs(market)
low=sorted(s for s in market if ratings[s]+h.GRADE_BOOST[1]<=65)
assert len(low)>100
r9=30037576
assert r9 in market
legend=sorted(s for s in market if s//1000000 in (27,30,31,33,48,93))
elite=sorted(s for s in market if ratings[s]+h.GRADE_BOOST[1]>=85 and s not in legend)
assert elite and legend
cfg['risk_packs']['97300011']=dict(name='+11大罗冲击包',price=3000,grades=[0]*10+[100],tiers=[
    dict(name='传奇大罗',weight=1,pool=[r9]),dict(name='低能力球员',weight=999,pool=low)],
    description='每包获得1名固定+11球员。<BR>传奇档0.1%：UL（终极传奇）罗纳尔多，仅1张候选。<BR>普通档99.9%：原生等级1、+1能力不高于65的可交易球员；在普通档内等概率。<BR>强化固定+11，但绝大多数结果为低能力卡；没有大罗保底。')
cfg['risk_packs']['97300012']=dict(name='全赛季大起大落包·+1～+11',price=1500,grades=[35,20,15,10,7,5,3,2,1.5,1,.5],tiers=[
    dict(name='普通',weight=70,pool=low),dict(name='精英',weight=25,pool=elite),dict(name='传奇',weight=5,pool=legend)],
    description='每包随机获得1名球员，强化+1～+11。<BR>球员档位：普通70%、精英25%、传奇5%；各档内等概率。<BR>传奇季：EL（欧洲传奇）、UL（终极传奇）、CEL（欧洲联赛传奇）、MUL（曼联传奇）、WL（世界传奇）。<BR>强化独立抽取：+1为35%、+2为20%、+3为15%、+4为10%、+5为7%、+6为5%、+7为3%、+8为2%、+9为1.5%、+10为1%、+11为0.5%。<BR>可能获得低能力+1，也可能获得传奇+11；没有高档或最高强化保底。')
for i in ('97300011','97300012'):cfg['limits'][i]=dict(count=100,period='day')
cfg['bundles']['97400020']=dict(name='冒险二十包礼包',price=48000,contents=[[97300011,10],[97300012,10]],description='内含20个卡包：+11大罗冲击包10个、大起大落包10个。各包单独开奖，礼包不保证传奇或大罗。')
cfg['bundles']['97400100']=dict(name='冒险百包礼包',price=190000,contents=[[97300011,40],[97300012,60]],description='内含100个卡包：+11大罗冲击包40个、大起大落包60个。各包单独开奖，没有礼包大罗保底。')
for i in cfg['bundles']:cfg['limits'][i]=dict(count=5,period='day')
cfg['strength_packs']={};cfg['retired_sale_items']=list(map(int,h.pack_catalogue['items']))
for oldid,d in sorted(h.pack_catalogue['items'].items(),key=lambda pair:(pair[1]['order'],int(pair[0]))):
    d=copy.deepcopy(d);d['pool']=[spid for spid in d['pool'] if spid not in retired_cards]
    assert d['pool'],'New issuance cannot have an empty pool'
    d['search']={key:value for key,value in d['search'].items() if int(key) not in retired_cards}
    i=int(oldid)+400000;choice=d['mode']=='choice'
    name=d['name'].replace('·随机+1','·随机+5～+10').replace('自选+1','自选固定+8').replace('·10选1·+1','·10选1·固定+8')
    action=f'从{len(d["pool"])}张冻结赛季卡中任选1名，固定+8。' if choice else f'从{len(d["pool"])}张冻结赛季卡中等概率随机获得1名球员，强化+5～+10。'
    season_lines=[line for line in d['description'].split('<BR>') if line.startswith(('包含赛季','TOP10按'))]
    if choice:
        desc=action+'<BR>'+'<BR>'.join(season_lines)+'<BR>背包使用后选定1人再确认；取消不消耗。'
        grades=[0]*7+[100];price=min(96000,max(6000,d['price']*10))
    else:
        grades=[0]*4+[35,25,20,12,6,2];price=min(24000,max(600,d['price']*8))
        desc=action+'<BR>'+'<BR>'.join(season_lines)+'<BR>强化独立抽取：+5为35%、+6为25%、+7为20%、+8为12%、+9为6%、+10为2%；没有最高强化保底。'
    cfg['strength_packs'][str(i)]=dict(name=name,mode=d['mode'],price=price,grades=grades,tiers=[dict(name='指定赛季',weight=100,pool=d['pool'])],description=desc,search=d['search'])
    cfg['limits'][str(i)]=copy.deepcopy(cfg['limits'][oldid])
cfg['bundles']['97400010']=dict(name='传奇高强十连礼包',price=216000,contents=[[97500900,10]],description='内含10个纯传奇合集随机+5～+10卡包；每包独立开奖，不保证+10。')
cfg['limits']['97400010']=dict(count=10,period='day')
for oldroot,newroot,title in [(71010101,71220101,'高强五档连锁·十轮版'),(70000001,71220201,'成长五档连锁·十轮版')]:
    oldsteps=h.CHAINED[oldroot];round_steps=[list(range(newroot+r*len(oldsteps),newroot+(r+1)*len(oldsteps))) for r in range(10)];newsteps=round_steps[0]
    packages={};prices={}
    for r,steps in enumerate(round_steps):
        for index,(oldi,i) in enumerate(zip(oldsteps,steps)):
            oldname,icon,contents,description=h.PACKAGES[oldi]
            packages[str(i)]=dict(name=f'{title}·第{r+1}轮第{index+1}档',contents=[list(x) for x in contents],description='本连锁最多购买10轮，按顺序购买；当前档奖励即时发到背包，不占其它商品购买次数。')
            prices[str(i)]=h.product_price(oldi,1)
    cfg['chains'][str(newroot)]=dict(name=title,rounds=10,steps=newsteps,round_steps=round_steps,packages=packages,prices=prices)
# Final user-approved enhancement curve, equally applied to the new random lines.
from pack_probability import probabilities
curve=[0]*5+probabilities(6,11)
probabilities='强化独立抽取：+6为30%、+7为28%、+8为25%、+9为10%、+10为6%、+11为1%。'
for item in list(cfg['risk_packs'].values())+list(cfg['strength_packs'].values()):
    if item.get('mode')=='choice':continue
    item['grades']=list(curve)
    item.update(min_grade=6,max_grade=11,probability_mode='formula',probability_formula='six-anchor-v1')
    item['name']=item['name'].replace('+5～+10','+6～+11').replace('+1～+11','+6～+11').replace('+11大罗冲击包','大罗冲击包·+6～+11')
    original=item['description'].split('<BR>')
    original=[line for line in original if not line.startswith('强化')]
    original=[line.replace('固定+11','强化+6～+11').replace('强化+5～+10','强化+6～+11').replace('强化+1～+11','强化+6～+11').replace('低能力+1，','低能力+6，') for line in original]
    item['description']='<BR>'.join(original+[probabilities,'最高+11不是保底。'])
cfg['risk_packs']['97300011']['description']+='<BR>大罗+11总概率0.001%（十万分之一），没有大罗保底。'
for item in cfg['bundles'].values():
    item['description']=item['description'].replace('+11大罗冲击包','大罗冲击包').replace('+5～+10','+6～+11').replace('不保证+10','不保证+11')
cfg['hash']=sig(cfg)
(R/'product_packs.json').write_text(json.dumps(cfg,ensure_ascii=False,separators=(',',':')),encoding='utf8')
cat=(S/'pack_catalogue.py').read_text(encoding='utf8')
cat=cat.replace("    def remaining(st, itemid):\n", "    def remaining(st, itemid):\n        if getattr(h, '_per_product_limits', False) and itemid in entries:\n            return h.item_purchase_remaining(st, itemid)\n",1)
cat=cat.replace("            cap = config['limits'][entries[itemid]['supply']]", "            cap = h.item_purchase_limit(itemid)['count'] if getattr(h, '_per_product_limits', False) else config['limits'][entries[itemid]['supply']]")
for name in ('validate_purchase','commit_purchase'):
    cat=cat.replace(f'    def {name}(st, context):\n', f"    def {name}(st, context):\n        if getattr(h, '_per_product_limits', False):\n            return None\n",1)
assert cat.count("if getattr(h, '_per_product_limits', False)")==4
(R/'pack_catalogue.py').write_text(cat,encoding='utf8')
source=(S/'http_config.py').read_text(encoding='utf8');marker='if __name__ == "__main__":\n    # Windows'
assert source.count(marker)==1
source=source.replace(marker,'import product_packs\nproduct_packs.install(sys.modules[__name__])\n\n'+marker)
(R/'http_config.py').write_text(source,encoding='utf8')
for n in ('http_config.py','pack_catalogue.py','product_packs.py'):shutil.copyfile(R/n,P/n)
shutil.copyfile(R/'product_packs.json',P/'gamedata/product_packs.json')
(R/'baseline.json').write_text(json.dumps({n:hashlib.sha256((S/n).read_bytes()).hexdigest() for n in ('http_config.py','pack_catalogue.py','gamedata/pack_cadence.json','gamedata/pack_catalogue.json')},indent=2),encoding='utf8')
print(json.dumps(dict(products=len(cfg['limits']),risk=len(cfg['risk_packs']),chains=len(cfg['chains']),low_cards=len(low),r9_spid=r9)))
