"""Single-commit, idempotent league/cup rewards. Install before optional reward extensions.
Uses existing handler code against an isolated globals map to stage its state writes;
no temporary monkeypatch of the server module or shared disk paths is performed.
"""
import copy
import functools
import json
import types
import uuid
import threading

MATCH_RECEIPTS=4
CUP_CLAIMS=64


def install(hc):
    if not isinstance(hc.STATE_LOCK,type(threading.RLock())):
        raise RuntimeError('Initialize STATE_LOCK = threading.RLock() in source before starting server; never replace a live lock')
    if getattr(hc,'_league_reward_guard_installed',False):return
    originals={name:getattr(hc,name) for name in ('ep_l2_calendar','ep_l2_end','ep_cup_leave','ep_match_end','match_step')}
    # Staging the current plain source functions preserves their formulas exactly.
    # A future wrapper that captures an external hc must be installed after this guard.
    for name,fn in originals.items():
        if not isinstance(fn,types.FunctionType) or fn.__closure__ or fn.__globals__ is not hc.__dict__:
            raise RuntimeError('Install league_reward_guard before wrappers of '+name)

    hooks={event:[] for event in ('calendar_before_commit','match_playing','match_before_commit')}

    def register_reward_hook(event,callback):
        if event not in hooks:raise ValueError('Unknown reward event: '+str(event))
        if not callable(callback):raise TypeError('Reward hook must be callable')
        if callback not in hooks[event]:hooks[event].append(callback)
        def remove():
            if callback in hooks[event]:hooks[event].remove(callback)
        return remove

    def dispatch(event,*args):
        # Hooks mutate only this staged state. An exception prevents the sole commit.
        # Registration belongs to process startup; callbacks must never call _save.
        for callback in tuple(hooks[event]):callback(*args)

    def staged(name,st,*args):
        fn=originals[name]
        namespace=dict(fn.__globals__)
        namespace.update(_state=lambda:st,_save=lambda data:None,_json=lambda data:data)
        return types.FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)(*args)

    def owner(st):return hc.my_coach(st)['_id']

    def summary(response):
        # Historical reward descriptions are immutable; live resources are rebuilt.
        return copy.deepcopy({k:v for k,v in response.items() if k!='resources'})

    def live_reply(st,response,mid=None):
        out=summary(response)
        resources=hc.coach_me_resources(st,hc._default_slot(st))
        if mid is not None:
            resources += [{'uri':f'/match/{mid}','body':copy.deepcopy(st['match'])}]
        resources += hc.l2_resources(st)
        out['resources']=resources
        return out

    def league_complete(lg):
        league=lg.get('league') or {}
        teams=league.get('teams') or []
        try:
            maximum=int(league['maxround']);next_round=int(league['nextround'])
            if len(teams)<2 or len(set(teams))!=len(teams) or maximum<0 or next_round<=maximum:return False
            # maxround is generated and persisted by this server's calendar, never a claim parameter.
            for rnd in range(maximum+1):
                expected={(h,a) for h,a in hc.league_round(teams,rnd) if h is not None and a is not None}
                seen=set()
                for match in league.get('matchrecords') or []:
                    if match.get('round')!=rnd:continue
                    goals=match.get('goals') or {};gh,ga=goals.get('home'),goals.get('away')
                    if not isinstance(gh,int) or isinstance(gh,bool) or not isinstance(ga,int) or isinstance(ga,bool) or min(gh,ga)<0:continue
                    pair=(match.get('home'),match.get('away'))
                    if pair in expected:seen.add(pair)
                if seen!=expected:return False
            return True
        except (KeyError,TypeError,ValueError,OverflowError):return False

    @functools.wraps(originals['ep_l2_calendar'])
    def calendar(query,body):
        with hc.STATE_LOCK:
            st=hc._state();out=staged('ep_l2_calendar',st,query,body)
            if out.get('result'):
                st['league2']['season_instance_id']=uuid.uuid4().hex
                st['league2']['season_owner_id']=owner(st)
                dispatch('calendar_before_commit',st,json.loads(body or b'{}'),out)
                hc._save(st)
            return hc._json(out)

    @functools.wraps(originals['ep_l2_end'])
    def end(query,body):
        with hc.STATE_LOCK:
            st=hc._state();lg=st.get('league2') or {}
            receipt=lg.get('season_reward_receipt')
            if receipt:
                if lg.get('season_owner_id')!=owner(st):return hc._json({'result':False,'reason':'LEAGUE_FAIL'})
                return hc._json(live_reply(st,receipt))
            # Legacy finished seasons were already paid by the old implementation.
            # No historical receipt exists to replay; never issue another reward.
            if (lg.get('sponsoroffice') or {}).get('season',{}).get('status')=='finished':
                return hc._json({'result':False,'reason':'LEAGUE_FAIL'})
            if not league_complete(lg):return hc._json({'result':False,'reason':'LEAGUE_FAIL'})
            if lg.get('season_owner_id',owner(st))!=owner(st):return hc._json({'result':False,'reason':'LEAGUE_FAIL'})
            lg.setdefault('season_instance_id',uuid.uuid4().hex)
            lg.setdefault('season_owner_id',owner(st))
            out=staged('ep_l2_end',st,query,body)
            if out.get('result'):
                lg['season_reward_receipt']=summary(out)
                lg['season_reward_claimed']=True
                hc._save(st)  # reward, promotion, EXP and receipt commit together
                out=live_reply(st,out)
            return hc._json(out)

    @functools.wraps(originals['match_step'])
    def match_step(mid,body,step):
        with hc.STATE_LOCK:
            st=hc._state();match=st.get('match') or {}
            if match.get('id')!=mid:return hc._json({'result':False})
            participants={str(p.get('id')) for side in (match.get('side') or {}).values() for p in side.get('players',[]) if p.get('id') is not None}
            if participants and str(owner(st)) not in participants:return hc._json({'result':False,'reason':'INVALID_PARAM'})
            credited=mid in ((st.get('reward_claims') or {}).get('matches') or {})
            if credited or match.get('stage') in ('closed','canceled'):
                return hc._json({'result':True,'resources':[{'uri':f'/match/{mid}','body':match}]})
            old_stage=match.get('stage')
            out=staged('match_step',st,mid,body,step)
            if out.get('result'):
                if old_stage!='playing' and match.get('stage')=='playing':
                    dispatch('match_playing',st,match,json.loads(body or b'{}'))
                hc._save(st)
            return hc._json(out)

    @functools.wraps(originals['ep_match_end'])
    def match_end(mid,query,body):
        with hc.STATE_LOCK:
            st=hc._state();receipts=(st.get('reward_claims') or {}).get('matches') or {}
            prior=receipts.get(mid)
            if prior:
                if prior['owner']!=owner(st):return hc._json({'result':False,'reason':'INVALID_PARAM'})
                if (st.get('match') or {}).get('id')!=mid:
                    return hc._json({'result':True,'resources':[]})
                return hc._json(live_reply(st,prior['response'],mid))
            match=st.get('match') or {}
            if match.get('id')!=mid:
                # Training Ground and other untracked modes intentionally have no reward instance.
                return hc._json({'result':True,'resources':[]})
            participants={str(p.get('id')) for side in (match.get('side') or {}).values() for p in side.get('players',[]) if p.get('id') is not None}
            if participants and str(owner(st)) not in participants:return hc._json({'result':False,'reason':'INVALID_PARAM'})
            # A legacy or simulated already-closed match has already paid its saved reward.
            if match.get('stage')=='closed':
                return hc._json({'result':True,'resources':[{'uri':f'/match/{mid}','body':match}]})
            if match.get('stage')!='playing':return hc._json({'result':False,'reason':'INVALID_PARAM'})
            try:
                req=json.loads(body or b'{}')
                for side in ('home','away'):
                    score=req[side]['score']
                    if isinstance(score,bool) or int(score)!=float(score) or not 0<=int(score)<=999:
                        raise ValueError('invalid score')
            except (KeyError,TypeError,ValueError,OverflowError):
                return hc._json({'result':False,'reason':'INVALID_PARAM'})
            out=staged('ep_match_end',st,mid,query,body)
            if out.get('result'):
                dispatch('match_before_commit',st,match,req,out)
                receipts=st.setdefault('reward_claims',{}).setdefault('matches',{})
                receipts[mid]={'owner':owner(st),'response':summary(out)}
                while len(receipts)>MATCH_RECEIPTS:receipts.pop(next(iter(receipts)))
                hc._save(st)  # EP, EXP, cash, league/cup progress and receipt commit once
                out=live_reply(st,out,mid)
            return hc._json(out)

    @functools.wraps(originals['ep_cup_leave'])
    def cup_leave(cupid,query,body):
        with hc.STATE_LOCK:
            st=hc._state();cup=(st.get('cups') or {}).get(cupid)
            if cup is None:return hc._json({'result':True,'rewards':[]})
            cup_owner=(cup.get('coaches') or [{}])[0].get('_id')
            if cup_owner is not None and str(cup_owner)!=str(owner(st)):
                return hc._json({'result':False,'reason':'ITEM_USE_ERROR'})
            ledger=st.setdefault('reward_claims',{}).setdefault('cups',{})
            if cupid in ledger:
                st['cups'].pop(cupid,None);hc._save(st)
                return hc._json({'result':True,'rewards':[]})
            state=(cup.get('coaches') or [{}])[0].get('state')
            # Champion status is only valid after the server has finished the final.
            if state=='won' and not cup.get('finished'):
                return hc._json({'result':False,'reason':'ITEM_USE_ERROR'})
            out=staged('ep_cup_leave',st,cupid,query,body)
            # Existing playing->leave is abandonment, with no reward. Keep that behavior.
            if out.get('result'):
                ledger[cupid]={'owner':owner(st),'rewards':copy.deepcopy(out.get('rewards',[])),
                               'abandoned':state not in ('won','eliminated')}
                while len(ledger)>CUP_CLAIMS:ledger.pop(next(iter(ledger)))
                hc._save(st)
            return hc._json(out)

    hc.ep_l2_calendar=calendar;hc.ep_l2_end=end;hc.ep_cup_leave=cup_leave
    hc.ep_match_end=match_end;hc.match_step=match_step
    hc.ENDPOINTS['/league2/calendar']=calendar;hc.ENDPOINTS['/league2/end']=end
    # The route table retains function objects, so update that captured handler too.
    hc.ROUTES=[(pattern,cup_leave if fn is originals['ep_cup_leave'] else match_end if fn is originals['ep_match_end'] else fn) for pattern,fn in hc.ROUTES]
    hc.register_reward_hook=register_reward_hook
    hc.league_reward_complete=league_complete
    hc._league_reward_guard_installed=True
