"""Versioned, disclosed pack cadence. All state mutations use the native single commit."""
from collections import Counter
import copy, datetime, functools, hashlib, json, math, os, time
from pathlib import Path

def signature(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def supply_period(group):
    return 'day' if group.endswith('_day') else 'month' if group.endswith('_month') else 'week'

def validate(config,hc):
    if config.get('schema')!=1 or config.get('hash')!=signature({k:v for k,v in config.items() if k!='hash'}):
        raise ValueError('Cadence config signature/schema mismatch')
    if not isinstance(config.get('enabled'),bool):raise ValueError('enabled must be boolean')
    for key,value in config['limits'].items():
        if type(value) is not int or not 1<=value<=1000:raise ValueError('Invalid shared supply')
    existing=set(hc.market_spids())
    if not set(config.get('active_items',[]))<=set(map(int,config['items'])):raise ValueError('Unknown active item')
    for key,data in config['items'].items():
        if int(key)!=data['itemid'] or data['hash']!=signature({k:v for k,v in data.items() if k!='hash'}):raise ValueError('Frozen item changed')
        if type(data['price']) is not int or not 0<=data['price']<=10**9:raise ValueError('Invalid price')
        if not 1<=len(data['grades'])<=hc.MAX_GRADE or any(type(w) not in (float,int) or not math.isfinite(w) or w<0 for w in data['grades']) or sum(data['grades'])<=0:raise ValueError('Invalid grade probabilities')
        if not math.isclose(sum(t['chance'] for t in data['tiers']),1,abs_tol=1e-9):raise ValueError('Tier probabilities must total one')
        for tier in data['tiers']:
            if not tier['pool']:raise ValueError('Empty released pool')
            seen=set()
            for spid,weight,anchor,ovr,rank in tier['pool']:
                if spid not in existing or spid in seen or not math.isfinite(weight) or weight<=0 or anchor<=0:raise ValueError('Invalid released card')
                seen.add(spid)
        pity=data.get('pity')
        if pity and (pity['tier'] not in {t['name'] for t in data['tiers']} or not 2<=pity['after']<=1000):raise ValueError('Invalid pity rule')
    for key,data in config['legacy'].items():
        if not data['pool'] or not data['grades']:raise ValueError('Missing legacy frozen probability')
        if any(s not in existing or not math.isfinite(w) or w<=0 for s,w in data['pool']):raise ValueError('Invalid legacy frozen pool')
    return config

class Cadence:
    def __init__(self,hc,config):
        self.h=hc;self.config=validate(copy.deepcopy(config),hc)
        self.items={int(k):v for k,v in config['items'].items()};self.legacy={int(k):v for k,v in config['legacy'].items()}
        self.lotteries={int(k):v for k,v in config.get('legacy_lotteries',{}).items()}
        self.chains={int(k):v for k,v in config.get('legacy_chains',{}).items()}
        self.reward_id=int(config['mark_exchange']['itemid']);self.units_cache={}
        self.previous_pool=hc.pack_pool;self.previous_grades=hc.pack_grades

    def periods(self):
        day=datetime.date.fromisoformat(self.h.today_wib())
        return {'day':day.isoformat(),'week':(day-datetime.timedelta(days=day.weekday())).isoformat(),'month':day.replace(day=1).isoformat()}

    def rotation(self):
        day=datetime.date.fromisoformat(self.h.today_wib());epoch=datetime.date.fromisoformat(self.config['rotation_epoch'])
        return max(0,(day-epoch).days//self.config['rotation_days'])%4

    def active(self,itemid):
        if itemid==self.reward_id:return False
        data=self.items.get(itemid)
        return data is None or itemid in self.config['active_items'] and data.get('rotation') in (None,self.rotation())

    def policy(self,itemid,trail=()):
        if itemid in trail:raise ValueError('Recursive product cycle')
        cache_key=(itemid,bool(trail))
        if cache_key in self.units_cache:return self.units_cache[cache_key]
        if itemid in self.items:
            result=(dict(self.items[itemid]['limits']),False)
        elif itemid in self.legacy:
            data=self.legacy[itemid];result=(dict(data['limits']),data['archived'])
        elif itemid in self.h.PACKS:
            # A newly edited admin SKU must be publicly classified/released first.
            result=({},True)
        elif itemid in self.h.PACKAGES or itemid in self.h.MONTHLY:
            if itemid in self.h.PACKAGES:contents=self.h.PACKAGES[itemid][2]
            else:
                data=self.h.MONTHLY[itemid];contents=list(data[3])+[(i,n*data[2]) for i,n in data[4]]
            total=Counter();archived=False
            for child,count in contents:
                if child in (self.h.EP_ITEM,self.h.ES_ITEM):continue
                units,closed=self.policy(child,trail+(itemid,));total.update({g:n*count for g,n in units.items()});archived|=closed
            result=(dict(total),archived or any(n>self.config['limits'][g] for g,n in total.items()))
        elif itemid in self.lotteries and self.config.get('archive_legacy_lotteries',False):result=({},True)
        elif itemid in self.h.ITEMS and self.h.ITEMS[itemid][2] in self.config.get('archive_legacy_misc_types',[]):result=({},True)
        elif itemid in self.h.ITEMS and self.h.ITEMS[itemid][2]=='ITEM_LOTTERY':
            # Reserve the most restrictive possible reward path, never fractional units.
            total={};archived=False
            for _,child in self.h.ITEMS[itemid][3]['prizes']:
                if not isinstance(child,int):continue
                units,closed=self.policy(child,trail+(itemid,));archived|=closed
                for group,count in units.items():total[group]=max(total.get(group,0),count)
            result=(total,archived)
        else:result=({},False)
        if not trail and itemid in self.h.CHAIN_STEPS and self.h.CHAIN_STEPS[itemid][0] in self.chains and self.config.get('legacy_chain_exempt',False):result=({},False)
        self.units_cache[cache_key]=result
        return result

    def price_floor(self,itemid,trail=()):
        if itemid in trail:raise ValueError('Recursive product pricing')
        if not trail and itemid in self.h.CHAIN_STEPS and self.h.CHAIN_STEPS[itemid][0] in self.chains and self.config.get('legacy_chain_exempt',False):return 0
        if itemid in self.items:return self.items[itemid]['price']
        if itemid in self.legacy:return self.legacy[itemid]['price_floor']
        if itemid in (self.h.EP_ITEM,self.h.ES_ITEM):return 0
        if itemid in self.h.PACKAGES:
            return sum(n*self.price_floor(i,trail+(itemid,)) for i,n in self.h.PACKAGES[itemid][2])
        if itemid in self.h.MONTHLY:
            data=self.h.MONTHLY[itemid]
            return sum(n*self.price_floor(i,trail+(itemid,)) for i,n in data[3])+data[2]*sum(n*self.price_floor(i,trail+(itemid,)) for i,n in data[4])
        if itemid in self.h.ITEMS and self.h.ITEMS[itemid][2]=='ITEM_LOTTERY':
            prizes=self.h.ITEMS[itemid][3]['prizes'];weight=sum(w for w,_ in prizes)
            return math.ceil(sum(w*self.price_floor(i,trail+(itemid,)) for w,i in prizes if isinstance(i,int))/weight)
        return 0

    def remaining(self,st,itemid):
        if itemid in self.h.CHAIN_STEPS and self.h.CHAIN_STEPS[itemid][0] in self.chains:
            first,index=self.h.CHAIN_STEPS[itemid]
            return int(index==self.chain_progress(st,first,0))
        units,archived=self.policy(itemid)
        if archived or not self.active(itemid):return 0
        periods=self.periods();supply=st.get('pack_cadence_supply') or {};available=[]
        for group,needed in units.items():
            period=supply_period(group);saved=supply.get(group) or {}
            used=saved.get('used',0) if saved.get('period')==periods[period] else 0
            available.append(max(0,(self.config['limits'][group]-used)//needed))
        return min(available) if available else self.h.NO_LIMIT

    def validate_purchase(self,st,context):
        itemid=context['itemid']
        if self.remaining(st,itemid)<context['bunch']:return 'NOT_EXIST_PRODUCT'
        if itemid in self.h.CHAIN_STEPS and self.h.CHAIN_STEPS[itemid][0] in self.chains:
            context['cadence_chain_before']=self.chain_record(st,self.h.CHAIN_STEPS[itemid][0])
        return None

    def chain_record(self,st,first):
        saved=(st.get('pack_cadence_chains') or {}).get(str(first))
        if saved:return copy.deepcopy(saved)
        candidates=[]
        for coach in st.get('coaches',[]):
            try:done=max(0,min(len(self.chains[first]['steps']),int((coach.get('chain') or {}).get(str(first),0))))
            except (TypeError,ValueError,OverflowError):done=0
            if done:candidates.append((done,int(coach.get('slot',99)),str(coach['_id']),coach.get('appat')))
        if not candidates:return {'owner':None,'done':0}
        done,slot,owner,started=sorted(candidates,key=lambda row:(-row[0],row[1]))[0]
        return {'owner':owner,'owner_appat':started,'done':done,'migrated':True}

    def chain_progress(self,st,first,local_done):
        if first not in self.chains:return local_done
        record=self.chain_record(st,first);coach=self.h.my_coach(st);owner=str(coach['_id'])
        if record.get('owner_deleted') or record['owner'] not in (None,owner) or record.get('owner_appat') is not None and record['owner_appat']!=coach.get('appat'):
            return len(self.chains[first]['steps'])
        return max(record['done'],local_done)

    def preserve_chains(self,st,prior):
        # Derive from the last committed state before a manager can be purged or recreated.
        # This is part of the caller's one save, never a migration save of its own.
        for first in self.chains:
            old=self.chain_record(prior,first);new=self.chain_record(st,first)
            if old['owner'] is not None:
                current=next((c for c in st.get('coaches',[]) if str(c['_id'])==old['owner']),None)
                deleted=old.get('owner_deleted',False) or current is None or old.get('owner_appat') is not None and current.get('appat')!=old['owner_appat']
                new={'owner':old['owner'],'owner_appat':old.get('owner_appat'),'owner_deleted':deleted,
                     'done':max(old['done'],new['done'] if new['owner']==old['owner'] else 0),'migrated':old.get('migrated',False)}
            if new['owner'] is not None:st.setdefault('pack_cadence_chains',{})[str(first)]=new

    def commit_purchase(self,st,context):
        itemid=context['itemid'];units,archived=self.policy(itemid)
        # Recheck under the transaction lock in case another startup hook changed context.
        is_chain=itemid in self.h.CHAIN_STEPS and self.h.CHAIN_STEPS[itemid][0] in self.chains
        if is_chain:
            first,index=self.h.CHAIN_STEPS[itemid];record=context.get('cadence_chain_before')
            if record is None or record['owner'] not in (None,str(self.h.my_coach(st)['_id'])) or record['done']!=index:return 'NOT_EXIST_PRODUCT'
            record.update(owner=str(self.h.my_coach(st)['_id']),owner_appat=self.h.my_coach(st).get('appat'),done=max(record['done'],index+1))
            st.setdefault('pack_cadence_chains',{})[str(first)]=record
        else:
            failure=self.validate_purchase(st,context)
            if failure:return failure
        periods=self.periods();supply=st.setdefault('pack_cadence_supply',{})
        for group,count in units.items():
            period=supply_period(group);saved=supply.get(group)
            if not saved or saved['period']!=periods[period]:saved={'period':periods[period],'used':0};supply[group]=saved
            saved['used']+=count*context['bunch']
        return None

    def ledger(self,coach):
        return coach.setdefault('pack_cadence',{'marks':0,'pity':{},'exchanged':{},'opens':{}})

    def exchange(self,st):
        coach=self.h.my_coach(st);ledger=self.ledger(coach);rule=self.config['mark_exchange'];week=self.periods()['week']
        used=ledger.setdefault('exchanged',{}).get(week,0)
        if ledger['marks']>=rule['cost'] and used<rule['weekly_limit']:
            ledger['marks']-=rule['cost'];ledger['exchanged'][week]=used+1
            # A reward pack goes to inventory even at full roster; never auto-opens or sells.
            self.h.inventory_add(coach,self.reward_id,1)
            ledger['last_exchange']={'week':week,'cost':rule['cost'],'itemid':self.reward_id}
            ledger['exchanged']={week:used+1}
            return True
        return False

    def open(self,item_id,query,body):
        with self.h.STATE_LOCK:
            st=self.h._state();slot=self.h._default_slot(st);coach=self.h.my_coach(st);team=st['teams'][str(slot)]
            item=next((i for i in coach.get('items',[]) if i['_id']==item_id and i['remains']>0),None)
            if item is None or item['itemid'] not in self.items:return None
            if len(team['players'])>=self.h.MAX_PLAYERS:return self.h._json({'result':False,'reason':'Exceed plyer limit'})
            data=self.items[item['itemid']];ledger=self.ledger(coach);pity=data.get('pity');forced=False
            if pity and ledger['pity'].get(pity['key'],0)>=pity['after']-1:
                tier=next(t for t in data['tiers'] if t['name']==pity['tier']);forced=True
            else:tier=self.h.random.choices(data['tiers'],[t['chance'] for t in data['tiers']])[0]
            row=self.h.random.choices(tier['pool'],[r[1] for r in tier['pool']])[0]
            grade=self.h.random.choices(range(1,len(data['grades'])+1),data['grades'])[0]
            card=self.h.add_player(team,row[0],grade)
            card['pack_cadence_origin']={'edition':data['version'],'itemid':data['itemid'],'tier':tier['name'],'issued_at':self.h.w3c(self.h.time.time())}
            if pity:ledger['pity'][pity['key']]=0 if tier['name']==pity['tier'] else ledger['pity'].get(pity['key'],0)+1
            ledger['marks']+=data['marks'];ledger['opens'][str(data['itemid'])]=ledger['opens'].get(str(data['itemid']),0)+1
            item['remains']-=1
            if item['remains']==0:coach['items'].remove(item)
            exchanged=self.exchange(st)
            self.h._save(st)
            return self.h._json({'result':True,'player':{'_id':card['_id'],'spid':card['spid'],'grade':grade,'price':self.h.card_price(card['spid'],grade)},
                    'cadence':{'edition':data['version'],'tier':tier['name'],'pity_triggered':forced,'marks':ledger['marks'],'automatic_exchange':exchanged},
                    'resources':self.h.coach_me_resources(st,slot)})

def install(hc,config=None):
    if getattr(hc,'_pack_cadence_installed',False):return
    path=Path(hc.HERE)/'gamedata/pack_cadence.json'
    if config is None and not path.exists():return
    config=json.loads(path.read_text(encoding='utf-8')) if config is None else config
    if not config.get('enabled',False):return
    if not callable(getattr(hc,'register_shop_purchase_hook',None)):raise RuntimeError('Install single-commit economy purchase hooks first')
    cadence=Cadence(hc,config)
    original_apply=hc.apply_shop;original_item=hc.item_def;original_price=hc.product_price
    original_use=hc.ep_item_use;original_entry=hc.shop_entry;original_list=hc.shop_list;original_daily=hc.daily_login
    original_purchase=hc.ENDPOINTS['/shop/purchase'];original_save=hc._save
    original_limited=hc.ENDPOINTS['/shop/remained/limited'];original_special=hc.ENDPOINTS['/shop/remained/limited/STSHOP']
    def register():
        cadence.units_cache.clear()
        for itemid,data in cadence.legacy.items():hc.PACKS[itemid]=(data['name'],copy.deepcopy(data['definition']))
        for itemid,data in cadence.lotteries.items():hc.ITEMS[itemid]=hc.item_from(data)
        for first,data in cadence.chains.items():
            for key,definition in data['packages'].items():hc.PACKAGES[int(key)]=hc.package_from(definition)
            hc.CHAINED[first]=tuple(data['steps'])
        hc.CHAIN_STEPS={i:(first,k) for first,steps in hc.CHAINED.items() for k,i in enumerate(steps)}
        for itemid,data in cadence.items.items():
            maximum=max(i for i,w in enumerate(data['grades'],1) if w>0)
            hc.PACKS[itemid]=(data['name'],{'icon':2000006,'all':True,'grade':maximum})
        hc.SHOP_NEW=tuple(i for i in cadence.items if i!=cadence.reward_id)+tuple(i for i in hc.SHOP_NEW if i not in cadence.items)
    @functools.wraps(original_apply)
    def apply_shop(cfg=None):
        result=original_apply(cfg);register();return result
    def pack_pool(itemid):
        if itemid in cadence.legacy:return [tuple(row) for row in cadence.legacy[itemid]['pool']]
        if itemid not in cadence.items:return cadence.previous_pool(itemid)
        combined=Counter()
        for tier in cadence.items[itemid]['tiers']:
            total=sum(r[1] for r in tier['pool'])
            for spid,weight,*_ in tier['pool']:combined[spid]+=tier['chance']*weight/total
        return list(combined.items())
    def pack_grades(itemid):
        if itemid in cadence.legacy:return [tuple(row) for row in cadence.legacy[itemid]['grades']]
        return list(enumerate(cadence.items[itemid]['grades'],1)) if itemid in cadence.items else cadence.previous_grades(itemid)
    def price(itemid,n,value=lambda:0):
        if itemid in hc.CHAIN_STEPS and hc.CHAIN_STEPS[itemid][0] in cadence.chains:
            first=hc.CHAIN_STEPS[itemid][0]
            return cadence.chains[first]['prices'][str(itemid)]*n
        if itemid in cadence.items:return max(1,math.ceil(cadence.items[itemid]['price']*n*(.95 if n>1 else 1)))
        floor=cadence.price_floor(itemid)
        return max(original_price(itemid,n,value),math.ceil(floor*n*(.95 if n>1 else 1)))
    @functools.wraps(original_item)
    def item_def(itemid):
        out=original_item(itemid);units,archived=cadence.policy(itemid)
        if itemid in cadence.items:
            data=cadence.items[itemid];prob=', '.join(f'+{i}={w/sum(data["grades"])*100:g}%' for i,w in enumerate(data['grades'],1) if w)
            out['description']=f'发行版{data["version"]}。强化：{prob}。每包{data["marks"]}印记；满500自动兑换奖励包，每周最多1次，余量保留。'
        if units or archived:
            out['bunches']=[b for b in out['bunches'] if b['bunch']==1]
            out['description']=out.get('description','')+(' 旧版停售，已持有仍按原概率开启。' if archived else ' 共享供应：'+','.join(f'{g}×{n}' for g,n in units.items()))
        return out
    @functools.wraps(original_entry)
    def entry(itemid,category='PLAYERPACK',shopid=None):
        out=original_entry(itemid,category,shopid);units,archived=cadence.policy(itemid)
        if units or archived or itemid in cadence.items:
            left=cadence.remaining(hc._state(),itemid)
            out.update(buy=left>0,forceenable=False,remainedperaccount=left,remained=left,visible=not archived and cadence.active(itemid))
            if units:out['limitcountperaccount']=min(cadence.config['limits'][g]//n for g,n in units.items())
        return out
    @functools.wraps(original_list)
    def listing(st):
        return [e for e in original_list(st) if cadence.active(int(e['product']['itemid'])) and not cadence.policy(int(e['product']['itemid']))[1]]
    @functools.wraps(original_use)
    def use(item_id,query,body):
        result=cadence.open(item_id,query,body)
        return original_use(item_id,query,body) if result is None else result
    @functools.wraps(original_daily)
    def daily(st,now=None):
        result=original_daily(st,now);cadence.exchange(st);return result
    def save(st):
        with hc.STATE_LOCK:
            cadence.preserve_chains(st,hc._state())
            return original_save(st)
    def extra_limited(st,special=False):
        rows=[]
        ids=set(cadence.items)|set(cadence.legacy)|set(hc.PACKAGES)|set(hc.ITEMS)|set(hc.MONTHLY)
        for i in sorted(ids):
            units,archived=cadence.policy(i)
            if not(units or archived or i in cadence.items):continue
            left=cadence.remaining(st,i)
            if special:
                if i in hc.SPECIAL:rows.append({'shopid':hc.STSHOPID+i,'remained':left})
            else:
                rows.append({'shopid':i,'remained':left,'remainedperaccount':left,'buy':left>0})
                if i in hc.MP_SHOP:rows.append({'shopid':hc.MP_SHOPID+i,'remained':left,'remainedperaccount':left,'buy':left>0})
        return rows
    def limited(q,b,special=False):
        with hc.STATE_LOCK:
            previous=original_special if special else original_limited
            rows=json.loads(previous(q,b)[1]);rows+=extra_limited(hc._state(),special)
            return hc._json(rows)
    @functools.wraps(original_purchase)
    def purchase(q,b):
        with hc.STATE_LOCK:
            result=original_purchase(q,b);out=json.loads(result[1])
            if out.get('result'):
                resources=[r for r in out.get('resources',[]) if r.get('uri')!='/shop/remained/limited']
                resources.append({'uri':'/shop/remained/limited','body':json.loads(limited('',b'')[1])})
                out['resources']=resources
                return hc._json(out)
            return result
    hc.apply_shop=apply_shop;hc.pack_pool=pack_pool;hc.pack_grades=pack_grades;hc.product_price=price
    hc.item_def=item_def;hc.shop_entry=entry;hc.shop_list=listing;hc.ep_item_use=use;hc.daily_login=daily
    hc.ep_shop_purchase=purchase;hc.ENDPOINTS['/shop/purchase']=purchase
    hc.chain_account_progress=cadence.chain_progress;hc._save=save
    hc.ENDPOINTS['/shop/remained/limited']=limited
    hc.ENDPOINTS['/shop/remained/limited/STSHOP']=lambda q,b:limited(q,b,True)
    hc.ROUTES[:]=[(pattern,use if fn is original_use else fn) for pattern,fn in hc.ROUTES]
    hc.register_shop_purchase_hook('validate',cadence.validate_purchase)
    hc.register_shop_purchase_hook('before_commit',cadence.commit_purchase)
    register();hc.pack_cadence=cadence;hc._pack_cadence_installed=True
    import admin
    for lang in admin.I18N:
        admin.I18N[lang]['e_cadence_frozen']='Released pack odds/price are frozen. Publish a new edition with new item IDs.'
        admin.I18N[lang]['e_cadence_config']='Invalid or incompatible cadence release.'
    admin.I18N['zh'].update(e_cadence_frozen='已发行卡包的概率与价格已冻结，请用新商品ID发布新版本。',e_cadence_config='发行配置无效或不兼容。')
    def status(params):
        st=hc._state();c=hc.my_coach(st)
        info=copy.deepcopy(cadence.config) if params.get('full') else {k:cadence.config[k] for k in ('edition','hash','budget_daily','limits','rotation_epoch','rotation_days','active_items','disclosure')}
        return {'config':info,'progress':copy.deepcopy(c.get('pack_cadence',{})),
                'remaining':{str(i):cadence.remaining(st,i) for i in set(cadence.items)|set(cadence.legacy)},
                'automatic_exchange':cadence.config['mark_exchange'],'capacity':hc.MAX_PLAYERS}
    admin.API['pack_cadence']=status;admin.READ_ONLY.add('pack_cadence')
    def odds(params):
        try:itemid=int(params['itemid'])
        except (ValueError,TypeError,KeyError):raise admin.AdminError('e_product_missing')
        if itemid in cadence.items:return copy.deepcopy(cadence.items[itemid])
        if itemid in cadence.legacy:return copy.deepcopy(cadence.legacy[itemid])
        raise admin.AdminError('e_product_missing')
    admin.API['pack_cadence_odds']=odds;admin.READ_ONLY.add('pack_cadence_odds')
    previous_lists=admin.API.get('shop_lists')
    if previous_lists:
        def protect_lists(params):
            incoming=(params.get('lists') or {}).get('chained')
            if incoming is not None:
                proposed={int(row[0]):list(map(int,row)) for row in incoming if row}
                frozen_steps={i for data in cadence.chains.values() for i in data['steps']}
                if any(proposed.get(first)!=data['steps'] for first,data in cadence.chains.items()):raise admin.AdminError('e_cadence_frozen')
                if any(first not in cadence.chains and frozen_steps.intersection(steps) for first,steps in proposed.items()):raise admin.AdminError('e_cadence_frozen')
            return previous_lists(params)
        admin.API['shop_lists']=protect_lists
    def publish(params):
        try:
            candidate=validate(copy.deepcopy(params['config']),hc)
            if not candidate['enabled']:raise ValueError('Disabling a deployed edition requires maintenance/restart')
            for key,data in cadence.config['items'].items():
                if candidate['items'].get(key)!=data:raise ValueError('Released inventory definition cannot change')
            for key,data in cadence.config['legacy'].items():
                updated=candidate['legacy'].get(key)
                if updated is None or any(updated.get(field)!=data[field] for field in ('name','definition','pool','grades')):
                    raise ValueError('Legacy issued probabilities cannot change')
            if candidate.get('legacy_lotteries')!=cadence.config.get('legacy_lotteries'):raise ValueError('Legacy lottery contents cannot change')
            if candidate.get('legacy_chains')!=cadence.config.get('legacy_chains') or candidate.get('legacy_chain_exempt')!=cadence.config.get('legacy_chain_exempt'):
                raise ValueError('Existing once-only chain commitment cannot change')
            for key in ('mark_exchange','rotation_epoch','rotation_days'):
                if candidate[key]!=cadence.config[key]:raise ValueError('Previously disclosed progress contract cannot change')
            for key in set(candidate['items'])-set(cadence.config['items']):
                if int(key) in hc.PACKS or int(key) in hc.ITEMS or int(key) in hc.PACKAGES or int(key) in hc.MONTHLY:
                    raise ValueError('New release ID collides with an existing product')
        except (KeyError,ValueError,TypeError,OverflowError):raise admin.AdminError('e_cadence_config')
        if candidate==cadence.config:return {'edition':candidate['edition'],'hash':candidate['hash'],'already_published':True}
        old=copy.deepcopy(cadence.config);old_bytes=path.read_bytes() if path.exists() else None
        next_file=path.with_name(path.name+'.cadence-next')
        if next_file.exists():raise admin.AdminError('e_cadence_config')
        if old_bytes is not None:path.with_name(path.name+'.before-'+str(time.time_ns())).write_bytes(old_bytes)
        try:
            with next_file.open('wb') as file:
                file.write(json.dumps(candidate,ensure_ascii=False,indent=2).encode());file.flush();os.fsync(file.fileno())
            os.replace(next_file,path)
            cadence.config=candidate;cadence.items={int(k):v for k,v in candidate['items'].items()};cadence.legacy={int(k):v for k,v in candidate['legacy'].items()}
            hc.apply_shop()
        except Exception:
            cadence.config=old;cadence.items={int(k):v for k,v in old['items'].items()};cadence.legacy={int(k):v for k,v in old['legacy'].items()}
            if old_bytes is not None:next_file.write_bytes(old_bytes);os.replace(next_file,path)
            elif path.exists():path.unlink()
            hc.apply_shop();raise
        finally:
            if next_file.exists():next_file.unlink()
        return {'edition':candidate['edition'],'hash':candidate['hash'],'active_items':candidate['active_items']}
    admin.API['pack_cadence_publish']=publish
    for action in ('shop_save','shop_delete','shop_restore','shop_price'):
        previous=admin.API.get(action)
        if previous is None:continue
        def protect(params,previous=previous,action=action):
            try:itemid=int(params.get('itemid',0))
            except (TypeError,ValueError):itemid=0
            if itemid in cadence.items or action!='shop_price' and (itemid in cadence.legacy or itemid in cadence.lotteries):raise admin.AdminError('e_cadence_frozen')
            if itemid in hc.CHAIN_STEPS and hc.CHAIN_STEPS[itemid][0] in cadence.chains:raise admin.AdminError('e_cadence_frozen')
            if action=='shop_price' and itemid in cadence.legacy and params.get('price') is not None:
                minimum=cadence.price_floor(itemid)
                if int(params['price'])<minimum:raise admin.AdminError('e_range',('th_shop_price',),minimum,10**9)
            return previous(params)
        admin.API[action]=protect
