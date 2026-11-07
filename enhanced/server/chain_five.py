"""Append-only five-stage welcome chain; install after cadence, before descriptions."""
import copy, functools, json

FIRST=70000001
FOUR=70000004
FIVE=70000005
EDITION='20261106-quality-chain-five-v3'

def install(h):
    if getattr(h,'_chain_five_installed',False):return
    c=h.pack_cadence
    old=copy.deepcopy(c.chains[FIRST])
    if old['steps']!=[70000001,70000002,70000003]:raise RuntimeError('Review prior chain edition before appending')
    data=copy.deepcopy(old)
    data['steps']+= [FOUR,FIVE]
    data['prices'].update({str(FOUR):6000,str(FIVE):18000})
    data['packages'].update({
        str(FOUR):{'name':'成长连锁4/5·首期前锋定向','icon':'2000006','description':'6000点券：优质赛季精选+5至+7×3、精英+7至+9×1、首期前锋定向+7至+9×1（固定97010010，不轮换）。终生一次；无传奇/巅峰周供应消耗。','contents':[[97010001,3],[97010002,1],[97010010,1]]},
        str(FIVE):{'name':'成长连锁5/5·传奇追逐','icon':'2000006','description':'18000点券：每周传奇+8至+10包×1、精英+7至+9×2、精选+5至+7×4。终生一次；与商城共用每周传奇供应1单位，余量不足须等WIB周一刷新。卡包到背包，不自动开。','contents':[[97010004,1],[97010002,2],[97010001,4]]}})
    c.chains[FIRST]=data
    previous_apply=h.apply_shop
    def refresh():
        targeted=97010010  # Frozen entitlement; native static-data cache cannot change this SKU.
        data['packages'][str(FOUR)]['contents'][-1][0]=targeted
        for key,value in data['packages'].items():
            itemid=int(key);definition=copy.deepcopy(value)
            if itemid in old['steps']:definition['name']=f'成长连锁{old["steps"].index(itemid)+1}/5·'+['启航','定位','精英'][old['steps'].index(itemid)]
            h.PACKAGES[itemid]=h.package_from(definition)
        h.CHAINED[FIRST]=tuple(data['steps'])
        h.CHAIN_STEPS={i:(root,k) for root,steps in h.CHAINED.items() for k,i in enumerate(steps)}
        c.units_cache.clear()
        return targeted
    @functools.wraps(previous_apply)
    def apply_shop(cfg=None):
        result=previous_apply(cfg);refresh();return result
    h.apply_shop=apply_shop
    prior_policy=c.policy;prior_floor=c.price_floor;prior_remaining=c.remaining
    def new_chain_step(itemid):
        return itemid in h.CHAIN_STEPS and h.CHAIN_STEPS[itemid][0]==FIRST and itemid not in old['steps']
    def policy(itemid,trail=()):
        return prior_policy(itemid,trail or (-1,)) if new_chain_step(itemid) else prior_policy(itemid,trail)
    def floor(itemid,trail=()):
        return prior_floor(itemid,trail or (-1,)) if new_chain_step(itemid) else prior_floor(itemid,trail)
    def remaining(st,itemid):
        available=prior_remaining(st,itemid)
        if itemid not in h.CHAIN_STEPS or not available:return available
        units,closed=policy(itemid)
        if closed:return 0
        periods=c.periods();supply=st.get('pack_cadence_supply') or {}
        for group,needed in units.items():
            period='day' if group.endswith('_day') else 'month' if group.endswith('_month') else 'week';saved=supply.get(group) or {}
            used=saved.get('used',0) if saved.get('period')==periods[period] else 0
            if c.config['limits'][group]-used<needed:return 0
        return available
    c.policy=policy;c.price_floor=floor;c.remaining=remaining
    def status(st,first):
        steps=h.CHAINED[first];done=c.chain_progress(st,first,0)
        open_stage=done<len(steps)
        buy=open_stage and bool(c.remaining(st,steps[done]))
        return {'step':min(done,len(steps)-1),'buy':buy,'remainedperaccount':int(open_stage),'remained':int(buy)}
    def chained_entry(st,first):
        if first==FIRST:refresh()
        steps=h.CHAINED[first];done=c.chain_progress(st,first,0);state=status(st,first);parts=[]
        for k,itemid in enumerate(steps):
            entry=dict(h.shop_entry(itemid,'CHAINED'),shopid=first,index=k+1,maxCount=len(steps),limitcountperaccount=1,
                remainedperaccount=int(k>=done),remained=int(k>=done),buy=k==done and state['buy'],
                currentstep='complete' if k<done else 'activity' if k==done and state['buy'] else 'default')
            # Every stage belongs to the SAME native root shop; productid identifies its SKU.
            parts.append(entry)
        title=(h._SHOP.get('chain_names') or {}).get(str(first)) or '建队成长连锁·五阶段'
        return dict(parts[0],**state,chained=parts[1:],chainedproductname=title)
    previous_limited=h.ENDPOINTS['/shop/remained/limited']
    def limited(q,b):
        rows=json.loads(previous_limited(q,b)[1]);st=h._state()
        return h._json([dict(shopid=FIRST,**status(st,FIRST)) if r.get('shopid')==FIRST else r for r in rows])
    previous_purchase=h.ENDPOINTS['/shop/purchase']
    def purchase(q,b):
        with h.STATE_LOCK:
            targeted=refresh();out=json.loads(previous_purchase(q,b)[1])
            try:itemid=int(json.loads(b or b'{}').get('productid') or 0)
            except (ValueError,TypeError,AttributeError):itemid=0
            if itemid not in data['steps']:return h._json(out)
            st=h._state();out.setdefault('states',{})[str(FIRST)]=status(st,FIRST)
            if out.get('result'):
                resources=[r for r in out.get('resources',[]) if r.get('uri') not in ('/shop/list','/shop/remained/limited')]
                resources+=[{'uri':'/shop/list','body':h.shop_list(st)},{'uri':'/shop/remained/limited','body':json.loads(limited('',b'')[1])}]
                out['resources']=resources
                if itemid==FOUR:out['chain_reward_snapshot']={'edition':EDITION,'targeted_itemid':targeted,'contents':copy.deepcopy(data['packages'][str(FOUR)]['contents'])}
            return h._json(out)
    h.chained_entry=chained_entry;h.chain_status=status;h.ep_shop_purchase=purchase
    h.ENDPOINTS['/shop/purchase']=purchase;h.ENDPOINTS['/shop/remained/limited']=limited
    h.chain_five={'edition':EDITION,'root':FIRST,'steps':data['steps'],'legacy_exempt_steps':old['steps'],'prices':data['prices'],'targeted_itemid':97010010,'rotation':False}
    refresh();h._chain_five_installed=True
