"""Local transaction and lifecycle adapters for upstream 9104fab social features.
Never replaces market supply, valuation, enhancement fees or the atomic state store.
"""
import copy
import functools
import hashlib
import hmac
import json
import math
import os
import threading
import types
import contextvars


def install_base(h):
    quote_secret=os.urandom(32)
    def social_timer(interval, function, args=None, kwargs=None):
        if function is h.messenger_push:
            owner=h.my_coach(h._state())['_id']
            original=function
            def checked_push(*values,**options):
                with h.STATE_LOCK:
                    st=h._state()
                    if h.my_coach(st)['_id']!=owner:return
                    uri=values[0]
                    if uri.startswith('/match/'):
                        mid=uri.split('/')[2]
                        if (st.get('ladder_pending') or {}).get('id')!=mid:return
                    return original(*values,**options)
            function=checked_push
        timer=threading.Timer(interval,function,args=args,kwargs=kwargs)
        timer.daemon=True
        return timer
    h.social_timer=social_timer
    # Request helpers stage a detached state, preserving the single atomic save and
    # preventing an exception/failed save from leaking uncommitted cache mutations.
    def transaction(name,validate=None):
        original=getattr(h,name)
        @functools.wraps(original)
        def wrapped(*args):
            with h.STATE_LOCK:
                state=copy.deepcopy(h._state())
                if validate is not None and not validate(state,args):
                    return h._json({'result':False,'reason':'INVALID_PARAM'})
                ns=dict(original.__globals__)
                ns['_state']=lambda:state
                result=types.FunctionType(original.__code__,ns,original.__name__,original.__defaults__,original.__closure__)(*args)
                return result
        setattr(h,name,wrapped)
        h.ROUTES=[(p,wrapped if fn is original else fn) for p,fn in h.ROUTES]
        for path,fn in list(h.ENDPOINTS.items()):
            if fn is original:h.ENDPOINTS[path]=wrapped
    def active_room(st,args):
        room=st.get('room') or {}
        return room.get('owner')==h.my_coach(st)['_id']
    def new_room(st,args):
        req=json.loads(args[-1] or b'{}')
        if req.get('type','pvp_ladder_mgr') not in ('pvp_ladder','pvp_ladder_1v1','pvp_ladder_mgr'):
            return False
        return (st.get('match') or {}).get('stage') not in ('created','squad','setting','playing')
    for name in ('ep_room','ep_matchmaking','ep_room_back','ep_achievement_reward','ep_badge_use','ep_coach_profile','ep_hiderank','ep_tv_history'):
        transaction(name,new_room if name=='ep_room' else active_room if name in ('ep_matchmaking','ep_room_back') else None)
    # A GET must not add ladder/mission defaults to the engine's cached asset snapshot.
    for name in ('ep_ladder_my_info','ep_ladder_leaderboard','ep_ladder_friends','ep_rank_friends','ep_contact_list','ep_vm_summary','ep_vm_ladder_info','ep_vm_coach','ep_achievement_me'):
        transaction(name)
    # Match settings cannot mutate an already-playing or another manager's match.
    def settings_ok(st,args):
        mid=args[0];match=st.get('match') or {}
        mine=str(h.my_coach(st)['_id'])
        users={str(p.get('id')) for s in match.get('side',{}).values() for p in s.get('players',[])}
        return match.get('id')==mid and match.get('stage') in ('created','squad','setting') and mine in users
    transaction('ep_match_gamesettings',settings_ok)
    # Native GPSHOP has no request nonce. Its signed numeric shop id binds the manager,
    # mission week, GP balance and spend sequence, giving one quote one commit. Values
    # stay within the client's signed int32; old replies replay without another debit.
    def gp_quote(st,item):
        m=h.missions_state(st)
        material=f'{h.my_coach(st)["_id"]}:{m["week"]}:{m["gp"]}:{m.get("spend_sequence",0)}:{item}'
        return 1500000000+int.from_bytes(hmac.new(quote_secret,material.encode(),hashlib.sha256).digest()[:8],'big')%500000000
    def gp_shop_list():
        st=copy.deepcopy(h._state());out=[]
        for item,cost in h.GP_SHOP:
            e=h.shop_entry(item,'GPSHOP',gp_quote(st,item))
            e['visible']=True
            e['product']['staticdata']['bunches']=[{'bunch':1,'price':cost}]
            out.append(e)
        return out
    h.gp_shop_list=gp_shop_list
    # GP buys are a separate mission-only transaction; ordinary currency paths stay intact.
    native_buy=h.ep_shop_purchase
    def shop_purchase(query,body):
        req=json.loads(body or b'{}');sid=req.get('shopid')
        if type(sid) is not int or not 1500000000<=sid<2000000000:
            return native_buy(query,body)
        with h.STATE_LOCK:
            st=copy.deepcopy(h._state());coach=h.my_coach(st)
            if not h.missions_cfg()['enabled']:return h._json({'result':False,'reason':'NOT_EXIST_PRODUCT'})
            m=h.missions_state(st);ledger=m.setdefault('shop_receipts',{})
            key=str(sid)
            if key in ledger:return h._json(copy.deepcopy(ledger[key]))
            choices=[(i,c) for i,c in h.GP_SHOP if gp_quote(st,i)==sid]
            if len(choices)!=1:return h._json({'result':False,'reason':'INVALID_PARAM'})
            item,cost=choices[0]
            if req.get('productid') not in (None,0,item):return h._json({'result':False,'reason':'NOT_EXIST_PRODUCT'})
            if m['gp']<cost:return h._json({'result':False,'reason':'NOT_ENOUGH_GP'})
            if 'expectedgp' in req and req['expectedgp']!=m['gp']:return h._json({'result':False,'reason':'INVALID_PARAM'})
            h.inventory_add(coach,item,1);m['gp']-=cost;m['spend_sequence']=m.get('spend_sequence',0)+1
            result={'result':True,'resources':h.coach_me_resources(st,h._default_slot(st))}
            ledger[key]=copy.deepcopy(result)
            while len(ledger)>128:ledger.pop(next(iter(ledger)))
            h._save(st)
            return h._json(result)
    h.ep_shop_purchase=shop_purchase
    h.ENDPOINTS['/shop/purchase']=shop_purchase
    h._social_gp_purchase=shop_purchase


