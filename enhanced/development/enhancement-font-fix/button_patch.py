from avm_patch import Code

def patch(a):
    # Preserve the native busy lock. Only reconcile a ready preview that still
    # belongs to the two selected objects; never turn an old response payable.
    mid=26;base=a.A['body_records'][mid]['fields'][1]
    late=a.A['mn'].index('[late]')
    c=Code(a).local(0).ownprop('_available').jump(0x12,'done')
    c.local(0).ownprop('_preview').store(base)
    c.local(base).jump(0x12,'done')
    for key,index in [('first',0),('second',1)]:
        c.local(base).prop(key).local(0).ownprop('_selectedTargets').number(index).op(0x66,late).jump(0x1a,'done')
    c.local(base).prop('protection').jump(0x12,'payable')
    c.local(base).prop('protection').prop('blocked').jump(0x12,'payable')
    # Clicking a blocked quote only opens the existing read-only explanation.
    # The existing first guard in onClickEnhanceButton prevents any PUT.
    c.local(0).ownprop('enhanceButton').op(0x26).set('enabled').jump(0x10,'done')
    c.label('payable').local(0).ownprop('_money').jump(0x12,'done')
    c.local(base).prop('enhancepay').store(base+1)
    c.local(base+1).op(0x95).string('number').jump(0x14,'done')
    c.op(0x5d,a.name('isFinite')).local(base+1).call('isFinite',1).jump(0x12,'done')
    c.local(base+1).number(0).op(0xaf).jump(0x12,'done')
    c.local(0).ownprop('_enhanceCost').local(base+1).set('ep')
    c.local(0).ownprop('enhanceButton').local(0).ownprop('_money').prop('ep').local(base+1).op(0xb0).set('enabled')
    c.label('done')
    a.modify(mid,{len(a.A['body'][mid])-1:c.done()},locals_extra=2)
    # Native money notifications updated text but left the button untouched.
    # Re-evaluate after receiving the wallet, before rendering its labels.
    mid=22;assert a.A['body'][mid][23]==0xf0
    c=Code(a).local(0).owncall('updateControlButtons',0).op(0x29)
    a.modify(mid,{23:c.done()})
