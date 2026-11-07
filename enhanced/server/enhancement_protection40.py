"""Optional client protection: 40% pre-attempt displayed value replaces normal fee."""
import base64
import copy
import functools
import hashlib
import hmac
import json
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import parse_qs

ITEM=1000090
VERSION='protection40-v3-both'
DEFAULT=dict(enabled=True,version=VERSION,ttl=180,fraction_percent=40,ordinary_fee_replaced=True,protect_material=True,material_on_failure='keep',material_on_success='consume')

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

def fee(value):
    if type(value) is not int or value <= 0:
        raise ValueError('PROTECTION_INVALID_VALUE')
    amount = (value * 2 + 4) // 5
    if amount > 2**53 - 1:
        raise ValueError('PROTECTION_PRICE_TOO_LARGE')
    return amount


def install(h):
    if getattr(h,'_protection40_installed',False):return
    cfg=dict(DEFAULT)
    if not isinstance(h.STATE_LOCK,type(threading.RLock())):raise RuntimeError('Protection requires RLock')
    secret=secrets.token_bytes(32)
    def fail(reason,**kw):return h._json(dict(result=False,reason=reason,**kw))
    def owner(st):return str(h.my_coach(st)['_id'])
    def snapshot(p):return {k:v for k,v in p.items() if k!='_market_merge_snapshot'}
    def owns_pending(st,pending):
        slot=h._default_slot(st)
        meta=pending.get('_breakthrough_quote')
        if meta and (meta.get('owner')!=owner(st) or meta.get('slot')!=slot):return False
        return any(h.iid(p)==str(pending.get('id')) for p in st['teams'][str(slot)]['players'])
    def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
    def context(st,a,b,points,event,item):
        slot=h._default_slot(st);pa,pb=h.enhance_pair(st['teams'][str(slot)],a,b)
        if pa is None or not 1<=h.grade_of(pa)<=19 or pa.get('locked') or pb.get('locked') or pa.get('lock') or pb.get('lock'):
            raise ValueError('INVALID_PARAM')
        booster_id='-1' if str(item)==str(ITEM) else str(item)
        booster=h.boost_stack(st,booster_id) if booster_id!='-1' else None
        if booster_id!='-1' and (booster is None or booster.get('expired') or booster.get('__expired')):
            raise ValueError('BOOST_ITEM_UNAVAILABLE')
        # At the ceiling, keep the checkbox protection but do not spend a useless booster.
        if not h.enhancement_point_effective(pa,pb,True):
            booster=None;booster_id='-1'
        rate=h.enhance25_rate(pa,pb,points=='1',booster,event)
        if h.grade_of(pb)==0 or rate>=1:
            raise ValueError('PROTECTION_NOT_REQUIRED')
        bvalue=h.player_value_price(pa['spid'],h.grade_of(pa));protect=fee(bvalue)
        normal=0
        settings=h.enhancement_settings_get()
        effective_points=h.enhancement_point_effective(pa,pb,points=='1')
        data=dict(version=VERSION,owner=owner(st),appat=h.my_coach(st).get('appat'),slot=slot,target=str(a),material=str(b),
                  target_snapshot=digest(snapshot(pa)),material_snapshot=digest(snapshot(pb)),
                  grade=h.grade_of(pa),points=effective_points,event=str(event),base=bvalue,fee=protect,
                  normal_ep=normal,total_ep=normal+protect,rate=rate,boost_itemid=booster_id,
                  boost_snapshot=digest(booster) if booster else None,
                  boost_name=({1000052:'黄金强化加成',1000053:'白银强化加成',1000054:'青铜强化加成'}.get(int(booster_id),h.item_def(int(booster_id)).get('name','强化加成道具')) if booster else None),
                  settings_revision=settings['revision'],rate_configuration_saved=(Path(h.HERE)/'gamedata/enhancement_rates.json').is_file(),
                  rules=digest(cfg))
        return pa,pb,data,booster
    def sign(data):
        body=base64.urlsafe_b64encode(canonical(dict(data,issued=int(time.time()),nonce=secrets.token_hex(8)))).rstrip(b'=')
        return body.decode()+'.'+hmac.new(secret,body,hashlib.sha256).hexdigest()
    def verify(token,data):
        try:
            body,signature=token.split('.')
            if not hmac.compare_digest(hmac.new(secret,body.encode(),hashlib.sha256).hexdigest(),signature):return False
            saved=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
            age=time.time()-saved.pop('issued');saved.pop('nonce')
            return 0<=age<=cfg['ttl'] and saved==data
        except (ValueError,KeyError,TypeError):return False
    def restore_status(st):
        pending=st['enhance_restore']
        p=next((p for p in st['teams'][str(h._default_slot(st))]['players'] if h.iid(p)==str(pending['id'])),None)
        current=h.grade_of(p) if p else -1
        target=pending.get('grade',-1)
        return dict(current_grade=current,restore_grade=target,can_restore=p is not None and 0<=current<target<=h.MAX_GRADE)
    def label(data):
        return ('强化保护：目标卡强化前身价 '+format(data['base'],',')+' EP × 40% = '+format(data['fee'],',')+' EP；本次总计 '+format(data['total_ep'],',')+
                ' EP（已替代原强化手续费，不再另收）。每次尝试均收费，成功失败不退款；成功主卡升1并消耗副卡；失败主卡、副卡均保留，双方等级、经验与阵容位置不变。保护本身不提高概率，可与加成道具及强化点数叠加，点数/道具均为相对加成且不突破同级材料上限；已满上限不扣点数或加成道具，无活动概率加成；最终成功率 '+format(data['rate']*100,'.3f').rstrip('0').rstrip('.')+'%。'+(' 本次同时使用'+data['boost_name']+'，无论成功失败均消耗1个。' if data['boost_name'] else '')+' ES扣取/失败发放保持，不产生恢复报价。')
    if any(ITEM in table for table in (h.ITEMS,h.PACKS,h.PACKAGES,h.MONTHLY)):
        raise RuntimeError('Protection service ID collides with a real product')
    original_item=h.item_def
    def item_def(itemid):
        if itemid==ITEM:
            return dict(itemid=ITEM,productid=ITEM,name='强化保护（身价40%，替代手续费）',
                category='USE',type='ENHANCEMENT_BOOST',unit='COUNT',itemicon=1000002,bundleicon=1000002,
                currency='ep',stackable=False,mingrade=7,maxgrade=20,protection_service=True,
                description='可选强化保护：每次收目标卡强化前身价40%，替代原手续费；失败主副卡均保留，成功消耗副卡。主卡+1至+19且可能失败的有效组合可用；可与黄金等强化加成道具同时使用。',bunches=[])
        return original_item(itemid)
    h.item_def=item_def
    original_static=h.ep_static_item
    def static_item(query,body):
        kind,raw=original_static(query,body)
        data=json.loads(raw)
        if str(ITEM) in [str(i) for i in json.loads(body or b'{}').get('itemids',[])]:data[str(ITEM)]=item_def(ITEM)
        return h._json(data)
    original_inventory_add=h.inventory_add
    def inventory_add(coach,itemid,count):
        if int(itemid)==ITEM:raise ValueError('Protection is a service, not an inventory item')
        return original_inventory_add(coach,itemid,count)
    h.inventory_add=inventory_add
    original_bag_add=h.bag_add
    def bag_add(st,title,items=(),players=(),msg=''):
        if any(int(i.get('itemid',0))==ITEM for i in items):raise ValueError('Protection cannot be gifted')
        return original_bag_add(st,title,items,players,msg)
    h.bag_add=bag_add
    original_items=h.coach_items
    def coach_items(st,slot,where='items'):
        # Protection is now an independent checkbox, never a booster inventory row.
        return [row for row in original_items(st,slot,where) if str(row.get('itemid'))!=str(ITEM)]
    h.coach_items=coach_items
    old_preview=h.ep_enhance25_preview;old_enhance=h.ep_enhance25
    def requested(item,query):
        params=parse_qs(query)
        return str(item)==str(ITEM) or params.get('protection')==['1'] or 'protection_ack' in params or 'protection_token' in params
    def blocked_preview(st,a,b,reason,points,event,item='-1',**protection):
        # Business unavailability is a successful read, never a transport error.
        # Native RC treats result=False on GET as a fatal server-data failure.
        # No payment token is issued; the shipped click guard blocks execution.
        pa,pb=h.enhance_pair(st['teams'][str(h._default_slot(st))],a,b)
        valid=pa is not None and 1<=h.grade_of(pa)<=h.MAX_GRADE
        payload=dict(result=True,reason=reason,grade=min(h.MAX_GRADE,h.enhance_grade(pa,pb)) if valid else 1,
            levelinfo=h.player_levelinfo(pa) if valid else dict(level=1,exp=0,to=100),exp=0,
            price=0,probability=round(h.enhance25_rate(pa,pb,points=='1',h.boost_stack(st,str(item)) if str(item)!=str(ITEM) else None,event)*100,3) if valid else 0,
            enhancepay=0,needes=h.enhance_es(pa) if valid else 0,
            protection=dict(protection,blocked=True,available=False,version=VERSION,reason=reason,fee=0,total_ep=0))
        return h._json(payload)
    @functools.wraps(old_preview)
    def preview(a,b,points,item,event,query,body):
        if not requested(item,query):return old_preview(a,b,points,item,event,query,body)
        with h.STATE_LOCK:
            st=h._state()
            pending=st.get('enhance_restore')
            if pending:
                if not owns_pending(st,pending):
                    return blocked_preview(st,a,b,'RESTORE_OTHER_MANAGER',points,event,item=item,can_restore=False,
                        label='旧恢复报价属于另一经理，请切回原经理处理；保护不会覆盖旧报价。')
                status=restore_status(st)
                message=('请先按原报价恢复，或明确放弃旧恢复报价，再重新预览保护。' if status['can_restore'] else
                    '当前+'+str(status['current_grade'])+'，旧报价恢复到+'+str(status['restore_grade'])+'，已无需恢复或当前不可恢复；只能明确放弃旧报价或关闭，不会降低主卡。')
                discard=dict(action='discard_restore',owner=owner(st),appat=h.my_coach(st).get('appat'),slot=h._default_slot(st),pending=digest(pending),version=VERSION)
                return blocked_preview(st,a,b,'RESTORE_PENDING',points,event,item=item,label=message,**status,
                    restore=dict(pending,**status),discard_token=sign(discard),discard_uri='/player/enhance2.5/restore/discard')
            try:pa,pb,data,booster=context(st,a,b,points,event,item)
            except ValueError as error:return blocked_preview(st,a,b,str(error),points,event,item=item,label='该组合不提升强化等级或原本必成功，无需付费保护；请取消勾选“强化保护”后继续。本次没有扣费或消耗材料。' if str(error)=='PROTECTION_NOT_REQUIRED' else '加成道具不足、已失效或保护条件无效，请重新选择。本次没有扣费或消耗材料。')
            rate=data['rate']
            # Native expLabel displays experience gained this attempt from zero;
            # merge_into grants no experience, while levelinfo keeps existing XP.
            return h._json(dict(result=True,grade=h.enhance_grade(pa,pb),levelinfo=h.player_levelinfo(pa),exp=0,
                price=h.player_value_price(pa['spid'],h.enhance_grade(pa,pb)),probability=round(rate*100,3),
                enhancepay=data['total_ep'],needes=h.enhance_es(pa) if h.enhancement_point_effective(pa,pb,True) else 0,
                protection=dict(version=VERSION,fee=data['fee'],total_ep=data['total_ep'],label=label(data),token=sign(data),expires_at=int(time.time())+cfg['ttl'])))
    @functools.wraps(old_enhance)
    def enhance(a,b,points,item,event,query,body):
        if not requested(item,query):return old_enhance(a,b,points,item,event,query,body)
        with h.STATE_LOCK:
            st=h._state()
            try:pa,pb,data,booster=context(st,a,b,points,event,item)
            except ValueError as error:return fail(str(error))
            params=parse_qs(query)
            if params.get('protection_ack')!=[VERSION] or not verify((params.get('protection_token') or [''])[0],data):return fail('PROTECTION_REPREVIEW_REQUIRED')
            receipt_key=hashlib.sha256(params['protection_token'][0].encode()).hexdigest()
            attempt_coach=h.my_coach(st)
            if receipt_key in attempt_coach.get('protection_attempt_receipts',{}):return fail('PROTECTION_ALREADY_USED')
            if st.get('enhance_restore'):return fail('RESTORE_PENDING')
            if h.my_coach(st).get('ep',h.START_EP)<data['total_ep']:return fail('NOT_ENOUGH_EP')
            need=h.enhance_es(pa)
            if data['points'] and h.my_coach(st).get('es',0)<need:return fail('NOT_ENOUGH_ES')
            before=h.grade_of(pa);slot=h._default_slot(st);team=st['teams'][str(slot)]
            success=h.random.random()<data['rate']
            h.add_ep(st,-data['total_ep'])
            if data['points']:h.add_es(st,-need)
            if booster:
                booster['remains']-=1
                if not booster['remains']:h.my_coach(st)['items'].remove(booster)
            pa['grade']=before+1 if success else before
            if success:h.merge_into(team,pa,pb)
            else:pa.pop('_market_merge_snapshot',None)
            grant=0 if success else need
            h.add_es(st,grant)
            out=dict(result=True,success=success,grade=pa['grade'],rgrade=pa['grade'],rprice=h.player_value_price(pa['spid'],pa['grade']),
                attribPlus=h.GRADE_BOOST[pa['grade']]-h.GRADE_BOOST[before],grantes=grant,
                usepoint={'currency':'ES','price':0},getitems=[],resources=h.coach_me_resources(st,slot),
                protection=dict(applied=True,paid=True,fee=data['fee'],total_ep=data['total_ep'],kept_grade=not success,material_kept=not success,protected_cards='main_and_material',version=VERSION))
            stamp=time.time()
            receipts={key:expiry for key,expiry in attempt_coach.get('protection_attempt_receipts',{}).items() if expiry>=stamp}
            receipts[receipt_key]=stamp+cfg['ttl']
            attempt_coach['protection_attempt_receipts']=receipts
            h._save(st)
            return h._json(out)
    def discard(query,body):
        with h.STATE_LOCK:
            st=h._state();pending=st.get('enhance_restore')
            if not pending:return fail('NO_PENDING_RESTORE')
            if not owns_pending(st,pending):return fail('RESTORE_OTHER_MANAGER')
            data=dict(action='discard_restore',owner=owner(st),appat=h.my_coach(st).get('appat'),slot=h._default_slot(st),pending=digest(pending),version=VERSION)
            params=parse_qs(query)
            if params.get('protection_ack')!=[VERSION] or not verify((params.get('protection_token') or [''])[0],data):return fail('PROTECTION_REPREVIEW_REQUIRED')
            st.pop('enhance_restore');h._save(st)
            return h._json(dict(result=True,discarded=True,resources=h.coach_me_resources(st,h._default_slot(st))))
    replacements={old_preview:preview,old_enhance:enhance,original_static:static_item}
    h.ROUTES=[(pat,replacements.get(fn,fn)) for pat,fn in h.ROUTES]
    for uri,fn in list(h.ENDPOINTS.items()):h.ENDPOINTS[uri]=replacements.get(fn,fn)
    h.ep_enhance25_preview=preview;h.ep_enhance25=enhance
    h.ep_static_item=static_item
    h.ENDPOINTS['/player/enhance2.5/restore/discard']=discard
    h.ENDPOINTS['/info/enhancement/protection/rules']=lambda query,body:h._json(dict(cfg,
        wallet='EP',service_itemid=ITEM,base_policy='Target current pre-attempt player_value_price; ceil(value * 40 / 100); replaces ordinary fee',
        failure='Keeps both main and material instances, grades, XP and squad slots; original ES rules; no restore quote',success='Upgrade main; consume material',protected_cards='main_and_material',
        fee_on='Every confirmed attempt, success or failure',boost_item_exclusive=False,independent_checkbox=True))
    h.PROTECTION40=copy.deepcopy(cfg);h.protection40_fee=lambda grade,spid:fee(h.player_value_price(spid,grade))
    original_log=h.H._log
    def log(request,body):
        path=request.path
        try:
            request.path=re.sub(r'([?&]protection_token=)[^&]*',r'\1[redacted]',path)
            return original_log(request,body)
        finally:request.path=path
    h.H._log=log
    h._protection40_installed=True
