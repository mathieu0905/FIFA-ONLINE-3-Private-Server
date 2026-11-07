"""Offline cash-point economy. EP remains transfer-market money; cash buys shop products."""
import functools, math, json, datetime, pathlib

START_CASH=500
DAILY_CASH=10000
MATCH_DAILY_CAP=10000
CASH_MAX=10**9

def install(hc):
    if getattr(hc,'_cash_economy_installed',False):return
    hc._cash_economy_installed=True
    purchase_hooks={event:[] for event in ('validate','before_commit')}
    def register_shop_purchase_hook(event,callback):
        if event not in purchase_hooks:raise ValueError('Unknown purchase hook')
        if not callable(callback):raise TypeError('Purchase callback must be callable')
        if callback not in purchase_hooks[event]:purchase_hooks[event].append(callback)
        def remove():
            if callback in purchase_hooks[event]:purchase_hooks[event].remove(callback)
        return remove
    hc.register_shop_purchase_hook=register_shop_purchase_hook
    def purchase_dispatch(event,st,context):
        for callback in tuple(purchase_hooks[event]):
            failure=callback(st,context)
            if failure:return failure
        return None
    def balance(coach):return max(0,min(CASH_MAX,int(coach.get('cash',START_CASH))))
    def add_cash(st,n,reason='adjustment'):
        coach=hc.my_coach(st);old=balance(coach);new=max(0,min(CASH_MAX,old+int(n)))
        coach['cash']=new
        ledger=coach.setdefault('cash_ledger',[])
        ledger.append({'time':hc.w3c(hc.time.time()),'delta':new-old,'balance':new,'reason':reason})
        del ledger[:-100]
        return new
    hc.cash_balance=balance;hc.add_cash=add_cash
    original_coach=hc.coach_me
    @functools.wraps(original_coach)
    def coach_me(st,slot):
        out=original_coach(st,slot);coach=next(c for c in st['coaches'] if c['slot']==slot)
        out['money']['cash']=balance(coach);return out
    hc.coach_me=coach_me
    original_daily=hc.daily_login
    @functools.wraps(original_daily)
    def daily_login(st,now=None):
        out=original_daily(st,now);coach=hc.my_coach(st);day=hc.today_wib(now)
        if coach.get('cash_daily_day')!=day:
            add_cash(st,DAILY_CASH,'daily');coach['cash_daily_day']=day
        return out
    hc.daily_login=daily_login
    original_reward=hc.match_reward
    @functools.wraps(original_reward)
    def match_reward(st,stats):
        out=original_reward(st,stats);match=st.get('match') or {};mid=match.get('id')
        if not mid or match.get('simulated') or (match.get('gamesettings') or {}).get('simulated'):return out
        coach=hc.my_coach(st);day=hc.today_wib();ledger=coach.setdefault('cash_match_rewards',{})
        if ledger.get('day')!=day:ledger.clear();ledger.update(day=day,earned=0,matches={})
        if str(mid) in ledger['matches']:return out
        mine=stats.get('myTeam','home');opp=stats.get('opponentTeam','away')
        mg=int((stats.get(mine) or {}).get('score') or 0);og=int((stats.get(opp) or {}).get('score') or 0)
        grant=min(1000 if mg>og else 700 if mg==og else 400,max(0,MATCH_DAILY_CAP-int(ledger['earned'])))
        add_cash(st,grant,'match:'+str(mid));ledger['earned']+=grant;ledger['matches'][str(mid)]=grant
        out['cashreward']={'total':grant,'dailycap':MATCH_DAILY_CAP,'earnedtoday':ledger['earned']}
        return out
    hc.match_reward=match_reward

    def default_price(itemid,trail=()):
        if itemid in trail:return 1
        trail=trail+(itemid,)
        fixed=(hc._SHOP.get('prices') or {}).get(str(itemid))
        if fixed is not None and int(fixed)>0:return int(fixed)
        if itemid in hc.PACKS:
            _,f=hc.PACKS[itemid];g=int(f.get('grade',1));seasons=set(f.get('seasons') or ([f['season']] if f.get('season') else []))
            top=int(f.get('top') or 0);ovr=int(f.get('ovr') or 65)
            base=25 if ovr<70 else 40 if ovr<75 else 65 if ovr<80 else 100 if ovr<85 else 250 if ovr<88 else 500
            if top:base=max(base,600 if top<=5 else 350 if top<=30 else 220 if top<=100 else 140)
            if seasons & {91,93}:base=max(base,500)
            scale=1 if g<=1 else 1.25 if g<=3 else 2 if g<=5 else 4 if g<=8 else 8 if g<=10 else 20
            return max(1,round(base*scale))
        if itemid in hc.ITEMS:
            _,_,typ,eff,_=hc.ITEMS[itemid]
            if typ=='PLAYER_EXP_CAPSULE':return max(5,math.ceil(int(eff['exp'])/1000*20))
            if typ=='COACH_EXP_CAPSULE':return max(5,math.ceil(int(eff['exp'])/1000*25))
            if typ=='ITEM_LOTTERY':
                prizes=eff.get('prizes') or []
                value=sum(w*(default_price(p,trail) if isinstance(p,int) else max(1,p[1]/100000)) for w,p in prizes)/max(1,sum(w for w,p in prizes))
                return max(10,math.ceil(value*1.1))
            if typ=='EP_LOTTERY':return max(5,math.ceil((sum(eff['ep'])/2)/100000))
            return {'ENHANCEMENT_BOOST':25,'LEAGUE_SIMULATION':5,'TEAM_CHANGE':30,'COACHNAME_CHANGE':30}.get(typ,25)
        if itemid in hc.PACKAGES:
            contents=hc.PACKAGES[itemid][2]
            return max(1,math.ceil(sum(n*(0.00001 if i==hc.EP_ITEM else 0.02 if i==hc.ES_ITEM else default_price(i,trail)) for i,n in contents)*0.9))
        if itemid in hc.MONTHLY:
            _,_,days,now,daily,_=hc.MONTHLY[itemid]
            value=lambda rows:sum(n*(0.00001 if i==hc.EP_ITEM else 0.02 if i==hc.ES_ITEM else default_price(i,trail)) for i,n in rows)
            return max(1,math.ceil((value(now)+days*value(daily))*0.6))
        return 25
    hc.cash_product_price=default_price
    def product_price(itemid,n,value=lambda:0):
        # Fixed cash amounts are exact; do not sig3-round low point prices.
        return max(1,math.ceil(default_price(itemid)*n*(0.95 if n>1 else 1)))
    hc.product_price=product_price;hc.SHOP_FREE=False
    original_item=hc.item_def
    @functools.wraps(original_item)
    def item_def(itemid):
        out=original_item(itemid)
        if itemid in hc.PACKS or itemid in hc.ITEMS or itemid in hc.PACKAGES or itemid in hc.MONTHLY:
            out=dict(out,currency='cash')
            out['purchasecurrency']='cash'
        def icons(v):
            if isinstance(v,list):return [icons(x) for x in v]
            if not isinstance(v,dict):return v
            v={k:icons(x) for k,x in v.items()}
            for key in ('itemicon','bundleicon'):
                if key in v and not pathlib.Path(hc.ASSETS,'externalAssets','shop',str(v[key])+'.png').is_file():
                    v[key]='2000006'
            return v
        return icons(out)
    hc.item_def=item_def
    original_apply=hc.apply_shop
    @functools.wraps(original_apply)
    def apply_shop(cfg=None):
        out=original_apply(cfg);hc.SHOP_FREE=False
        hc.pack_price.cache_clear()
        return out
    hc.apply_shop=apply_shop

    def ep_shop_purchase(query,body):
        try:
            req=json.loads(body or b'{}');itemid=int(req.get('productid') or 0) or int(req.get('shopid') or 0)%hc.MP_SHOPID%hc.STSHOPID
            index=req.get('bunch',0)
            if isinstance(index,bool) or int(index)!=float(index):raise ValueError()
            index=int(index)
        except (ValueError,TypeError,OverflowError):return hc._json({'result':False,'reason':'INVALID_PARAM'})
        if itemid in hc.SHOP_HIDDEN or not any(itemid in t for t in (hc.PACKS,hc.ITEMS,hc.PACKAGES,hc.MONTHLY)):
            return hc._json({'result':False,'reason':'NOT_EXIST_PRODUCT'})
        bunches=hc.item_def(itemid)['bunches']
        if not 0<=index<len(bunches):return hc._json({'result':False,'reason':'INVALID_PARAM'})
        b=bunches[index];st=hc._state();slot=hc._default_slot(st);coach=hc.my_coach(st)
        purchase_context={'itemid':itemid,'bunch':b['bunch'],'price':b['price'],'request':req}
        failure=purchase_dispatch('validate',st,purchase_context)
        if failure:return hc._json({'result':False,'reason':failure})
        if balance(coach)<b['price']:return hc._json({'result':False,'reason':'NOT_ENOUGH_CASH'})
        add_cash(st,-b['price'],'shop:'+str(itemid))
        contents=hc.PACKAGES[itemid][2] if itemid in hc.PACKAGES else hc.MONTHLY[itemid][3] if itemid in hc.MONTHLY else [(itemid,1)]
        for i,n in contents:
            if i==hc.EP_ITEM:hc.add_ep(st,n*b['bunch'])
            elif i==hc.ES_ITEM:hc.add_es(st,n*b['bunch'])
            else:hc.inventory_add(coach,i,n*b['bunch'])
        if itemid in hc.MONTHLY:
            now=hc.time.time();m=coach.setdefault('monthly',{}).setdefault(str(itemid),{'since':now,'expire':now,'rewarded':0})
            m['expire']=max(m['expire'],now)+hc.MONTHLY[itemid][2]*86400
        if itemid in hc.CHAIN_STEPS:
            first,k=hc.CHAIN_STEPS[itemid];chain=coach.setdefault('chain',{});chain[str(first)]=max(chain.get(str(first),0),k+1)
        failure=purchase_dispatch('before_commit',st,purchase_context)
        if failure:return hc._json({'result':False,'reason':failure})
        hc._save(st)
        return hc._json({'result':True,'currency':'cash','spent':b['price'],'resources':hc.coach_me_resources(st,slot)+([{'uri':'/monthlypack','body':hc.monthly_list(st)}] if itemid in hc.MONTHLY else [])})
    hc.ep_shop_purchase=ep_shop_purchase;hc.ENDPOINTS['/shop/purchase']=ep_shop_purchase
    hc.ENDPOINTS['/shop/remained/cash']=lambda q,b: hc._json({'cash':balance(hc.my_coach(hc._state())), 'resources':hc.coach_me_resources(hc._state(),hc._default_slot(hc._state()))})

    import admin
    original_summary=admin.summary
    def summary(p):
        out=original_summary(p);out['coach']['cash']=balance(admin.coach(hc._state()));out['economy']={'initial':START_CASH,'daily':DAILY_CASH,'match_daily_cap':MATCH_DAILY_CAP};return out
    admin.summary=summary;admin.API['summary']=summary
    def cash(p):
        st=hc._state();coach=hc.my_coach(st)
        if 'set' in p:coach['cash']=admin.as_int(p['set'],0,CASH_MAX,('f_cash',))
        else:add_cash(st,admin.as_int(p.get('add'),-CASH_MAX,CASH_MAX,('f_cash',)))
        hc._save(st);return {'cash':balance(coach)}
    admin.API['cash']=cash
    admin.READ_ONLY.add('cash_history')
    admin.API['cash_history']=lambda p: {'cash':balance(hc.my_coach(hc._state())),'transactions':hc.my_coach(hc._state()).get('cash_ledger',[])}
    hc.ENDPOINTS['/shop/cash/charge/url']=lambda q,b: hc._json({'url':'http://127.0.0.1:8088/'})
    hc.ENDPOINTS['/shop/cash/history/url']=lambda q,b: hc._json({'url':'http://127.0.0.1:8088/api/cash_history'})
    original_shop=admin.shop
    def shop(p):
        out=original_shop(p);out.update(free=False,currency='cash');return out
    admin.shop=shop;admin.API['shop']=shop
    def shop_free(p):
        cfg=hc.shop_config();cfg['free']=False;admin.save_shop(cfg);return {'free':False}
    admin.API['shop_free']=shop_free
    labels={
     'id':('Poin','Semua produk dibeli dengan poin. Saldo EP tidak terpakai.','Harga poin','Poin tetap','Poin'),
     'en':('Cash points','All products cost cash points. EP is separate.','Point price','Fixed points','Cash points'),
     'zh':('点券','所有商城商品使用点券购买，EP仍用于转会市场。','点券价格','固定点券价','点券管理'),
     'th':('แคช','สินค้าทั้งหมดใช้แคช EP แยกต่างหาก','ราคาแคช','แคชคงที่','แคช'),
     'vi':('Điểm','Mọi sản phẩm dùng điểm, EP được giữ riêng.','Giá điểm','Giá điểm cố định','Quản lý điểm'),
     'ko':('캐시','모든 상품은 캐시로 구매합니다. EP는 별도입니다.','캐시 가격','고정 캐시','캐시 관리')}
    for lang,(currency,note,price,fixed,title) in labels.items():
        admin.I18N[lang].update(f_cash=currency,cash_title=title,shop_free_note=note,th_shop_price=price,th_fixed_price=fixed)
    hc.ECONOMY={'currency':'cash','initial':START_CASH,'daily':DAILY_CASH,'match_daily_cap':MATCH_DAILY_CAP}
