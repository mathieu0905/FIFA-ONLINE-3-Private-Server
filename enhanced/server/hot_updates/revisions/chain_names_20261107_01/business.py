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
                old['name']=f'第{stages[i][2]+1}档 · {sum(x["count"] for x in items)}包'
                for child in items:child['staticdata']=clean_pack_definition(host,int(child['itemid']))
                old['description']='本档已购买。<BR>'+'<BR>'.join(x['staticdata']['name']+' ×'+str(x['count']) for x in items)
                part['product']['staticdata']=old
                continue
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
    elif '怀旧神兽' in raw:family='经典球星'
    elif '经典8赛季' in raw:family='经典赛季'
    elif '纯传奇' in raw or '经典传奇' in raw:family='传奇'
    elif '精选球星' in raw:family='精选球星'
    else:
        family=raw.replace('臻选新期·','').replace('·抽卡版','').replace('·印记','').split('·')[0]
    grades=[g for g,w in host.pack_grades(itemid) if w>0]
    grade='+'+str(grades[0]) if len(grades)==1 else '+'+str(min(grades))+'～+'+str(max(grades))
    kind='自选球员包' if out.get('category')=='DRAFTPACK' else '球员包'
    name=family+(' TOP'+top[1] if top else '')+kind+'（'+grade+'）'
    out['name']=name
    description=out.get('description','').replace(raw,name)
    out['description']=description.replace('臻选新期·','').replace('·抽卡版','').replace('·印记','').replace('怀旧神兽','经典球星').replace('经典8赛季','经典赛季')
    return out
