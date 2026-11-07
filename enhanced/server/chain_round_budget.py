"""One lifetime budget for the five-stage track; ordinary shop quotas stay separate."""
import copy,functools,json

ROOT=71010101
VERSION='chain-round-budget-v1'

def install(h):
    if getattr(h,'_chain_round_budget_installed',False):return
    c=h.pack_cadence;track=c.chains[ROOT];steps=tuple(track['steps'])
    if steps!=tuple(range(ROOT,ROOT+5)) or tuple(track['prices'][str(i)] for i in steps)!=(8000,15000,20000,36000,100000):
        raise RuntimeError('Review changed chain before applying round budget')
    prior_policy=c.policy;prior_remaining=c.remaining
    costs={i:copy.deepcopy(prior_policy(i)[0]) for i in steps}
    totals={}
    for units in costs.values():
        for group,n in units.items():totals[group]=totals.get(group,0)+n
    if totals!={'legend_week':3,'peak_week':2,'classic_month':1}:raise RuntimeError('Unexpected chain reward budget')
    def used_to(done):
        out={}
        for i in steps[:done]:
            for group,n in costs[i].items():out[group]=out.get(group,0)+n
        return out
    def account(st):
        original=c.chain_record(st,ROOT);saved=(st.get('quality_chain_round_supply') or {}).get(str(ROOT)) or {}
        done=min(5,max(int(original['done']),int(saved.get('completed_stages',0))))
        return {'version':VERSION,'owner':original.get('owner'),'owner_appat':original.get('owner_appat'),
                'completed_stages':done,'used':used_to(done),'budget':dict(totals),'lifetime':True}
    def policy(i,trail=()):
        if i in steps:
            # A standalone chain stage uses its lifetime track budget. A nested wrapper
            # must not launder a chain stage into ordinary inventory or a random box.
            return ({},bool(trail))
        return prior_policy(i,trail)
    def remaining(st,i):
        if i not in steps:return prior_remaining(st,i)
        record=account(st);index=steps.index(i)
        # Earlier wrappers close over the old ordinary-week policy. Do not delegate
        # target-stage availability to those closures: retain the same lifetime owner
        # and order contract directly, and use only this track's complete-round budget.
        if c.chain_progress(st,ROOT,0)!=index:return 0
        if record['completed_stages']!=index:return 0
        return int(all(record['used'].get(g,0)+n<=totals[g] for g,n in costs[i].items()))
    c.policy=policy;c.remaining=remaining;c.units_cache.clear()
    def validate(st,context):
        i=context['itemid']
        if i not in steps:return None
        record=account(st);index=steps.index(i)
        if record['completed_stages']!=index or not remaining(st,i):return 'NOT_EXIST_PRODUCT'
        context['chain_round_before']=copy.deepcopy(record)
        return None
    def before_commit(st,context):
        i=context['itemid']
        if i not in steps:return None
        old=context.get('chain_round_before');index=steps.index(i)
        if old is None or old['completed_stages']!=index:return 'NOT_EXIST_PRODUCT'
        actual=c.chain_record(st,ROOT)
        if actual['done']!=index+1:return 'NOT_EXIST_PRODUCT'
        issued=used_to(index+1)
        if any(n>totals[g] for g,n in issued.items()):return 'NOT_EXIST_PRODUCT'
        record=account(st);record.update(completed_stages=index+1,used=issued,
            owner=actual.get('owner'),owner_appat=actual.get('owner_appat'),migrated_from_paid_progress=index>0 and not bool((st.get('quality_chain_round_supply') or {}).get(str(ROOT))))
        st.setdefault('quality_chain_round_supply',{})[str(ROOT)]=record
        return None
    h.register_shop_purchase_hook('validate',validate);h.register_shop_purchase_hook('before_commit',before_commit)
    previous_purchase=h.ENDPOINTS['/shop/purchase']
    @functools.wraps(previous_purchase)
    def purchase(q,b):
        result=previous_purchase(q,b);out=json.loads(result[1])
        try:i=int(json.loads(b or b'{}').get('productid') or 0)
        except (ValueError,TypeError,AttributeError):i=0
        if i not in steps:return result
        st=h._state();record=c.chain_record(st,ROOT);coach=h.my_coach(st)
        if out.get('result'):
            out['chain_round_budget']=account(st)
        else:
            index=steps.index(i);done=account(st)['completed_stages'];price=track['prices'][str(i)]
            if record.get('owner_deleted'):
                code,text='CHAIN_OWNER_UNAVAILABLE','本期连锁属于原经理，请先恢复原经理'
            elif record.get('owner') is not None and (record['owner']!=str(coach['_id']) or record.get('owner_appat')!=coach.get('appat')):
                code,text='CHAIN_WRONG_MANAGER','请使用本期连锁的首购经理继续购买'
            elif done>=5:code,text='CHAIN_ALREADY_COMPLETE','本期五档连锁已全部购买，不能重复购买'
            elif index<done:code,text='CHAIN_STAGE_ALREADY_BOUGHT','本档已经购买，奖励已发到背包'
            elif index>done:code,text='CHAIN_PREVIOUS_STAGE_REQUIRED',f'请先购买本期第{done+1}档'
            elif int(coach.get('cash',0))<price:code,text='CHAIN_NOT_ENOUGH_CASH',f'点券不足，本档需要{price}点券'
            else:code,text='CHAIN_PURCHASE_UNAVAILABLE','本档暂不可购买，请刷新商城后重试'
            out.update(reason=text,reason_code=code,purchase_reason={'code':code,'text':text,'required_cash':price,'completed_stages':done})
        return h._json(out)
    h.ep_shop_purchase=purchase;h.ENDPOINTS['/shop/purchase']=purchase
    import admin
    def status(p):
        st=h._state();record=account(st)
        return {'track':ROOT,'mode':'one_lifetime_round','record':record,'ordinary_shop_quotas_unchanged':True,
                'remaining_by_stage':{str(i):remaining(st,i) for i in steps}}
    admin.API['chain_round_budget']=status;admin.READ_ONLY.add('chain_round_budget')
    h.quality_chain_round_budget={'version':VERSION,'track':ROOT,'costs':copy.deepcopy(costs),'budget':dict(totals),'mode':'one_lifetime_round'}
    h._chain_round_budget_installed=True
