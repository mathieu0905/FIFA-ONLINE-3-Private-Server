from client_tools import *
COMMAND='restore protected pair'

def control_patch(a):
    mid=20;scope=a.A['body_records'][mid]['fields'][3]
    c=Code(a).local(0).op(0x30)
    c.find('_owner').ownprop('_owner').store(2);c.local(2).jump(0x12,'done')
    c.local(2).string(COMMAND).local(1).call('query',2).op(0x29);c.label('done').op(0x47)
    callback=a.add_method(c.done(),scope,local_count=3)
    base=a.A['body_records'][mid]['fields'][1]
    # attachScreen receives [screen, data] on the operand stack. Add only a
    # callback, retaining the exact native first/second player objects and flow.
    c=Code(a).store(base);c.local(base).op(0x40,callback).set('fo3RestorePair');c.local(base)
    rows=dis(a.A,a.A['body'][mid]);at=next(int(line.split(':',1)[0]) for line in rows if 'callproperty attachScreen (2)' in line)
    a.modify(mid,{at:c.done()},locals_extra=1)
    return dict(restore_callback=callback)

def owner_patch(a):
    mid=18;base=a.A['body_records'][mid]['fields'][1];late=a.A['mn'].index('[late]');c=Code(a)
    c.local(1).string(COMMAND).jump(0x14,'native')
    # Restore only on the same live page, without overwriting a newer manual pair.
    c.local(0).prop('stage').jump(0x12,'done');c.local(0).prop('visible').jump(0x12,'done')
    c.local(0).prop('firstTarget').jump(0x11,'done');c.local(0).prop('secondTarget').jump(0x11,'done')
    c.local(2).jump(0x12,'done');c.local(2).prop('firstPlayer').store(base);c.local(base).jump(0x12,'done')
    c.local(2).prop('secondPlayer').store(base+1);c.local(base+1).jump(0x12,'done')
    c.local(base).prop('_id').jump(0x12,'done');c.local(base+1).prop('_id').jump(0x12,'done')
    c.local(base).prop('_id').local(base+1).prop('_id').jump(0x13,'done')
    c.local(0).ownprop('_players').store(base+2);c.local(base+2).jump(0x12,'done')
    c.op(0x20).store(base+3);c.op(0x20).store(base+4);c.number(0).store(base+5)
    c.label('loop').local(base+5).local(base+2).prop('length').jump(0x0c,'found')
    c.local(base+2).local(base+5).op(0x66,late).store(base+6)
    c.local(base+6).prop('_id').local(base).prop('_id').jump(0x14,'second')
    c.local(base+6).store(base+3)
    c.label('second').local(base+6).prop('_id').local(base+1).prop('_id').jump(0x14,'next')
    c.local(base+6).store(base+4)
    c.label('next').local(base+5).number(1).op(0xa0).store(base+5).jump(0x10,'loop')
    c.label('found').local(base+3).jump(0x12,'done');c.local(base+4).jump(0x12,'done')
    for row,old in ((base+3,base),(base+4,base+1)):
        for key in ('spid','grade'):c.local(row).prop(key).local(old).prop(key).jump(0x14,'done')
        c.local(0).local(row).owncall('availableEnhancePlayer',1).jump(0x12,'done')
        c.local(0).local(row).prop('locked').owncall('isPlayerLocked',1).jump(0x11,'done')
    c.local(base+3).prop('spid').local(base+4).prop('spid').jump(0x14,'done')
    c.local(0).local(base+3).local(base+4).owncall('selectTarget',2).op(0x29)
    c.local(0).owncall('invalidatePlayerList',0).op(0x29)
    c.label('done').op(0x47);c.label('native')
    a.modify(mid,{7:c.done()},locals_extra=7)
    return {}

def popup_patch(a):
    mid=27;base=a.A['body_records'][mid]['fields'][1];c=Code(a)
    capture=Code(a).local(0).ownprop('_result').store(base).local(0).ownprop('_data').store(base+2)
    c.local(base).jump(0x12,'done')
    c.local(base).prop('result').jump(0x12,'done')
    c.local(base).prop('success').op(0x27).jump(0x1a,'done')
    c.local(base).prop('protection').store(base+1);c.local(base+1).jump(0x12,'done')
    c.local(base+1).prop('material_kept').op(0x26).jump(0x1a,'done')
    c.local(base+2).jump(0x12,'done')
    c.local(base+2).prop('fo3RestorePair').jump(0x12,'done')
    c.local(base+2).prop('fo3PairRestored').jump(0x11,'done')
    c.local(base+2).op(0x26).set('fo3PairRestored')
    c.local(base+2).local(base+2).call('fo3RestorePair',1).op(0x29)
    c.label('done');a.modify(mid,{2:capture.done(),50:c.done()},locals_extra=3)
    return {}
