from pathlib import Path
import json
from avm_patch import Code,instructions
W=Path(__file__).parent
OLD=Path(r'D:\fifaol3\probability-number-box')
NAME='fo3EnhanceProbability';BOX='fo3ProtectionCheckbox';PLATE='fo3ProbabilityPlate';MARK='fo3ProtectionMark'

def checkbox(c,owner):
    owner(c);c.string(BOX).call('getChildByName',1)

def render(a,base,popup=False,waiting=False,empty=False):
    c=Code(a)
    if popup:
        c.local(0).ownprop('boostInfoPanel').store(base);c.local(base).jump(0x12,'done')
        c.local(base).prop('boostInfoContainer').store(base);c.local(base).jump(0x12,'done')
        c.local(base).prop('boostRate').store(base)
    else:
        c.local(0).ownprop('_owner').store(base);c.local(base).jump(0x12,'done')
        c.local(base).prop('infoPanel').store(base);c.local(base).jump(0x12,'done')
        c.local(base).prop('enhanceRate').store(base)
    c.local(base).jump(0x12,'done')
    c.local(base).string('__id15_' if popup else '__id7_').call('getChildByName',1).store(base+5)
    c.local(base+5).jump(0x12,'title_done');c.local(base+5).string('成功率').set('text');c.label('title_done')
    c.local(base).prop('rateContainer').store(base+5);c.local(base+5).jump(0x12,'done')
    c.local(base+5).op(0x27).set('visible')
    if popup:c.local(1).prop('info')
    elif empty:c.op(0x20)
    else:c.local(0).ownprop('_preview')
    c.store(base+1)
    # A rounded plate follows the original icon panel's exact geometry.
    c.local(base).string(PLATE).call('getChildByName',1).store(base+3)
    c.local(base+3).jump(0x11,'plate_exists')
    c.op(0x5d,a.name('Sprite','flash.display')).op(0x4a,a.name('Sprite','flash.display'),0).store(base+3)
    c.local(base+3).string(PLATE).set('name')
    for key in ('mouseEnabled','mouseChildren'):c.local(base+3).op(0x27).set(key)
    c.local(base).local(base+3).call('addChild',1).op(0x29)
    c.label('plate_exists')
    for key in ('x','y'):c.local(base+3).local(base+5).prop(key).set(key)
    c.local(base+3).prop('graphics').call('clear',0).op(0x29)
    c.local(base+3).prop('graphics').number(1).number(0x263d48).number(1).call('lineStyle',3).op(0x29)
    c.local(base+3).prop('graphics').number(0x10212b).number(1).call('beginFill',2).op(0x29)
    c.local(base+3).prop('graphics').number(0).number(0).local(base+5).prop('width').local(base+5).prop('height').number(14).number(14).call('drawRoundRect',6).op(0x29)
    c.local(base+3).prop('graphics').call('endFill',0).op(0x29)
    c.local(base).string(NAME).call('getChildByName',1).op(0x80,a.name('TextField','flash.text')).store(base+2)
    c.local(base+2).jump(0x11,'have_field')
    c.op(0x5d,a.name('TextField','flash.text')).op(0x4a,a.name('TextField','flash.text'),0).store(base+2)
    c.local(base+2).string(NAME).set('name')
    for key in ('selectable','mouseEnabled','multiline','wordWrap','border','background'):c.local(base+2).op(0x27).set(key)
    c.local(base+2).op(0x26).set('embedFonts')
    c.op(0x5d,a.name('TextFormat','flash.text')).string('$NormalFont').number(42 if popup else 32).number(0xf2c200).op(0x4a,a.name('TextFormat','flash.text'),3).store(base+4)
    c.local(base+4).string('center').set('align');c.local(base+2).local(base+4).set('defaultTextFormat')
    c.local(base).local(base+2).call('addChild',1).op(0x29)
    c.label('have_field')
    height=64 if popup else 46
    c.local(base+2).local(base+5).prop('x').set('x')
    c.local(base+2).local(base+5).prop('y').local(base+5).prop('height').number(height).op(0xa1).number(2).op(0xa3).op(0xa0).set('y')
    c.local(base+2).local(base+5).prop('width').set('width');c.local(base+2).number(height).set('height')
    c.string('...' if waiting else '-').store(base+3)
    c.local(base+1).jump(0x12,'set_text');c.local(base+1).prop('probability').store(base+4)
    c.local(base+4).op(0x95).string('number').jump(0x14,'set_text')
    c.op(0x5d,a.name('isFinite')).local(base+4).call('isFinite',1).jump(0x12,'set_text')
    c.local(base+4).number(0).op(0xad).jump(0x11,'set_text');c.local(base+4).number(100).op(0xaf).jump(0x11,'set_text')
    c.local(base+4).call('toString',0).string('%').op(0xa0).store(base+3)
    c.label('set_text').local(base+2).local(base+3).set('text');c.local(base+2).op(0x26).set('visible')
    c.label('done');return c.done()

