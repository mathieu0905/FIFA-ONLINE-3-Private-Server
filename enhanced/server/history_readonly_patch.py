"""Native chain render flags and paid-history projection. No state writes or rewards."""
import copy,functools,json

def install(h):
    if getattr(h,'_history_readonly_patch_installed',False):return
    c=h.pack_cadence;archived=set(c.config.get('archive_chain_tracks',[]))
    def paid(st,first):return min(len(h.CHAINED[first]),max(0,int(c.chain_record(st,first)['done'])))
    def status(st,first):
        n=paid(st,first)
        return {'step':max(0,n-1),'buy':False,'remained':0,'remainedperaccount':0}
    def project(row,st):
        first=row.get('shopid')
        if row.get('shopcategory')!='CHAINED':return row
        row=copy.deepcopy(row)
        # Native setChainedData adds this only when shopcategory is undefined;
        # our explicit child categories skip that branch. Tile completion rendering
        # itself is gated on data.chained, independently of currentstep.
        for child in row.get('chained',[]):child['chained']=True
        if first not in archived:
            if not row.get('buy') and row.get('remainedperaccount',0)>0:
                steps=h.CHAINED.get(first,());index=int(row.get('step',0))
                if 0<=index<len(steps):
                    periods=c.periods();units,_=c.policy(steps[index]);supply=st.get('pack_cadence_supply') or {};blocked=[]
                    for group,needed in units.items():
                        kind='day' if group.endswith('_day') else 'month' if group.endswith('_month') else 'week'
                        record=supply.get(group) or {};used=record.get('used',0) if record.get('period')==periods[kind] else 0
                        if used+needed>c.config['limits'][group]:blocked.append(group)
                    label=short=None
                    if any(g.endswith('_month') for g in blocked):label='本月固定+10额已用';short='待下月额度'
                    elif 'peak_week' in blocked:label='本周巅峰额已用';short='待下周巅峰额'
                    elif 'legend_week' in blocked:label='本周传奇额已用';short='待下周传奇额'
                    elif blocked:label='共享供应已用完';short='待共享额度'
                    if label:
                        row['status_reason']=label
                        if not row.get('chainedproductname','').endswith('·'+label):row['chainedproductname']=row.get('chainedproductname','')+'·'+label
                        current=([row]+row.get('chained',[]))[index];data=current.get('product',{}).get('staticdata',{})
                        if not data.get('name','').endswith('【'+short+'】'):data['name']=data.get('name','')+'【'+short+'】'
            return row
        n=paid(st,first)
        if not n:return None
        parts=([row]+row.get('chained',[]))[:n]
        for k,part in enumerate(parts):
            part.update(shopid=first,index=k+1,maxCount=n,buy=False,remained=0,remainedperaccount=0,currentstep='complete',__bannervisible=False)
        row.update(**status(st,first),chained=parts[1:],paid_history_count=n,original_track_length=len(h.CHAINED[first]),
            archived_readonly=True,chainedproductname=f'旧期已购{n}档权益记录·奖励在背包')
        return row
    def rows(body,st):return [view for row in body if (view:=project(row,st)) is not None]
    previous_entry=h.chained_entry
    def entry(st,first):
        row=previous_entry(st,first)
        if first not in archived:return row
        return project(row,st) or dict(row,visible=False,chained=[],paid_history_count=0,**status(st,first))
    previous_list=h.shop_list
    def listing(st):return rows(previous_list(st),st)
    previous_status=h.chain_status
    def chain_status(st,first):return status(st,first) if first in archived else previous_status(st,first)
    def limited_rows(body,st):return [dict(row,**status(st,row['shopid'])) if row.get('shopid') in archived else row for row in body]
    previous_limited=h.ENDPOINTS['/shop/remained/limited']
    def limited(q,b):
        result=previous_limited(q,b);return h._json(limited_rows(json.loads(result[1]),h._state()))
    previous_purchase=h.ENDPOINTS['/shop/purchase']
    @functools.wraps(previous_purchase)
    def purchase(q,b):
        result=previous_purchase(q,b);out=json.loads(result[1]);st=h._state()
        if isinstance(out.get('states'),dict):
            for first in archived:
                if str(first) in out['states']:out['states'][str(first)]=status(st,first)
        for resource in out.get('resources',[]):
            if resource.get('uri')=='/shop/list':resource['body']=rows(resource['body'],st)
            elif resource.get('uri')=='/shop/remained/limited':resource['body']=limited_rows(resource['body'],st)
        return h._json(out)
    h.chained_entry=entry;h.shop_list=listing;h.chain_status=chain_status
    h.ep_shop_purchase=purchase;h.ENDPOINTS['/shop/purchase']=purchase
    h.ENDPOINTS['/shop/remained/limited']=limited
    h._history_readonly_patch_installed=True
