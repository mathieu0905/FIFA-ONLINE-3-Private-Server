"""Native quota/stock refresh contract. Does not change economic limits or saves."""
import functools
import json


def install(h):
    if getattr(h, '_shop_stock_contract_installed', False):return
    c=h.pack_cadence
    prior_entry=h.shop_entry;prior_file=h.from_file
    prior_limited=h.ENDPOINTS['/shop/remained/limited']
    prior_purchase=h.ENDPOINTS['/shop/purchase']

    @functools.wraps(prior_entry)
    def entry(itemid,category='PLAYERPACK',shopid=None):
        row=prior_entry(itemid,category,shopid)
        # Chain children use a different native progress protocol, kept intact.
        if itemid not in h.CHAIN_STEPS:
            units,closed=c.policy(itemid)
            if units:
                left=c.remaining(h._state(),itemid)
                maximum=max(1,min(c.config['limits'][group]//n for group,n in units.items()))
                row.update(forceenable=False,limittotalcount=maximum,remained=left,
                           limitcountperaccount=maximum,remainedperaccount=left,buy=left>0)
        return row
    h.shop_entry=entry

    def stock(st):
        rows=json.loads(prior_limited('',b'')[1]);byid={r['shopid']:r for r in rows}
        for row in h.shop_list(st):
            itemid=int(row['product']['itemid'])
            if itemid in h.CHAIN_STEPS:continue
            units,closed=c.policy(itemid)
            if not units:continue
            left=c.remaining(st,itemid)
            byid[row['shopid']]={'shopid':row['shopid'],'remained':left,'remainedperaccount':left,'buy':left>0}
        return list(byid.values())

    def listing_response():return h._json(h.shop_list(h._state()))
    def limited(q,b):return h._json(stock(h._state()))
    @functools.wraps(prior_file)
    def from_file(path):
        if path=='/shop/list':return listing_response()
        if path=='/shop/remained/limited':return limited('',b'')
        return prior_file(path)
    h.from_file=from_file
    h.ENDPOINTS['/shop/list']=lambda q,b:listing_response()
    h.ENDPOINTS['/shop/remained/limited']=limited

    def purchase(q,b):
        with h.STATE_LOCK:
            out=json.loads(prior_purchase(q,b)[1]);st=h._state()
            try:
                request=json.loads(b or b'{}');itemid=int(request.get('productid') or 0)
                index=int(request.get('bunch',0))
                if itemid not in h.CHAIN_STEPS and out.get('reason')=='NOT_EXIST_PRODUCT' and itemid not in h.SHOP_HIDDEN and itemid in h.PACKS:
                    options=h.item_def(itemid)['bunches'];units,closed=c.policy(itemid)
                    if closed or not c.active(itemid):
                        out.update(reason='此卡包本期未上架，请选择当前在售商品。',reason_code='PRODUCT_NOT_ON_SALE')
                    if 0<=index<len(options) and units and not closed and c.active(itemid) and c.remaining(st,itemid)<options[index]['bunch']:
                        groups='、'.join({'legend_week':'每周传奇','peak_week':'每周巅峰','classic_month':'每月经典'}.get(g,g) for g in units)
                        text='本期共享额度不足（'+groups+'），请等待额度刷新或选择其他卡包。'
                        out.update(reason=text,reason_code='QUOTA_EXHAUSTED',purchase_reason={'code':'QUOTA_EXHAUSTED','text':text,'remaining':c.remaining(st,itemid),'groups':units})
            except (ValueError,TypeError,KeyError,IndexError,OverflowError):pass
            rows=h.shop_list(st);counts=stock(st)
            states=dict(out.get('states') or {})
            for row in counts:
                i=row['shopid']
                if i not in h.CHAIN_STEPS:states[str(i)]={k:v for k,v in row.items() if k!='shopid'}
            out['states']=states
            updates={'/shop/list':rows,'/shop/remained/limited':counts}
            for path in ('/specifictarget','/shop/list/STSHOP','/shop/remained/limited/STSHOP'):
                updates[path]=json.loads(h.ENDPOINTS[path]('',b'')[1])
            out['resources']=[r for r in out.get('resources',[]) if r.get('uri') not in updates]+[{'uri':uri,'body':body} for uri,body in updates.items()]
            return h._json(out)
    h.ep_shop_purchase=purchase;h.ENDPOINTS['/shop/purchase']=purchase
    h._shop_stock_contract_installed=True

