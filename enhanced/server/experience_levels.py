"""Versioned player level extension and strict EXP-capsule use; startup only.

No install-time state mutation. The matching client resource is required for the
post-23 attribute curve and native quantity control; this is not a UI-only cap.
"""
import functools
import types

VERSION = 'player-level30-v1'
MAX_LEVEL = 30
EXTENDED_NEED = dict(zip(range(23,30),(6000,9000,13500,20000,30000,45000,67500)))


def level_boost(level):
    level = max(1,min(MAX_LEVEL,int(level)))
    return level-1 if level<=23 else 22+(level-22)//2


def install(hc):
    if getattr(hc,'_experience_levels_installed',False):return
    original_need=hc.player_need
    def player_need(level):
        return EXTENDED_NEED.get(int(level),original_need(level))
    hc.PLAYER_MAX_LEVEL=MAX_LEVEL
    hc.player_need=player_need
    hc.player_level_boost=level_boost
    hc.EXPPLAYER={str(lv):{'requiredplayerexp':player_need(lv)} for lv in range(1,MAX_LEVEL+2)}
    original_file=hc.from_file
    def from_file(path):
        if path=='/static/db/EXPPLAYER':return hc._json(hc.EXPPLAYER)
        return original_file(path)
    hc.from_file=from_file

    # xi_ratings is the only server path that adds level-1 to positional OVR.
    # Clone only this function's dependency: public/persisted level remains 30.
    original_xi=hc.xi_ratings
    if not isinstance(original_xi,types.FunctionType) or original_xi.__closure__:
        raise RuntimeError('Review new xi_ratings wrapper before extending level curve')
    actual_levelinfo=hc.player_levelinfo
    def effective_levelinfo(player):
        info=dict(actual_levelinfo(player))
        info['level']=level_boost(info['level'])+1
        return info
    xi_globals=dict(original_xi.__globals__,player_levelinfo=effective_levelinfo)
    hc.xi_ratings=types.FunctionType(original_xi.__code__,xi_globals,original_xi.__name__,original_xi.__defaults__)

    original_use=hc.use_item
    @functools.wraps(original_use)
    def use_item(st,slot,coach,it,req):
        if hc.ITEMS[it['itemid']][2]=='PLAYER_EXP_CAPSULE':
            player=next((p for p in st['teams'][str(slot)]['players'] if hc.iid(p)==str(req.get('targetid'))),None)
            if player is None or player.get('locked') or player.get('lock'):
                return {'result':False,'reason':'ITEM_USE_ERROR'}
            expected=req.get('expected')
            if expected is not None:
                info=hc.player_levelinfo(player)
                current=dict(level=info['level'],exp=info['exp'],remains=it['remains'])
                if (not isinstance(expected,dict) or set(expected)!=set(current)
                        or any(type(value) is not int for value in expected.values()) or expected!=current):
                    return {'result':False,'reason':'ITEM_USE_ERROR'}
        return original_use(st,slot,coach,it,req)
    hc.use_item=use_item
    def rules():
        return dict(version=VERSION,max_level=MAX_LEVEL,
                    transitions=[dict(level=lv,required_exp=player_need(lv)) for lv in range(1,MAX_LEVEL)],
                    attribute_bonus={str(lv):level_boost(lv) for lv in range(1,MAX_LEVEL+1)},
                    legacy_level1_to23_preserved=True,
                    full_cap_retains_unused_capsules=True)
    hc.player_level_rules=rules
    hc.ENDPOINTS['/info/player/level_rules']=lambda q,b:hc._json(rules())
    hc._experience_levels_installed=True