def install_final(h):
    # Registration runs once at startup, after the existing idempotent reward guard.
    # Enhancement hooks are deliberately not reinstalled or altered.
    original=h.coach_me
    @functools.wraps(original)
    def coach_me(st,slot):
        return original(copy.deepcopy(st),slot)
    h.coach_me=coach_me
    native=h.ENDPOINTS['/shop/purchase']
    gp=h._social_gp_purchase
    def purchase(query,body):
        req=json.loads(body or b'{}');sid=req.get('shopid')
        if type(sid) is int and 1500000000<=sid<2000000000:
            return gp(query,body)
        return native(query,body)
    h.ENDPOINTS['/shop/purchase']=purchase
    h.ep_shop_purchase=purchase
    # Attribute upgrade activity to the existing successful commit, without changing
    # its charge, random outcome, protection, material or restore semantics.
    attempt=contextvars.ContextVar('mission_upgrade_attempt',default=None)
    persisted=h._save
    def save(st):
        context=attempt.get()
        if context is not None and not context['counted']:
            h.mission_event(st,upgrade=1)
        pending=int(h.PLAYTIME['pending'])
        if pending>0 and st.get('coaches'):
            coach=h.my_coach(st);coach['playtime']=coach.get('playtime',0)+pending
        result=persisted(st)
        if context is not None:context['counted']=True
        h.PLAYTIME['pending']=max(0,h.PLAYTIME['pending']-pending)
        return result
    h._save=save
    def with_attempt(fn):
        @functools.wraps(fn)
        def wrapped(*args):
            marker=attempt.set({'counted':False})
            try:return fn(*args)
            finally:attempt.reset(marker)
        return wrapped
    mapped={}
    for pattern,fn in h.ROUTES:
        if 'enhance' in pattern.pattern and not any(word in pattern.pattern for word in ('preview','restore','discard')):
            mapped[fn]=with_attempt(fn)
    h.ROUTES=[(pattern,mapped.get(fn,fn)) for pattern,fn in h.ROUTES]
    # Historical real managers/teams, wallet, roster and reward ledgers are never seeded
    # from virtual managers. The population stays deterministic, generated data only.
    h._upstream_social_revision='9104fab-local-compatible-v1'