def reset_checkbox(a,base,changed_pair=False):
    c=Code(a)
    if changed_pair:c.local(1).jump(0x12,'reset_done')
    checkbox(c,lambda c:c.local(0));c.store(base)
    c.local(base).jump(0x12,'reset_done');c.local(base).op(0x27).set('selected');c.label('reset_done')
    c.local(base).jump(0x12,'reset_mark_done');c.local(base).string(MARK).call('getChildByName',1).store(base)
    c.local(base).jump(0x12,'reset_mark_done');c.local(base).op(0x27).set('visible');c.label('reset_mark_done')
    return c.done()

def control_patch(a):
    previous=json.loads((OLD/'TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())
    # Replace only the already-added numeric rendering, retaining original logic.
    for mid,at in ((32,7),(35,119),(18,7),(25,7)):
        a.A['body'][mid]=bytes.fromhex(previous[str(mid)]['original'])
        base=a.A['body_records'][mid]['fields'][1]
        code=(reset_checkbox(a,base+5,mid==25) if mid in (18,25) else b'')+render(a,base,waiting=mid==35,empty=mid!=32)
        a.modify(mid,{at:code},locals_extra=6)
    # Compact checkbox uses vector strokes and the same registered client font.
    callback=len(a.A['meth'])
    c=Code(a).local(0).op(0x30);c.find('_available').ownprop('_available').jump(0x12,'done')
    c.local(1).prop('currentTarget').store(2);c.local(2).prop('enabled').jump(0x12,'done')
    c.local(2).local(2).prop('selected').op(0x96).set('selected')
    c.local(2).string(MARK).call('getChildByName',1).store(3)
    c.local(3).local(2).prop('selected').set('visible')
    c.find('requestPreview').owncall('requestPreview',0).op(0x29);c.label('done').op(0x47)
    assert a.add_method(c.done(),a.A['body_records'][8]['fields'][3],local_count=4)==callback
    mid=8;base=a.A['body_records'][mid]['fields'][1]
    c=Code(a);checkbox(c,lambda c:c.local(0));c.jump(0x11,'created')
    c.op(0x5d,a.name('MovieClip','flash.display')).op(0x4a,a.name('MovieClip','flash.display'),0).store(base)
    c.local(base).string(BOX).set('name')
    for key,value in [('x',30),('y',50)]:c.local(base).number(value).set(key)
    c.local(base).op(0x26).set('buttonMode');c.local(base).op(0x27).set('mouseChildren')
    c.local(base).prop('graphics').number(0).number(0).call('beginFill',2).op(0x29)
    c.local(base).prop('graphics').number(0).number(0).number(380).number(24).call('drawRect',4).op(0x29)
    c.local(base).prop('graphics').call('endFill',0).op(0x29)
    c.local(base).prop('graphics').number(1).number(0x607884).number(1).call('lineStyle',3).op(0x29)
    c.local(base).prop('graphics').number(0x132833).number(1).call('beginFill',2).op(0x29)
    c.local(base).prop('graphics').number(0).number(3).number(18).number(18).number(3).number(3).call('drawRoundRect',6).op(0x29)
    c.local(base).prop('graphics').call('endFill',0).op(0x29)
    c.op(0x5d,a.name('Sprite','flash.display')).op(0x4a,a.name('Sprite','flash.display'),0).store(base+1)
    c.local(base+1).string(MARK).set('name');c.local(base+1).op(0x27).set('visible')
    c.local(base+1).prop('graphics').number(2).number(0xf2c200).number(1).call('lineStyle',3).op(0x29)
    for method,x,y in [('moveTo',4,11),('lineTo',8,15),('lineTo',15,6)]:c.local(base+1).prop('graphics').number(x).number(y).call(method,2).op(0x29)
    c.local(base).local(base+1).call('addChild',1).op(0x29)
    c.op(0x5d,a.name('TextField','flash.text')).op(0x4a,a.name('TextField','flash.text'),0).store(base+1)
    c.local(base+1).string('fo3ProtectionCaption').set('name')
    for key,value in [('x',28),('y',0),('width',352),('height',24)]:c.local(base+1).number(value).set(key)
    for key in ('mouseEnabled','selectable'):c.local(base+1).op(0x27).set(key)
    c.local(base+1).op(0x26).set('embedFonts')
    c.local(base+1).op(0x5d,a.name('TextFormat','flash.text')).string('$NormalFont').number(16).number(0xaebdc5).op(0x4a,a.name('TextFormat','flash.text'),3).set('defaultTextFormat')
    c.local(base+1).string('强化保护（身价40%，失败保级）').set('text');c.local(base).local(base+1).call('addChild',1).op(0x29)
    for key in ('selected','enabled'):c.local(base).op(0x27).set(key)
    c.local(base).op(0x26).set('visible')
    c.local(base).string('click').op(0x40,callback).call('addEventListener',2).op(0x29)
    c.local(0).local(base).call('addChild',1).op(0x29);c.label('created')
    a.modify(mid,{len(a.A['body'][mid])-1:c.done()},locals_extra=2)
    mid=26;base=a.A['body_records'][mid]['fields'][1]
    c=Code(a);checkbox(c,lambda c:c.local(0));c.store(base);c.local(base).jump(0x12,'done')
    c.local(base).local(0).ownprop('_available').set('enabled');c.label('done')
    a.modify(mid,{len(a.A['body'][mid])-1:c.done()},locals_extra=1)
    mid=38;base=a.A['body_records'][mid]['fields'][1]
    returns=[at for at,end,op,t in instructions(a.A['body'][mid]) if op==0x48];assert len(returns)==1
    c=Code(a).store(base);checkbox(c,lambda c:c.local(0));c.store(base+1)
    c.local(base+1).jump(0x12,'done');c.local(base+1).prop('selected').jump(0x12,'done')
    c.local(base).string('?protection=1').op(0xa0).store(base);c.label('done').local(base)
    a.modify(mid,{returns[0]:c.done()},locals_extra=2)
    # Ignore responses from a previous checkbox/item/point/pair selection.
    mid=34;late=a.A['mn'].index('[late]')
    def scoped(c,name):
        ids=[i for i,n in enumerate(a.A['mn']) if n==name and a.values[6][i][0]==7]
        assert len(ids)==1;(c.op(0x5d,ids[0]).op(0x66,ids[0]));return c
    c=Code(a);c.find('_available').ownprop('_available').jump(0x12,'stale')
    for key,index in [('first',0),('second',1)]:
        c.find('_selectedTargets').ownprop('_selectedTargets').number(index).op(0x66,late);scoped(c,key);c.jump(0x1a,'stale')
    c.find('generatePreviewURI');scoped(c,'first');scoped(c,'second');c.owncall('generatePreviewURI',2);scoped(c,'previewUri');c.jump(0x19,'current')
    c.label('stale').op(0x47);c.label('current')
    a.modify(mid,{0:c.done()})
    return dict(toggle_callback=callback)

def popup_patch(a):
    mid=25;row=json.loads((OLD/'TeamManagementPlayerEnhancingPopupScreen-ABC.patch.json').read_text())[str(mid)]
    a.A['body'][mid]=bytes.fromhex(row['original']);base=a.A['body_records'][mid]['fields'][1]
    c=Code(a).local(1).jump(0x12,'skip');c.local(1).prop('cmd').string('setData').jump(0x14,'skip')
    c.raw(render(a,base,popup=True));c.label('skip')
    a.modify(mid,{len(a.A['body'][mid])-1:c.done()},locals_extra=6)
    return {}
