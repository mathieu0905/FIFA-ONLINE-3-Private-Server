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
VERSION='protection40-v1'
DEFAULT=dict(enabled=True,version=VERSION,ttl=180,fraction_percent=40,ordinary_fee_replaced=True)

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
    def context(st,a,b,points,event):
        slot=h._default_slot(st);pa,pb=h.enhance_pair(st['teams'][str(slot)],a,b)
        if pa is None or not 1<=h.grade_of(pa)<=19 or pa.get('locked') or pb.get('locked') or pa.get('lock') or pb.get('lock'):
            raise ValueError('INVALID_PARAM')
        if h.enhancement_failure_grade(pa)==h.grade_of(pa) or h.grade_of(pb)==0 or h.enhance25_rate(pa,pb,points=='1',None,event)>=1:
            raise ValueError('PROTECTION_NOT_REQUIRED')
        bvalue=h.player_value_price(pa['spid'],h.grade_of(pa));protect=fee(bvalue)
        normal=0
        settings=h.enhancement_settings_get()
        data=dict(version=VERSION,owner=owner(st),appat=h.my_coach(st).get('appat'),slot=slot,target=str(a),material=str(b),
                  target_snapshot=digest(snapshot(pa)),material_snapshot=digest(snapshot(pb)),
                  grade=h.grade_of(pa),points=points=='1',event=str(event),base=bvalue,fee=protect,
                  normal_ep=normal,total_ep=normal+protect,rate=h.enhance25_rate(pa,pb,points=='1',None,event),
                  settings_revision=settings['revision'],rate_configuration_saved=(Path(h.HERE)/'gamedata/enhancement_rates.json').is_file(),
                  rules=digest(cfg))
        return pa,pb,data
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
                ' EP（已替代原强化手续费，不再另收）。每次尝试均收费，成功失败不退款；成功升1、失败主卡保级、经验保留，材料仍消耗。概率不提升；与加成道具互斥，当前+12起（冲+13）点数按材料加成后基础概率相对提高10%，ES扣取/失败发放保持，不产生恢复报价。')
    if any(ITEM in table for table in (h.ITEMS,h.PACKS,h.PACKAGES,h.MONTHLY)):
        raise RuntimeError('Protection service ID collides with a real product')
    original_item=h.item_def
    def item_def(itemid):
        if itemid==ITEM:
            return dict(itemid=ITEM,productid=ITEM,name='强化保护（身价40%，替代手续费）',
                category='USE',type='ENHANCEMENT_BOOST',unit='COUNT',itemicon=1000002,bundleicon=1000002,
                currency='ep',stackable=False,mingrade=7,maxgrade=20,protection_service=True,
                description='可选强化保护：每次收目标卡强化前身价40%，替代原手续费；失败保级、材料照耗。仅会掉级且可能失败的+6至+19（+10阶段线除外）组合可用；与加成道具互斥。',bunches=[])
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
        rows=original_items(st,slot,where)
        if where=='items' and not any(row.get('itemid')==ITEM for row in rows):rows=rows+[dict(_id='bp-protection-service',id='bp-protection-service',itemid=ITEM,remains=1,count=1,
                                        expireable=True,expired=False,staticdata=h.item_def(ITEM))]
        return rows
    h.coach_items=coach_items
    old_preview=h.ep_enhance25_preview;old_enhance=h.ep_enhance25
    def blocked_preview(st,a,b,reason,points,event,**protection):
        # Business unavailability is a successful read, never a transport error.
        # Native RC treats result=False on GET as a fatal server-data failure.
        # No payment token is issued; the shipped click guard blocks execution.
        pa,pb=h.enhance_pair(st['teams'][str(h._default_slot(st))],a,b)
        valid=pa is not None and 1<=h.grade_of(pa)<=h.MAX_GRADE
        payload=dict(result=True,reason=reason,grade=min(h.MAX_GRADE,h.enhance_grade(pa,pb)) if valid else 1,
            levelinfo=h.player_levelinfo(pa) if valid else dict(level=1,exp=0,to=100),exp=0,
            price=0,probability=round(h.enhance25_rate(pa,pb,points=='1',None,event)*100,3) if valid else 0,
            enhancepay=0,needes=h.enhance_es(pa) if valid else 0,
            protection=dict(protection,blocked=True,available=False,version=VERSION,reason=reason,fee=0,total_ep=0))
        return h._json(payload)
    @functools.wraps(old_preview)
    def preview(a,b,points,item,event,query,body):
        if str(item)!=str(ITEM):return old_preview(a,b,points,item,event,query,body)
        with h.STATE_LOCK:
            st=h._state()
            pending=st.get('enhance_restore')
            if pending:
                if not owns_pending(st,pending):
                    return blocked_preview(st,a,b,'RESTORE_OTHER_MANAGER',points,event,can_restore=False,
                        label='旧恢复报价属于另一经理，请切回原经理处理；保护不会覆盖旧报价。')
                status=restore_status(st)
                message=('请先按原报价恢复，或明确放弃旧恢复报价，再重新预览保护。' if status['can_restore'] else
                    '当前+'+str(status['current_grade'])+'，旧报价恢复到+'+str(status['restore_grade'])+'，已无需恢复或当前不可恢复；只能明确放弃旧报价或关闭，不会降低主卡。')
                discard=dict(action='discard_restore',owner=owner(st),appat=h.my_coach(st).get('appat'),slot=h._default_slot(st),pending=digest(pending),version=VERSION)
                return blocked_preview(st,a,b,'RESTORE_PENDING',points,event,label=message,**status,
                    restore=dict(pending,**status),discard_token=sign(discard),discard_uri='/player/enhance2.5/restore/discard')
            try:pa,pb,data=context(st,a,b,points,event)
            except ValueError as error:return blocked_preview(st,a,b,str(error),points,event,label='该等级原本已保级或组合必成功，无需付费保护；请将加成道具改选“不用”继续。本次没有扣费或消耗材料。' if str(error)=='PROTECTION_NOT_REQUIRED' else '保护预览条件无效，请重新选择。本次没有扣费或消耗材料。')
            rate=h.enhance25_rate(pa,pb,points=='1',None,event)
            # Native expLabel displays experience gained this attempt from zero;
            # merge_into grants no experience, while levelinfo keeps existing XP.
            return h._json(dict(result=True,grade=h.enhance_grade(pa,pb),levelinfo=h.player_levelinfo(pa),exp=0,
                price=h.player_value_price(pa['spid'],h.enhance_grade(pa,pb)),probability=round(rate*100,3),
                enhancepay=data['total_ep'],needes=h.enhance_es(pa),
                protection=dict(version=VERSION,fee=data['fee'],total_ep=data['total_ep'],label=label(data),token=sign(data),expires_at=int(time.time())+cfg['ttl'])))
    @functools.wraps(old_enhance)
    def enhance(a,b,points,item,event,query,body):
        if str(item)!=str(ITEM):return old_enhance(a,b,points,item,event,query,body)
        with h.STATE_LOCK:
            st=h._state()
            try:pa,pb,data=context(st,a,b,points,event)
            except ValueError as error:return fail(str(error))
            params=parse_qs(query)
            if params.get('protection_ack')!=[VERSION] or not verify((params.get('protection_token') or [''])[0],data):return fail('PROTECTION_REPREVIEW_REQUIRED')
            if st.get('enhance_restore'):return fail('RESTORE_PENDING')
            if h.my_coach(st).get('ep',h.START_EP)<data['total_ep']:return fail('NOT_ENOUGH_EP')
            need=h.enhance_es(pa)
            if points=='1' and h.my_coach(st).get('es',0)<need:return fail('NOT_ENOUGH_ES')
            before=h.grade_of(pa);slot=h._default_slot(st);team=st['teams'][str(slot)]
            success=h.random.random()<h.enhance25_rate(pa,pb,points=='1',None,event)
            h.add_ep(st,-data['total_ep'])
            if points=='1':h.add_es(st,-need)
            pa['grade']=before+1 if success else before
            h.merge_into(team,pa,pb)
            grant=0 if success else need
            h.add_es(st,grant)
            out=dict(result=True,success=success,grade=pa['grade'],rgrade=pa['grade'],rprice=h.player_value_price(pa['spid'],pa['grade']),
                attribPlus=h.GRADE_BOOST[pa['grade']]-h.GRADE_BOOST[before],grantes=grant,
                usepoint={'currency':'ES','price':0},getitems=[],resources=h.coach_me_resources(st,slot),
                protection=dict(applied=True,paid=True,fee=data['fee'],total_ep=data['total_ep'],kept_grade=not success,version=VERSION))
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
        failure='Keeps target grade/XP; consumes material; original ES rules; no restore quote',
        fee_on='Every confirmed attempt, success or failure',boost_item_exclusive=True))
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
