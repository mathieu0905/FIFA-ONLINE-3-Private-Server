"""Independent product allowances, ten-round chains and frozen high-variance packs."""
import copy, contextvars, datetime, functools, hashlib, hmac, json, random
from pathlib import Path

def signature(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def install(h):
    if getattr(h,'_product_packs_installed',False):return
    cfg=json.loads((Path(h.HERE)/'gamedata/product_packs.json').read_text(encoding='utf8'))
    if cfg['hash']!=signature({k:v for k,v in cfg.items() if k!='hash'}):raise ValueError('Invalid product rules signature')
    risks={int(k):v for k,v in {**cfg['risk_packs'],**cfg.get('strength_packs',{})}.items()}
    retired=set(map(int,cfg.get('retired_sale_items',[])))
    bundles={int(k):v for k,v in cfg['bundles'].items()}
    tracks={int(k):v for k,v in cfg['chains'].items()}
    stages={int(i):(root,round_index,index) for root,t in tracks.items() for round_index,steps in enumerate(t['round_steps']) for index,i in enumerate(steps)}
    rules={int(k):v for k,v in cfg['limits'].items()}
    if not set(map(int,h.pack_catalogue['items']))<=set(rules):raise ValueError('Independent limits must cover every issued catalogue item')
    previous_item,previous_entry,previous_list,previous_apply=h.item_def,h.shop_entry,h.shop_list,h.apply_shop
    previous_pool,previous_grades,previous_price=h.pack_pool,h.pack_grades,h.product_price
    prior_policy,prior_remaining=h.pack_cadence.policy,h.pack_cadence.remaining
    prior_use,prior_inventory,prior_move=h.ep_item_use,h.coach_items,h.stack_move
    prior_purchase=h.ENDPOINTS['/shop/purchase'];prior_chained=h.chained_entry
    prior_state=h._state;listing_snapshot=contextvars.ContextVar('product_listing_snapshot',default=None)
    def read_state():
        snapshot=listing_snapshot.get()
        return snapshot if snapshot is not None else prior_state()
    market=set(h.market_spids())
    for i,d in risks.items():
        if i in h.PACKS or i in h.ITEMS or any(not t['pool'] or not set(t['pool'])<=market for t in d['tiers']):raise ValueError('Invalid risk pack')
        if sum(t['weight'] for t in d['tiers'])<=0 or sum(d['grades'])<=0 or len(d['grades'])>h.MAX_GRADE:raise ValueError('Invalid risk probabilities')

    def register():
        for i,d in risks.items():h.PACKS[i]=(d['name'],{'all':True,'grade':len(d['grades']),'icon':'2000006'})
        for i,d in bundles.items():h.PACKAGES[i]=(d['name'],'2000006',[tuple(x) for x in d['contents']],d['description'])
        for root,t in tracks.items():
            for i,d in t['packages'].items():h.PACKAGES[int(i)]=(d['name'],'2000006',[tuple(x) for x in d['contents']],d['description'])
            h.CHAINED[root]=tuple(t['steps'])
        h.CHAIN_STEPS={i:(root,k) for root,steps in h.CHAINED.items() for k,i in enumerate(steps)}
        h.CHAIN_STEPS.update({i:(root,index) for i,(root,round_index,index) in stages.items()})
        h.SHOP_NEW=tuple(risks)+tuple(bundles)+tuple(i for i in h.SHOP_NEW if i not in risks and i not in bundles)
        h.pack_cadence.units_cache.clear()

    def period(rule):
        day=datetime.date.fromisoformat(h.today_wib())
        if rule['period']=='week':day-=datetime.timedelta(days=day.weekday())
        elif rule['period']=='month':day=day.replace(day=1)
        return day.isoformat()
    def count_record(st,i):
        rule=rules[i];record=(st.get('product_purchase_counts') or {}).get(str(i)) or {}
        used=record.get('used',0) if record.get('period')==period(rule) else 0
        return used,period(rule)
    def chain_record(st,root):return (st.get('product_chain_rounds') or {}).get(str(root)) or {'rounds':0,'stage':0,'owner':None,'owner_appat':None}
    def chain_available(st,i):
        root,round_index,index=stages[i];t=tracks[root];r=chain_record(st,root);coach=h.my_coach(st)
        return int(r['rounds']<t['rounds'] and r['rounds']==round_index and r['stage']==index and
                   (r['owner'] is None or (r['owner']==str(coach['_id']) and r['owner_appat']==coach.get('appat'))))
    def remaining(st,i):
        if i in retired:return 0
        if i in stages:return chain_available(st,i)
        if i in rules:return max(0,rules[i]['count']-count_record(st,i)[0]) if h.pack_cadence.active(i) else 0
        return prior_remaining(st,i)
    def policy(i,trail=()):
        if i in retired:return {},True
        if i in stages:return ({},bool(trail))
        if i in rules:return {},False
        return prior_policy(i,trail)
    def quota_text(i):
        r=rules[i];label={'day':'每天','week':'每周','month':'每月'}[r['period']]
        return f'本商品独立限购：{label}{r["count"]}份；其它卡包、礼包不占本商品次数。'
    def clean(text):
        return '<BR>'.join(x for x in str(text).split('<BR>') if not any(s in x for s in ('共享供应','全账号每日共享','全账号每周共享','单赛季随机包全账号','纯传奇随机包全账号','所有自选包全账号')))
    def definition(i):
        out=previous_item(i)
        if i in risks:
            d=risks[i];choice=d.get('mode')=='choice'
            out={**out,'name':d['name'],'category':'DRAFTPACK' if choice else 'PLAYERPACK','type':'CUSTOM','itemicon':'2000006','bundleicon':'2000006','description':d['description']}
            if choice:out['draft']={'season':d['tiers'][0]['pool'][0]//1000000,'grade':next(g for g,w in enumerate(d['grades'],1) if w),'availables':1}
        elif i in bundles:out={**out,'description':bundles[i]['description']+'<BR>'+out.get('description','')}
        elif i in stages:
            root,_,_=stages[i];d=tracks[root]['packages'][str(i)]
            out={**out,'description':d['description']+'<BR>'+'<BR>'.join(h.item_def(child)['name']+' ×'+str(count) for child,count in d['contents'])}
        elif i in h.PACKS and h.PACKS[i][1].get('probability_mode'):
            from pack_probability import grades as probability_grades
            rows=probability_grades(h.PACKS[i][1])
            curve='、'.join(f'+{grade}：{weight:g}%' for grade,weight in rows)
            out={**out,'description':out.get('description','')+'<BR>'+f'强化范围+{rows[0][0]}～+{rows[-1][0]}。<BR>强化概率：{curve}。'}
        if i in retired:
            out={**out,'description':'旧版+1卡包已停售；背包中已持有的仍按原规则开启。<BR>'+clean(out.get('description',''))}
        elif i in rules:
            out={**out,'description':clean(out.get('description',''))+'<BR>'+quota_text(i)}
            # Native quantity menu: buying ten is one request but consumes ten item allowances.
            quantities=(1,10) if rules[i]['count']>=10 and i in h.PACKS else (1,)
            out['bunches']=[{'bunch':n,'price':price(i,n)} for n in quantities]
        return out
    def pool(i):
        if i not in risks:return previous_pool(i)
        d=risks[i];total=sum(t['weight'] for t in d['tiers']);weights={}
        for t in d['tiers']:
            for s in t['pool']:weights[s]=weights.get(s,0)+t['weight']/total/len(t['pool'])
        return list(weights.items())
    def grades(i):return list(enumerate(risks[i]['grades'],1)) if i in risks else previous_grades(i)
    def price(i,n,value=lambda:0):
        if i in risks:return risks[i]['price']*n
        if i in bundles:return bundles[i]['price']*n
        if i in stages:
            root,_,_=stages[i];return tracks[root]['prices'][str(i)]*n
        return previous_price(i,n,value)
    def entry(i,category='PLAYERPACK',shopid=None):
        out=previous_entry(i,category,shopid)
        if i in rules:
            left=remaining(h._state(),i);cap=rules[i]['count']
            out.update(visible=i not in retired,forceenable=False,buy=left>0,remained=left,remainedperaccount=left,limittotalcount=cap,limitcountperaccount=cap)
        return out
    def validate(st,context):
        i=context['itemid']
        if i in rules and context['bunch']>remaining(st,i):return '本商品本期限购次数不足，请选择其它商品或等待本商品刷新。'
    def commit(st,context):
        i=context['itemid']
        if i in rules:
            failure=validate(st,context)
            if failure:return failure
            used,p=count_record(st,i)
            st.setdefault('product_purchase_counts',{})[str(i)]={'period':p,'used':used+context['bunch'],'rule_version':cfg['edition']}
    def apply_shop(config=None):
        result=previous_apply(config);register();return result

    def chained_entry(st,root):
        if root not in tracks:return prior_chained(st,root)
        t=tracks[root];r=chain_record(st,root);done=r['stage'];complete=r['rounds']>=t['rounds'];parts=[]
        current=t['round_steps'][min(r['rounds'],t['rounds']-1)]
        for index,i in enumerate(current):
            part=h.shop_entry(i,'CHAINED');part.update(index=index+1,maxCount=len(t['steps']),limitcountperaccount=1,
                remainedperaccount=int(not complete and index>=done),remained=int(not complete and index>=done),
                buy=bool(not complete and index==done and chain_available(st,i)),
                currentstep='complete' if complete or index<done else 'activity' if index==done else 'default')
            parts.append(part)
        can_buy=not complete and bool(chain_available(st,current[done]))
        return dict(parts[0],shopid=root,_id=str(root),step=min(done,len(parts)-1),chained=parts[1:],
            chainedproductname=t['name']+f'（第{min(r["rounds"]+1,t["rounds"])}/{t["rounds"]}轮）',
            buy=can_buy,remained=int(can_buy),remainedperaccount=int(can_buy))
    def listing(st):
        marker=listing_snapshot.set(st)
        try:
            rows=previous_list(st)
            rows=[r for r in rows if r.get('shopid') not in tracks]
            return [chained_entry(st,root) for root in tracks]+rows
        finally:listing_snapshot.reset(marker)
    def purchase(q,b):
        try:
            req=json.loads(b or b'{}');i=int(req.get('productid') or 0)
            if not i:i=int(req.get('shopid') or 0)
        except (TypeError,ValueError,AttributeError):return prior_purchase(q,b)
        if i not in stages:
            result=prior_purchase(q,b);out=json.loads(result[1])
            if i in rules and out.get('result'):
                st=h._state();updates={'/shop/list':listing(st)}
                out['resources']=[r for r in out.get('resources',[]) if r.get('uri') not in updates]+[{'uri':uri,'body':data} for uri,data in updates.items()]
                out.setdefault('states',{})[str(i)]={'remained':remaining(st,i),'remainedperaccount':remaining(st,i),'buy':remaining(st,i)>0}
                return h._json(out)
            return result
        with h.STATE_LOCK:
            st=h._state();root,round_index,index=stages[i];t=tracks[root];coach=h.my_coach(st)
            if isinstance(req.get('bunch',0),bool) or req.get('bunch',0)!=0 or req.get('shopid',root) not in (root,i) or not chain_available(st,i):return h._json({'result':False,'reason':'请按当前轮次的档位顺序购买，或本连锁已达到10轮。'})
            amount=price(i,1)
            if int(coach.get('cash',0))<amount:
                return h._json({'result':False,'reason':'NOT_ENOUGH_CASH'})
            h.add_cash(st,-amount,'shop:'+str(i))
            for child,count in t['packages'][str(i)]['contents']:h.inventory_add(coach,child,count)
            record=copy.deepcopy(chain_record(st,root));record.update(owner=str(coach['_id']),owner_appat=coach.get('appat'))
            record['stage']=index+1
            if record['stage']==len(t['steps']):record['rounds']+=1;record['stage']=0
            st.setdefault('product_chain_rounds',{})[str(root)]=record
            h._save(st)
            return h._json({'result':True,'currency':'cash','spent':amount,'chain_round':record,
                'states':{str(root):{'step':record['stage'],'buy':record['rounds']<t['rounds'],'remained':int(record['rounds']<t['rounds']),'remainedperaccount':int(record['rounds']<t['rounds'])}},
                'resources':h.coach_me_resources(st,h._default_slot(st))+[{'uri':'/shop/list','body':listing(st)}]})

    def opening_id(coach,item):
        value=f'{coach["_id"]}:{coach.get("appat")}:{item["_id"]}:{item["itemid"]}:{item["remains"]}:{cfg["edition"]}'
        return item['_id']+'_pf_'+hmac.new(bytes.fromhex(cfg['token_key']),value.encode(),hashlib.sha256).hexdigest()[:24]
    def inventory(st,slot,where='items'):
        rows=prior_inventory(st,slot,where);coach=next(c for c in st['coaches'] if c['slot']==slot)
        raw={i['_id']:i for i in coach.get(where,[])}
        for row in rows:
            if row['itemid'] in risks and row['_id'] in raw:row['_id']=row['id']=opening_id(coach,raw[row['_id']])
        return rows
    def move(coach,i,src,dst):
        for item in coach.get(src,[]):
            if item['itemid'] in risks and opening_id(coach,item)==i:return prior_move(coach,item['_id'],src,dst)
        return prior_move(coach,i,src,dst)
    def use(itemid,q,b):
        if '_pf_' not in itemid:return prior_use(itemid,q,b)
        with h.STATE_LOCK:
            st=h._state();coach=h.my_coach(st);receipt=coach.get('risk_pack_receipts',{}).get(itemid)
            try:chosen=json.loads(b or b'{}').get('spids')
            except (ValueError,TypeError,AttributeError):return h._json({'result':False,'reason':'INVALID_PARAM'})
            if receipt:
                if receipt['chosen']!=chosen:return h._json({'result':False,'reason':'INVALID_PARAM'})
                return h._json({'result':True,'player':receipt['player'],'replayed':True,'resources':h.coach_me_resources(st,h._default_slot(st))})
            item=next((x for x in coach.get('items',[]) if x['itemid'] in risks and opening_id(coach,x)==itemid and x['remains']>0),None)
            if item is None:return h._json({'result':False,'reason':'INVALID_ITEM'})
            team=st['teams'][str(h._default_slot(st))]
            if len(team['players'])>=h.MAX_PLAYERS:return h._json({'result':False,'reason':'Exceed plyer limit'})
            d=risks[item['itemid']]
            if d.get('mode')=='choice':
                tier=d['tiers'][0]
                if not isinstance(chosen,list) or len(chosen)!=1 or type(chosen[0]) is not int or chosen[0] not in tier['pool']:return h._json({'result':False,'reason':'INVALID_PARAM'})
                spid=chosen[0]
            else:
                tier=h.random.choices(d['tiers'],[t['weight'] for t in d['tiers']])[0];spid=h.random.choice(tier['pool'])
            grade=h.random.choices(range(1,len(d['grades'])+1),d['grades'])[0]
            card=h.add_player(team,spid,grade);card['product_pack_origin']={'edition':cfg['edition'],'itemid':item['itemid'],'tier':tier['name']}
            player={'_id':card['_id'],'spid':spid,'grade':grade,'price':h.player_value_price(spid,grade)}
            coach.setdefault('risk_pack_receipts',{})[itemid]={'player':player,'chosen':chosen}
            item['remains']-=1
            if item['remains']==0:coach['items'].remove(item)
            h._save(st)
            return h._json({'result':True,'player':player,'resources':h.coach_me_resources(st,h._default_slot(st))})

    register()
    h._state=read_state
    h.pack_pool,h.pack_grades,h.product_price=pool,grades,price
    h.item_def,h.shop_entry,h.shop_list,h.apply_shop=definition,entry,listing,apply_shop
    h.pack_cadence.policy,h.pack_cadence.remaining=policy,remaining
    h.item_purchase_remaining=remaining;h.item_purchase_limit=lambda i:rules[i]
    h._per_product_limits=True
    h.register_shop_purchase_hook('validate',validate);h.register_shop_purchase_hook('before_commit',commit)
    h.chained_entry=chained_entry;h.coach_items,h.stack_move=inventory,move
    old_progress=h.chain_account_progress
    def progress(st,root,local_done):
        if root not in tracks:return old_progress(st,root,local_done)
        record=chain_record(st,root)
        return len(tracks[root]['steps']) if record['rounds']>=tracks[root]['rounds'] else record['stage']
    h.chain_account_progress=progress
    h.ep_item_use=use;h.ROUTES[:]=[(p,use if fn is prior_use else fn) for p,fn in h.ROUTES]
    h.ep_shop_purchase=purchase;h.ENDPOINTS['/shop/purchase']=purchase
    # Preserve old +1 inventory selection, but route new +8 selection to its exact frozen pool.
    old_choices=next(fn for p,fn in h.ROUTES if p.pattern==r'/item/draftpack/(\d+)/players/(\d+)')
    old_search=next(fn for p,fn in h.ROUTES if p.pattern==r'/packchoice/(\d+)/search')
    def candidates(i,query):
        from urllib.parse import parse_qs
        i=int(i);d=risks.get(i)
        if not d or d.get('mode')!='choice':return None
        coach=h.my_coach(h._state())
        if not any(x['itemid']==i and x['remains']>0 for x in coach.get('items',[])):return []
        q=parse_qs(query.lstrip('?'));text=q.get('q',[''])[0].casefold().strip()
        try:league=int(q.get('league',['255'])[0]);team=int(q.get('team',['255'])[0])
        except ValueError:return []
        rows=[]
        for s in d['tiers'][0]['pool']:
            info=d['search'][str(s)]
            if text and text not in info['name'].casefold():continue
            if league not in (255,-1,0) and info['league']!=league:continue
            if team not in (255,-1,0) and info['team']!=team:continue
            rows.append({'spid':s,'grade':8,'price':h.player_value_price(s,8),'expandme':'player'})
        return rows
    def choices(i,count,q,b):
        rows=candidates(i,'')
        return old_choices(i,count,q,b) if rows is None else h._json([] if int(count)==1 else rows)
    def search(i,q,b):
        rows=candidates(i,q)
        return old_search(i,q,b) if rows is None else h._json(rows)
    h.ROUTES[:]=[(p,choices if fn is old_choices else search if fn is old_search else fn) for p,fn in h.ROUTES]
    h.product_packs=cfg;h._product_packs_installed=True
