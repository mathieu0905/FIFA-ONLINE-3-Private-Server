"""Low construction fees with user-controlled live base rates; never sets rates."""
import copy
import functools
import json
from pathlib import Path

VERSION='growth-live-rates-v1'
DEFAULT=dict(enabled=False,version=VERSION,rate_policy='current-defaults-and-explicit-user-settings',construction_divisor=100)

def install(h,config=None):
    if getattr(h,'_growth_v2_installed',False):return
    path=Path(h.HERE)/'gamedata/growth_live_rates.json'
    cfg=dict(DEFAULT,**(config if config is not None else json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}))
    if type(cfg['enabled']) is not bool or cfg!=dict(DEFAULT,enabled=cfg['enabled']):
        raise ValueError('Growth-v2 parameters are published together; use a new version to change them')
    if not cfg['enabled']:
        h._growth_v2_installed=True;return
    if not getattr(h,'_breakthrough_balance_installed',False) or getattr(h,'_bp_protection_installed',False):
        raise RuntimeError('Install growth after breakthrough, before BP protection')
    if not callable(getattr(h,'enhancement_settings_get',None)):
        raise RuntimeError('Install current enhancement_settings before live-rate growth fees')
    # Valuation publishes its frozen original construction anchor. Never use a
    # dynamic market quote or a newly increased high-grade market valuation.
    anchor=getattr(h,'frozen_construction_price',h.card_price)
    old_cost=h.enhance_cost
    # Deliberately do not assign ENHANCE_RATE. File absence does not authorize
    # changing defaults; an explicitly saved default-valued file is still saved.
    def cost(target):
        grade=h.grade_of(target)
        if 5<=grade<=9:
            return max(1000,h.sig3(anchor(target['spid'],grade)//cfg['construction_divisor']))
        return old_cost(target)
    h.enhance_cost=cost
    # New material-rate combinations can yield 50.5%, so preserve their exact
    # preview instead of the legacy integer rounding. Unchanged 0..4 stays exact.
    originals={name:getattr(h,name) for name in ('ep_enhance_preview','ep_enhance25_preview')}
    def precise(name,args,points=False,itemid='-1',event='-1'):
        with h.STATE_LOCK:
            st=h._state();pa,pb=h.enhance_pair(st['teams'][str(h._default_slot(st))],args[0],args[1])
            response=originals[name](*args)
            if pa is None or not 5<=h.grade_of(pa)<=9:return response
            out=json.loads(response[1])
            if out.get('result'):
                rate=h.enhance_rate(pa,pb) if name=='ep_enhance_preview' else h.enhance25_rate(pa,pb,points,h.boost_stack(st,itemid),event)
                out['probability']=round(rate*100,3)
            return h._json(out)
    @functools.wraps(originals['ep_enhance_preview'])
    def preview(a,b,query,body):return precise('ep_enhance_preview',(a,b,query,body))
    @functools.wraps(originals['ep_enhance25_preview'])
    def preview25(a,b,points,item,event,query,body):
        return precise('ep_enhance25_preview',(a,b,points,item,event,query,body),points=='1',item,event)
    changes={originals['ep_enhance_preview']:preview,originals['ep_enhance25_preview']:preview25}
    h.ROUTES=[(pattern,changes.get(fn,fn)) for pattern,fn in h.ROUTES]
    for uri,fn in list(h.ENDPOINTS.items()):h.ENDPOINTS[uri]=changes.get(fn,fn)
    h.ep_enhance_preview=preview;h.ep_enhance25_preview=preview25
    h.GROWTH_V2=copy.deepcopy(cfg)
    def rules(query,body):
        with h.STATE_LOCK:
            current=tuple(h.ENHANCE_RATE);settings=h.enhancement_settings_get()
            return h._json(dict(cfg,configuration_saved=(Path(h.HERE)/'gamedata/enhancement_rates.json').is_file(),
                settings_revision=settings['revision'],settings=settings,
                actual_grade_rows=[dict(target_grade=g,base_rate=current[g],
                    plus1_gold_es_percent=min(100,100*(current[g]+.25)),
                    plus1_bp_es_percent=min(100,100*(current[g]+.10))) for g in range(5,10)],
                construction_anchor='Frozen historical card value, +5..9 1%; other grades unchanged',
                restore_quotes='Existing pending restore prices preserved; BP signature binds live settings revision'))
    h.ENDPOINTS['/info/enhancement/growth/rules']=rules
    h._growth_v2_installed=True
