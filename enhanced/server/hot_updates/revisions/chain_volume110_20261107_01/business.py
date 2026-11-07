def volume_data():
    import json,zlib,base64
    return json.loads(zlib.decompress(base64.b64decode('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')))

def volume_engine(host):
    import copy,json,hmac,hashlib,secrets,time,types
    from urllib.parse import parse_qs
    tracks={int(k):v for k,v in volume_data().items()}
    h=types.SimpleNamespace(**vars(host))
    h.ENDPOINTS=dict(host.ENDPOINTS)
    cfg={**host.product_packs,'chains':{**host.product_packs['chains'],**{str(k):v for k,v in tracks.items()}}}
    h.product_packs=cfg
    retired=set(cfg.get('retired_chains',[]));secret=bytes.fromhex(cfg['token_key'])
    stages={int(i):(root,rn,k) for root,t in tracks.items() for rn,steps in enumerate(t['round_steps']) for k,i in enumerate(steps)}
    def price(i,n):
        if i in stages:return tracks[stages[i][0]]['prices'][str(i)]*n
        return host.product_price(i,n)
    h.product_price=price
    def definition(i):
        if i not in stages:return host.item_def(i)
        root,rn,k=stages[i];d=tracks[root]['packages'][str(i)];out=copy.deepcopy(host.item_def(i))
        out.update(name=d['name'],description=f'第{rn+1}/10轮，第{k+1}/5档：共{d["count"]}包，其中精品包{d["premium_count"]}个。<BR>本档{d["price"]:,}点券；整轮110包。<BR>'+'<BR>'.join(host.item_def(child)['name']+' ×'+str(n) for child,n in d['contents']),bunches=[dict(bunch=1,price=d['price'])],items=[dict(itemid=child,count=n,staticdata=host.item_def(child)) for child,n in d['contents']])
        if d['premium_count']==0:
            featured=host.item_def(d['contents'][0][0])
            out['itemicon']=featured['itemicon'];out['bundleicon']=featured.get('bundleicon',featured['itemicon'])
        return out
    h.item_def=definition
    def chain_entry(st,row):
        root=row.get('shopid')
        if root not in tracks:return row
        row=copy.deepcopy(row);record=st.get('product_chain_rounds',{}).get(str(root),{});versions=record.get('volume_stage_versions',{})
        for part in [row]+row.get('chained',[]):
            i=int(part['product']['itemid'])
            if part.get('currentstep')=='complete' and versions.get(str(i))!='volume110-v1':continue
            d=definition(i);part['product']['staticdata']=d
        row['chainedproductname']=tracks[root]['name']+f'（第{min(record.get("rounds",0)+1,10)}/10轮·整轮110包）'
        return row
    h.chained_entry=lambda st,root:chain_entry(st,host.chained_entry(st,root))
    def old_listing(st):return [chain_entry(st,r) for r in filter_rows(host,host.shop_list(st))]

    def owner(st):
      c=h.my_coach(st);return [str(c['_id']),str(c.get('appat')),str(c.get('_admin_generation'))]

    def snapshot(st,root):
      if root not in tracks:return None
      t=tracks[root];r=st.get('product_chain_rounds',{}).get(str(root),{})
      rn=int(r.get('rounds',0));stage=int(r.get('stage',0));c=h.my_coach(st)
      if rn<0 or rn>=t['rounds'] or stage<0 or stage>=len(t['steps']) or (root in retired and stage==0):return None
      if r.get('owner') is not None and (r['owner']!=str(c['_id']) or r.get('owner_appat')!=c.get('appat')):return None
      steps=t['round_steps'][rn][stage:];rewards={};prices=[]
      for i in steps:
       prices.append(h.product_price(i,1))
       for child,n in t['packages'][str(i)]['contents']:rewards[child]=rewards.get(child,0)+n
      return dict(root=root,owner=owner(st),round=rn,stage=stage,steps=steps,prices=prices,total=sum(prices),rewards=[[i,n] for i,n in rewards.items()])

    def sign(q):return hmac.new(secret,json.dumps(q,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode(),hashlib.sha256).hexdigest()

    def decorate(rows,st):
      result=[]
      for row in rows:
       root=row.get('shopid');q=snapshot(st,root) if root in tracks else None
       result.append(dict(row,round_buy_supported=root in tracks,round_buy_enabled=q is not None,
                          round_buy_total=q['total'] if q else 0,round_buy_stages=len(q['steps']) if q else 0))
      return result

    def listing(st):return decorate(old_listing(st),st)

    def response(st,receipt,replayed=False):
      root=receipt['root'];entry=h.chained_entry(st,root);rows=listing(st)
      counts=json.loads(h.ENDPOINTS['/shop/remained/limited']('',b'')[1])
      return h._json(dict(result=True,currency='cash',spent=receipt['spent'],replayed=replayed,round_completed=receipt['round_completed'],
        message=f'本轮剩余档位已全部购买，共花费{receipt["spent"]:,}点券。奖励已进入背包。',
        states={str(root):{k:entry[k] for k in ('step','buy','remained','remainedperaccount')}},
        resources=h.coach_me_resources(st,h._default_slot(st))+[dict(uri='/shop/list',body=rows),dict(uri='/shop/remained/limited',body=counts)]))

    def quote(query,body):
      try:root=int(parse_qs(query.lstrip('?')).get('root',['0'])[0])
      except (ValueError,TypeError):return h._json(dict(result=False,message='无效的连锁编号。'))
      with h.STATE_LOCK:
       st=h._state();q=snapshot(st,root)
       if q is None:return h._json(dict(result=False,message='当前连锁已完成，或不能继续购买此轮。请刷新商城。'))
       q.update(expires=int(time.time())+180,nonce=secrets.token_hex(16));q['signature']=sign(q)
       t=tracks[root];labels=[f'{h.item_def(i)["name"]} ×{n}' for i,n in q['rewards']]
       message=f'{t["name"]}\n第{q["round"]+1}轮，购买剩余{len(q["steps"])}档。\n总价：{q["total"]:,}点券\n奖励：\n'+'\n'.join(labels)+'\n\n仅购买当前这一轮的剩余档位；不会连续购买下一轮。'
       return h._json(dict(result=True,quote=q,message=message))

    def purchase(query,body):
      try:req=json.loads(body or b'{}');q=req['quote'];sig=q['signature']
      except (ValueError,TypeError,KeyError):return h._json(dict(result=False,message='购买报价缺失，请重新点击本轮购买。'))
      if not isinstance(q,dict) or not isinstance(sig,str):return h._json(dict(result=False,message='无效报价。'))
      unsigned={k:v for k,v in q.items() if k!='signature'}
      expected={'root','owner','round','stage','steps','prices','total','rewards','expires','nonce'}
      if set(unsigned)!=expected or not hmac.compare_digest(sig,sign(unsigned)):return h._json(dict(result=False,message='报价验证失败，请重新获取价格。'))
      key=hashlib.sha256((q['nonce']+sig).encode()).hexdigest()
      with h.STATE_LOCK:
       st=h._state();c=h.my_coach(st);receipt=st.get('product_chain_bulk_receipts',{}).get(key)
       if q['owner']!=owner(st):return h._json(dict(result=False,message='经理已切换，请重新获取报价。'))
       if receipt:return response(st,receipt,True)
       if not isinstance(q['expires'],int) or q['expires']<time.time():return h._json(dict(result=False,message='报价已过期，请重新点击购买。'))
       current=snapshot(st,q['root'])
       if current is None or any(q[k]!=v for k,v in current.items()):return h._json(dict(result=False,message='本轮进度或价格已变化，请刷新后重试。'))
       if int(c.get('cash',0))<current['total']:return h._json(dict(result=False,message=f'点券不足，本轮剩余档位需要{current["total"]:,}点券。'))
       h.add_cash(st,-current['total'],'shop:round:'+str(q['root']))
       for child,n in current['rewards']:h.inventory_add(c,child,n)
       record=copy.deepcopy(st.get('product_chain_rounds',{}).get(str(q['root']),{}))
       record.update(owner=str(c['_id']),owner_appat=c.get('appat'),rounds=current['round']+1,stage=0)
       record.setdefault('volume_stage_versions',{}).update({str(i):'volume110-v1' for i in current['steps']})
       st.setdefault('product_chain_rounds',{})[str(q['root'])]=record
       receipt=dict(root=q['root'],spent=current['total'],round_completed=current['round']+1,owner=owner(st),granted=current['rewards'])
       st.setdefault('product_chain_bulk_receipts',{})[key]=receipt
       h._save(st)  # One atomic persistence commit for cash, rewards, progress and receipt.
       return response(st,receipt)
    def counts(st):
        return [dict(shopid=r['shopid'],**{key:r[key] for key in ('step','buy','remained','remainedperaccount') if key in r}) for r in listing(st) if 'remained' in r]
    h.ENDPOINTS['/shop/remained/limited']=lambda q,b:h._json(counts(h._state()))
    def single(req,i):
        root,rn,k=stages[i];st=h._state();coach=h.my_coach(st)
        current=snapshot(st,root)
        if isinstance(req.get('bunch',0),bool) or req.get('bunch',0)!=0 or req.get('shopid',root) not in (root,i) or current is None or current['round']!=rn or current['stage']!=k:
            return h._json(dict(result=False,reason='请按当前轮次的档位顺序购买。'))
        amount=price(i,1)
        if int(coach.get('cash',0))<amount:return h._json(dict(result=False,reason='NOT_ENOUGH_CASH'))
        h.add_cash(st,-amount,'shop:'+str(i))
        for child,n in tracks[root]['packages'][str(i)]['contents']:h.inventory_add(coach,child,n)
        record=copy.deepcopy(st.get('product_chain_rounds',{}).get(str(root),{}))
        record.update(owner=str(coach['_id']),owner_appat=coach.get('appat'),rounds=rn,stage=k+1)
        if k+1==5:record.update(rounds=rn+1,stage=0)
        record.setdefault('volume_stage_versions',{})[str(i)]='volume110-v1'
        st.setdefault('product_chain_rounds',{})[str(root)]=record
        h._save(st)
        receipt=dict(root=root,spent=amount,round_completed=record['rounds'])
        out=json.loads(response(st,receipt)[1]);out['message']='本档购买完成，卡包已进入背包。';out['chain_round']=record
        return h._json(out)
    return dict(listing=listing,counts=counts,quote=quote,purchase=purchase,single=single,stages=stages,snapshot=snapshot)

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
    with host.STATE_LOCK:return host._json(volume_engine(host)['listing'](host._state()))


def remained(host, query, body):
    with host.STATE_LOCK:return host._json(volume_engine(host)['counts'](host._state()))


def refresh_response(host, response):
    import json
    out=json.loads(response[1]);engine=volume_engine(host);st=host._state()
    for r in out.get('resources',[]):
        if r.get('uri')=='/shop/list':r['body']=engine['listing'](st)
        elif r.get('uri')=='/shop/remained/limited':r['body']=engine['counts'](st)
    return host._json(out)


def round_purchase(host, query, body):
    with host.STATE_LOCK:return volume_engine(host)['purchase'](query,body)


def purchase(host, query, body):
    import json
    with host.STATE_LOCK:
        try:
            req=json.loads(body or b'{}')
            itemid=int(req.get('productid') or 0) or int(req.get('shopid') or 0)%host.MP_SHOPID%host.STSHOPID
        except (ValueError,TypeError,AttributeError):
            return host._json(dict(result=False,reason='INVALID_PARAM'))
        engine=volume_engine(host)
        if itemid in engine['stages']:return engine['single'](req,itemid)
        if blocked(host,itemid):
            return host._json(dict(result=False,reason='NOT_EXIST_PRODUCT',message='自选商品已停售，请选择随机卡包；已持有的自选包仍可正常使用。'))
        return refresh_response(host,host.ENDPOINTS['/shop/purchase'](query,body))

def open_pack(host, query, body):
    return host.ep_item_use(host.hot_path_params['item_id'],query,body)

def round_quote(host, query, body):
    with host.STATE_LOCK:return volume_engine(host)['quote'](query,body)

