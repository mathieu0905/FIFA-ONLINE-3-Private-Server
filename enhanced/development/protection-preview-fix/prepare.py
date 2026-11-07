from pathlib import Path
R=Path(__file__).parent
source=(R/'enhancement_protection40.before.py').read_text('utf8')
needle='    @functools.wraps(old_preview)\n'
helper='''    def blocked_preview(st,a,b,reason,points,event,**protection):
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
'''
assert source.count(needle)==1
source=source.replace(needle,helper+needle)
source=source.replace("return fail('RESTORE_OTHER_MANAGER',protection=dict(blocked=True,version=VERSION,can_restore=False,\n                        reason='RESTORE_OTHER_MANAGER',label='旧恢复报价属于另一经理，请切回原经理处理；保护不会覆盖旧报价。'))", "return blocked_preview(st,a,b,'RESTORE_OTHER_MANAGER',points,event,can_restore=False,\n                        label='旧恢复报价属于另一经理，请切回原经理处理；保护不会覆盖旧报价。')")
source=source.replace("return fail('RESTORE_PENDING',protection=dict(blocked=True,version=VERSION,label=message,**status,\n                    restore=dict(pending,**status),discard_token=sign(discard),discard_uri='/player/enhance2.5/restore/discard'))", "return blocked_preview(st,a,b,'RESTORE_PENDING',points,event,label=message,**status,\n                    restore=dict(pending,**status),discard_token=sign(discard),discard_uri='/player/enhance2.5/restore/discard')")
old="except ValueError as error:return fail(str(error),message='该等级原本已保级或组合必成功时无需保护，请选“不用”继续。' if str(error)=='PROTECTION_NOT_REQUIRED' else '保护预览条件无效，请重新选择。')"
new="except ValueError as error:return blocked_preview(st,a,b,str(error),points,event,label='该等级原本已保级或组合必成功，无需付费保护；请将加成道具改选“不用”继续。本次没有扣费或消耗材料。' if str(error)=='PROTECTION_NOT_REQUIRED' else '保护预览条件无效，请重新选择。本次没有扣费或消耗材料。')"
assert old in source
source=source.replace(old,new)
assert "return fail('RESTORE_PENDING',protection=" not in source
compile(source,'enhancement_protection40.py','exec')
(R/'enhancement_protection40.py').write_text(source,encoding='utf8')
print('Prepared server-only blocked preview fix; execution unchanged')

