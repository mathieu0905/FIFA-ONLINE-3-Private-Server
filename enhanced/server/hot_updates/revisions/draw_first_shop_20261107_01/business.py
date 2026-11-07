"""Draw-first shop availability. Existing inventories and chain contracts are unchanged."""

def contains_choice(host, itemid, trail):
    if itemid in trail:
        raise ValueError('Cyclic package')
    trail=trail+(itemid,)
    if itemid in host.PACKS:
        return host.item_def(itemid).get('category')=='DRAFTPACK'
    if itemid in host.PACKAGES:
        return any(contains_choice(host,i,trail) for i,n in host.PACKAGES[itemid][2] if n>0)
    if itemid in host.MONTHLY:
        return any(contains_choice(host,i,trail) for i,n in host.MONTHLY[itemid][3]+host.MONTHLY[itemid][4] if n>0)
    return False

def blocked(host, itemid):
    # Existing ordered chain contracts remain on their original purchase path.
    if any(str(itemid) in t['packages'] for t in host.product_packs['chains'].values()):
        return False
    return contains_choice(host,itemid,())

def filter_rows(host, rows):
    return [r for r in rows if isinstance(r.get('chained'),list) or not blocked(host,int(r.get('product',{}).get('itemid',0)))]

def shop_list(host, query, body):
    with host.STATE_LOCK:
        return host._json(filter_rows(host,host.shop_list(host._state())))

def remained(host, query, body):
    import json
    with host.STATE_LOCK:
        out=json.loads(host.ENDPOINTS['/shop/remained/limited'](query,body)[1])
        return host._json([r for r in out if not blocked(host,int(r.get('shopid',0)))])

def refresh_response(host, response):
    import json
    out=json.loads(response[1])
    for resource in out.get('resources',[]):
        if resource.get('uri')=='/shop/list':resource['body']=filter_rows(host,resource['body'])
        elif resource.get('uri')=='/shop/remained/limited':
            resource['body']=[r for r in resource['body'] if not blocked(host,int(r.get('shopid',0)))]
    return host._json(out)

def round_purchase(host, query, body):
    with host.STATE_LOCK:
        return refresh_response(host,host.ENDPOINTS['/shop/chain/round/purchase'](query,body))

def purchase(host, query, body):
    import json
    with host.STATE_LOCK:
        try:
            req=json.loads(body or b'{}')
            itemid=int(req.get('productid') or 0) or int(req.get('shopid') or 0)%host.MP_SHOPID%host.STSHOPID
        except (ValueError,TypeError,AttributeError):
            return host._json(dict(result=False,reason='INVALID_PARAM'))
        if blocked(host,itemid):
            return host._json(dict(result=False,reason='NOT_EXIST_PRODUCT',message='自选商品已停售，请选择随机卡包；已持有的自选包仍可正常使用。'))
        return refresh_response(host,host.ENDPOINTS['/shop/purchase'](query,body))
