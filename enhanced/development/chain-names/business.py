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
    chain_pack_ids={i for t in tracks.values() for p in t['packages'].values() for i,n in p['contents']}
    def price(i,n):
        if i in stages:return tracks[stages[i][0]]['prices'][str(i)]*n
        return host.product_price(i,n)
    h.product_price=price
    def definition(i):
        if i not in stages:
            return clean_pack_definition(host,i) if i in chain_pack_ids else host.item_def(i)
        root,rn,k=stages[i];d=tracks[root]['packages'][str(i)];out=copy.deepcopy(host.item_def(i))
        out.update(name=d['name'],description=f'第{rn+1}轮 / 第{k+1}档<BR>共{d["count"]}个球员包，售价{d["price"]:,}点券。<BR>'+'<BR>'.join(definition(child)['name']+' ×'+str(n) for child,n in d['contents'])+'<BR>每包随机获得1名球员。',bunches=[dict(bunch=1,price=d['price'])],items=[dict(itemid=child,count=n,staticdata=definition(child)) for child,n in d['contents']])
        if d['premium_count']==0:
            featured=definition(d['contents'][0][0])
            out['itemicon']=featured['itemicon'];out['bundleicon']=featured.get('bundleicon',featured['itemicon'])
        return out
    h.item_def=definition
    def chain_entry(st,row):
        root=row.get('shopid')
        if root not in tracks:return row
        row=copy.deepcopy(row);record=st.get('product_chain_rounds',{}).get(str(root),{});versions=record.get('volume_stage_versions',{})
        for part in [row]+row.get('chained',[]):
            i=int(part['product']['itemid'])
            if part.get('currentstep')=='complete' and versions.get(str(i))!='volume110-v1':
                old=copy.deepcopy(host.item_def(i));items=old.get('items',[])
                old['name']=tracks[root]['name']
                for child in items:child['staticdata']=clean_pack_definition(host,int(child['itemid']))
                old['description']='本档已购买。<BR>'+'<BR>'.join(x['staticdata']['name']+' ×'+str(x['count']) for x in items)
                part['product']['staticdata']=old
                continue
            d=definition(i);part['product']['staticdata']=d
        row['chainedproductname']=tracks[root]['name']
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



def market_supply_activate(host, query, body):
    import copy
    import json
    import time
    from market_supply_settings import validate
    request=json.loads(body or b'{}')
    settings=validate(request.get('settings'))
    keys={quality+'_'+str(grade) for quality in ('low','mid','high','elite') for grade in range(11,21)}
    if set(settings['rare_overrides'])!=keys or any(rule['period_seconds']!=300 or rule['slots']!=5 for rule in settings['rare_overrides'].values()):
        raise ValueError('Minute activation requires exactly five independent one-minute slots per five-minute batch in every rare tier')
    engine=host.market_engine
    control=engine.supply_settings
    raw=(json.dumps(settings,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf8')
    target=control.digest(raw)
    with host.STATE_LOCK:
        current=control.get()
        state=host._state()
        if not engine.has_active(state):raise ValueError('No active manager; market activation deferred')
        market=state.get('market_simulation')
        if not market:raise ValueError('Market has not initialized')
        if current['active_revision']==target and market.get('supply_activation_revision')==target:
            return host._json(dict(result=True,replayed=True,revision=target))
        if request.get('revision')!=current['revision']:raise ValueError('Configuration changed; reload before activation')
        old_settings=copy.deepcopy(current['settings'])
        saved=control.set(dict(revision=current['revision'],settings=settings))
        try:
            stamp=time.time()
            legacy=market.setdefault('legacy_supply',[])
            moved=0
            for tier in engine.supply_plan():
                previous=market['rare_books'].get(tier['key'])
                if previous:
                    for row in previous['rows']:
                        archived=copy.deepcopy(row)
                        # Visible quotes and consumed history retain their exact values.
                        # Unquoted future opportunities are cancelled by the new policy.
                        if archived.get('price') is None:archived['count']=0
                        legacy.append(archived)
                        moved+=1
                period=tier['period']
                boundary=int(stamp//period)*period
                # Existing stock is moved above before the existing generator runs.
                # An expired empty batch lets it create this five-minute interval
                # under a new epoch; no classes, worker or global hooks are changed.
                market['rare_books'][tier['key']]=dict(epoch=(previous or {}).get('epoch',0),start=boundary-period,
                    period=period,slots=tier['slots'],chance=tier['chance'],pool_size=tier['pool_size'],rows=[])
            engine.rare_stock(state,stamp)
            market['supply_activation_revision']=saved['active_revision']
            host._save(state)
        except Exception:
            # Save may have committed before returning an I/O error. Its receipt
            # decides whether to retain the new configuration; never replay state.
            committed=host._state().get('market_simulation',{}).get('supply_activation_revision')==saved['active_revision']
            if committed:return host._json(dict(result=True,replayed=False,committed=True,revision=saved['active_revision']))
            control.set(dict(revision=saved['revision'],settings=old_settings))
            raise
        return host._json(dict(result=True,replayed=False,revision=saved['active_revision'],check_seconds=60,
            batch_seconds=300,preserved_rows=moved,policy='one independent opportunity per minute and tier; no weekly wait'))

def clean_pack_definition(host,itemid):
    import copy,re
    out=copy.deepcopy(host.item_def(itemid))
    if itemid not in host.PACKS:return out
    raw=out['name'];top=re.search(r'TOP\s*(\d+)',raw,re.I)
    if '传奇时刻' in raw:family='传奇时刻'
    elif 'ICON' in raw:family='ICON'
    elif '怀旧神兽' in raw or '经典8赛季' in raw:family='经典赛季混合'
    elif '纯传奇' in raw or '经典传奇' in raw:family='传奇混合'
    elif '精选球星' in raw:family='巨星混合'
    else:family=raw.replace('臻选新期·','').replace('·抽卡版','').replace('·印记','').split('·')[0]
    grades=[g for g,w in host.pack_grades(itemid) if w>0]
    strength=str(grades[0])+'强' if len(grades)==1 else str(min(grades))+'~'+str(max(grades))+'强'
    kind='指定球员包' if out.get('category')=='DRAFTPACK' else '球员包'
    name=family+('BEST'+top[1] if top else '')+kind+'（'+strength+'）'
    out['name']=name
    description=out.get('description','').replace(raw,name)
    out['description']=description.replace('臻选新期·','').replace('·抽卡版','').replace('·印记','').replace('怀旧神兽','经典赛季').replace('经典8赛季','经典赛季')
    return out
