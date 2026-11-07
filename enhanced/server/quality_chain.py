"""New paid five-stage quality track; old paid rights remain read-only, never reset."""
import copy,functools,json

def install(h):
    if getattr(h,'_quality_chain_installed',False):return
    c=h.pack_cadence;tracks=copy.deepcopy(c.config['chain_tracks']);archived=set(c.config.get('archive_chain_tracks',[]))
    old_steps={i for first in archived for i in h.CHAINED.get(first,())}
    for key,data in tracks.items():
        first=int(key)
        if first in c.chains:raise RuntimeError('New track root collides with issued chain')
        if len(data['steps'])!=5 or data['total_cash']!=sum(data['prices'].values()):raise RuntimeError('Invalid quality track')
        if set(data['steps'])&set(h.CHAIN_STEPS):raise RuntimeError('New track step collision')
        c.chains[first]=data
    def refresh():
        for key,data in tracks.items():
            first=int(key)
            for i,definition in data['packages'].items():h.PACKAGES[int(i)]=h.package_from(definition)
            h.CHAINED[first]=tuple(data['steps'])
        h.CHAIN_STEPS={i:(first,k) for first,steps in h.CHAINED.items() for k,i in enumerate(steps)}
        c.units_cache.clear()
    refresh();prior_apply=h.apply_shop
    @functools.wraps(prior_apply)
    def apply_shop(cfg=None):result=prior_apply(cfg);refresh();return result
    h.apply_shop=apply_shop
    prior_policy=c.policy;prior_floor=c.price_floor;prior_remaining=c.remaining
    new_steps={i for data in tracks.values() for i in data['steps']}
    def policy(i,trail=()):
        if i in old_steps:return {},True
        return prior_policy(i,trail or (-4,)) if i in new_steps else prior_policy(i,trail)
    def floor(i,trail=()):return prior_floor(i,trail or (-4,)) if i in new_steps else prior_floor(i,trail)
    def remaining(st,i):
        if i in old_steps:return 0
        left=prior_remaining(st,i)
        if i not in new_steps or not left:return left
        units,closed=policy(i)
        if closed:return 0
        periods=c.periods();supply=st.get('pack_cadence_supply') or {}
        for group,n in units.items():
            kind='day' if group.endswith('_day') else 'month' if group.endswith('_month') else 'week';used=supply.get(group) or {}
            count=used.get('used',0) if used.get('period')==periods[kind] else 0
            if count+n>c.config['limits'][group]:return 0
        return left
    c.policy=policy;c.price_floor=floor;c.remaining=remaining
    prior_entry=h.chained_entry
    def chained_entry(st,first):
        row=prior_entry(st,first)
        if str(first) in tracks:row['chainedproductname']=tracks[str(first)]['name']
        elif first in archived:
            row['chainedproductname']='旧期已购权益记录·奖励在背包'
            done=c.chain_record(st,first)['done'];count=len(h.CHAINED[first])
            row.update(step=min(done,count-1),buy=False,remained=0,remainedperaccount=int(done<count))
            for k,part in enumerate([row]+row['chained']):
                part['buy']=False
                part['currentstep']='complete' if k<done else 'default'
        return row
    h.chained_entry=chained_entry
    prior_list=h.shop_list
    def listing(st):
        rows=prior_list(st);roots=set(map(int,tracks))
        main=[r for r in rows if r.get('shopcategory')=='CHAINED' and r.get('shopid') in roots]
        other=[r for r in rows if not(r.get('shopcategory')=='CHAINED' and r.get('shopid') in roots|archived)]
        history=[chained_entry(st,first) for first in archived if c.chain_record(st,first)['done']>0]
        return main+other+history
    h.shop_list=listing
    prior_purchase=h.ENDPOINTS['/shop/purchase']
    def purchase(q,b):
        with h.STATE_LOCK:
            out=json.loads(prior_purchase(q,b)[1])
            try:i=int(json.loads(b or b'{}').get('productid') or 0)
            except (ValueError,TypeError,AttributeError):i=0
            if i not in new_steps:return h._json(out)
            st=h._state();first=h.CHAIN_STEPS[i][0];out.setdefault('states',{})[str(first)]=h.chain_status(st,first)
            if out.get('result'):
                resources=[r for r in out.get('resources',[]) if r.get('uri') not in ('/shop/list','/shop/remained/limited')]
                resources+=[{'uri':'/shop/list','body':listing(st)},{'uri':'/shop/remained/limited','body':json.loads(h.ENDPOINTS['/shop/remained/limited']('',b'')[1])}]
                out['resources']=resources
            return h._json(out)
    h.ep_shop_purchase=purchase;h.ENDPOINTS['/shop/purchase']=purchase
    import admin
    def history(p):
        st=h._state()
        return {'old_tracks':{str(first):{'record':c.chain_record(st,first),'future_sale':False,'reward_delivery':'paid contents already credited to native inventory on original purchase','progress_reset':False} for first in archived},'new_tracks':copy.deepcopy(tracks)}
    admin.API['chain_track_history']=history;admin.READ_ONLY.add('chain_track_history')
    previous_publish=admin.API['pack_cadence_publish']
    def publish(p):
        candidate=p.get('config')
        if not isinstance(candidate,dict) or candidate.get('chain_tracks')!=tracks or candidate.get('archive_chain_tracks')!=sorted(archived):raise admin.AdminError('e_cadence_frozen')
        return previous_publish(p)
    admin.API['pack_cadence_publish']=publish
    h.quality_chain_tracks=copy.deepcopy(tracks);h._quality_chain_installed=True
