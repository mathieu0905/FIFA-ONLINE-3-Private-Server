from client_tools import *
BOX='fo3ProtectionCheckbox';MARK='fo3ProtectionMark'
PREF_PROTECTION='fo3RememberProtection';PREF_POINT='fo3RememberPoint';PREF_ITEM='fo3RememberItem'

def box(c,local):
    c.local(0).string(BOX).call('getChildByName',1).store(local)
    c.local(local).jump(0x12,'done')

def protection_restore(a,base):
    c=Code(a);box(c,base)
    c.local(base).local(base).prop(PREF_PROTECTION).op(0x76).set('selected')
    c.local(base).string(MARK).call('getChildByName',1).store(base+1)
    c.local(base+1).jump(0x12,'done');c.local(base+1).local(base).prop('selected').set('visible')
    c.label('done');return c.done()

def point_restore(a,base,label=False):
    c=Code(a);box(c,base)
    c.op(0x27).store(base+1)
    c.local(0).ownprop('_available').jump(0x12,'apply')
    c.local(base).prop(PREF_POINT).jump(0x12,'apply')
    c.local(0).ownprop('_money').jump(0x12,'apply')
    c.local(0).ownprop('_money').prop('es')
    c.local(0).ownprop('_selectedTargets').number(0).op(0x66,a.A['mn'].index('[late]')).prop('grade')
    c.number(1).op(0xa0).number(10).op(0xa2).jump(0x15,'apply')
    c.op(0x26).store(base+1)
    c.label('apply');c.local(0).prop('usePointCheckBox').local(base+1).set('selected')
    if label:c.local(0).local(base+1).owncall('setEsLabel',1).op(0x29)
    c.label('done');return c.done()

def remember(a,base,field,kind):
    c=Code(a);box(c,base)
    if kind=='item':c.local(base).prop('fo3RestoringItems').jump(0x11,'done')
    c.local(base)
    if kind=='protection':c.local(base).prop('selected').op(0x76)
    elif kind=='point':c.local(0).prop('usePointCheckBox').prop('selected').op(0x76)
    elif kind=='item':
        c.local(0).ownprop('_selectItem').jump(0x12,'none')
        c.local(0).ownprop('_selectItem').prop('value').jump(0x10,'value')
        c.label('none').number(0);c.label('value')
    c.set(field);c.label('done');return c.done()

def control_patch(a):
    # Bind to native methods, preserving all existing bytecode and guards.
    assert any(c[0]=='EnhanceControlPanel' for c in a.A['cls'])
    initial=a.A['body_records'][8]['fields'][1]
    c=Code(a);box(c,initial)
    c.local(initial).prop('fo3RememberReady').jump(0x11,'done')
    c.local(initial).op(0x26).set('fo3RememberReady')
    for name,value in ((PREF_PROTECTION,False),(PREF_POINT,False),(PREF_ITEM,0)):
        c.local(initial)
        if type(value) is bool:c.op(0x26 if value else 0x27)
        else:c.number(value)
        c.set(name)
    c.local(initial).string('fo3ProtectionCaption').call('getChildByName',1).store(initial+1)
    c.local(initial+1).jump(0x12,'done');c.local(initial+1).string('强化保护（40%，失败双卡保留）').set('text')
    c.label('done');a.modify(8,{len(a.A['body'][8])-1:c.done()},locals_extra=2)

    # Explicit reset clears preferences. Ordinary result/pair refresh does not.
    base=a.A['body_records'][18]['fields'][1];c=Code(a);box(c,base)
    for name in (PREF_PROTECTION,PREF_POINT):c.local(base).op(0x27).set(name)
    c.local(base).number(0).set(PREF_ITEM);c.label('done')
    a.modify(18,{7:c.done()},locals_extra=1)
    a.modify(25,{567:protection_restore(a,a.A['body_records'][25]['fields'][1])},locals_extra=2)

    # These handlers run only for explicit user choices, not native list rebuilds.
    for mid,offset,field,kind in ((21,109,PREF_POINT,'point'),(24,52,PREF_ITEM,'item')):
        a.modify(mid,{offset:remember(a,a.A['body_records'][mid]['fields'][1],field,kind)},locals_extra=1)
    toggle=45
    rows=dis(a.A,a.A['body'][toggle]);at=next(int(line.split(':',1)[0]) for line in rows if 'findpropstrict requestPreview' in line)
    a.modify(toggle,{at:remember(a,a.A['body_records'][toggle]['fields'][1],PREF_PROTECTION,'protection')},locals_extra=1)

    # Restore by item ID from the current native eligible-item list. Never substitute.
    mid=30;base=a.A['body_records'][mid]['fields'][1];late=a.A['mn'].index('[late]');c=Code(a);box(c,base)
    c.local(base).prop(PREF_ITEM).string('').op(0xa0).store(base+1)
    c.local(base+1).string('0').jump(0x13,'done')
    c.number(0).store(base+2)
    c.label('loop').local(base+2).local(2).prop('length').jump(0x0c,'done')
    c.local(2).local(base+2).op(0x66,late).prop('value').string('').op(0xa0).local(base+1).jump(0x14,'next')
    c.local(0).local(2).local(base+2).owncall('selectDefaultBoostItem',2).op(0x29).jump(0x10,'done')
    c.label('next').local(base+2).number(1).op(0xa0).store(base+2).jump(0x10,'loop')
    c.label('done');c.local(base).jump(0x12,'exit');c.local(base).op(0x27).set('fo3RestoringItems');c.label('exit')
    begin=Code(a);box(begin,base);begin.local(base).op(0x26).set('fo3RestoringItems');begin.label('done')
    a.modify(mid,{7:begin.done(),327:c.done()},locals_extra=3)

    # Restore before URI capture and after native pending-preview reset.
    a.modify(35,{50:point_restore(a,a.A['body_records'][35]['fields'][1])},locals_extra=2)
    a.modify(26,{364:point_restore(a,a.A['body_records'][26]['fields'][1],label=True)},locals_extra=2)
    # Currency/inventory changes get a fresh quote, never an automatic PUT.
    for mid in (22,23):
        c=Code(a).local(0).ownprop('_available').jump(0x12,'done')
        c.local(0).owncall('requestPreview',0).op(0x29);c.label('done')
        a.modify(mid,{len(a.A['body'][mid])-1:c.done()})
    return dict(toggle_callback=toggle,remember_scope='Current enhancement page, including result return and pair changes',reset_clears_preferences=True)

def popup_patch(a):
    # The user still clicks the native confirm button. Only its redundant
    # protection-fee dialog is bypassed; fresh signed URI/payment path is intact.
    mid=33;base=a.A['body_records'][mid]['fields'][1];c=Code(a)
    c.local(0).ownprop('_data').store(base);c.local(base).jump(0x12,'done')
    c.local(base).prop('info').jump(0x12,'done')
    c.local(base).prop('info').prop('protection').store(base+1);c.local(base+1).jump(0x12,'done')
    c.local(base+1).prop('blocked').jump(0x11,'done')
    c.local(base+1).prop('token').jump(0x12,'done')
    c.local(base+1).prop('version').jump(0x12,'done')
    c.local(base).op(0x26).set('_bpConfirmed');c.label('done')
    a.modify(mid,{2:c.done()},locals_extra=2)
    return dict(native_confirm_preserved=True,extra_protection_fee_dialog_removed=True)
