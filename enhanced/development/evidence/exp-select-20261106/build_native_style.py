"""Rebuild only visual initialization on the user-confirmed working loop-label page."""
from pathlib import Path
import sys,json,struct,zlib,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
import build_client as b
from avm_patch import ABC,Code,R,u30,instructions,dis
O=Path(__file__).parent;I=O/'loop-label-v5';D=O/'native-style-v6';D.mkdir(exist_ok=True)
swf=(I/'page.swf').read_bytes();a=ABC(swf[0x11186:])
original=b.bigdir.read(Path('D:/FO3ID/server/backups/xp30-batch-module-20261106-145705-239491/6.backup'),'data/ui/TeamManagementExpCapsuleScreen.gfx');original=b'FWS'+original[3:8]+zlib.decompress(original[8:]);stock=ABC(original[0x11186:])
c=Code(a)
def xy(offset,y=0):
    c.local(5).local(0).ownprop('useButton').prop('x').local(0).ownprop('useButton').prop('width').number(2).op(0xa3).op(0xa0).number(abs(offset)).op(0xa1 if offset<0 else 0xa0).set('x')
    c.local(5).local(0).ownprop('useButton').prop('y').number(38-y).op(0xa1).set('y')
def text(name,value,width,x,input=False):
    mn=a.name('TextField','flash.text');c.op(0x5d,mn).op(0x4a,mn,0).store(5)
    c.local(5).string(name).set('name');c.local(5).number(width).set('width');c.local(5).number(26).set('height')
    for key in ('embedFonts','multiline','wordWrap'):c.local(5).op(0x27).set(key)
    c.local(5).op(0x5d,a.name('TextFormat','flash.text')).string('$LocalFont').number(14).number(0xffffff).op(0x4a,a.name('TextFormat','flash.text'),3).set('defaultTextFormat')
    if input:
        c.local(5).string('input').set('type');c.local(5).string('0-9').set('restrict');c.local(5).number(9).set('maxChars')
        c.local(5).op(0x26).set('border');c.local(5).op(0x26).set('background');c.local(5).number(0x141b25).set('backgroundColor');c.local(5).number(0x56616e).set('borderColor')
        c.local(5).prop('defaultTextFormat').store(6);c.local(6).string('center').set('align');c.local(5).local(6).set('defaultTextFormat')
    else:c.local(5).op(0x27).set('selectable')
    c.local(5).string(value).set('text');xy(x,1);c.local(0).local(5).call('addChild',1).op(0x29)
def listener(event):c.local(5).string(event).local(0).prop('fo3BatchRefresh').call('addEventListener',2).op(0x29)
def button(name,label,width,x):
    mn=a.name('BlueAquaButton');c.op(0x5d,mn).op(0x4a,mn,0).store(5)
    c.local(5).string(name).set('name');c.local(5).string(label).set('label');c.local(5).number(width).set('width');c.local(5).number(28).set('height')
    c.local(5).op(0x27).set('focusable');c.local(5).op(0x27).set('autoRepeat');c.local(5).op(0x27).set('enabled')
    xy(x);c.local(0).local(5).call('addChild',1).op(0x29);listener('buttonClick')
text('fo3ExpCaption','数量',44,-140);button('fo3ExpMinus','-',28,-88)
text('fo3ExpCount','1',64,-54,True);listener('change')
button('fo3ExpPlus','+',28,16);button('fo3ExpMax','最大',80,54)
end=max(at for at,_,op,_ in instructions(stock.A['body'][5]) if op==0x47)
# Original configUI prefix stays byte-exact; only the added visual block changes.
body=stock.A['body'][5][:end]+c.done()+stock.A['body'][5][end:]
rec=a.A['body_records'][5];fields=list(rec['fields']);fields[1]=max(fields[1],7)
a.changed[5]=u30(5)+b''.join(u30(x) for x in fields)+u30(len(body))+body+rec['suffix']
changes={}
for mid in (18,32):
    code=bytearray(a.A['body'][mid]);positions=[]
    for at,finish,op,targets in instructions(code):
        if op==0x61 and R(code,at+1).u30()==a.name('mouseEnabled'):
            value=u30(a.name('enabled'));assert len(value)==finish-at-1;code[at+1:finish]=value;positions.append(at)
    assert positions
    rec=a.A['body_records'][mid];a.changed[mid]=u30(mid)+b''.join(u30(x) for x in rec['fields'])+u30(len(code))+code+rec['suffix'];changes[mid]=positions
# Preserve the known-working status strings and arithmetic bytecode.
abc=a.output();check=ABC(abc)
for mid,rec in a.A['body_records'].items():
    if mid not in (5,18,32):assert rec['raw']==check.A['body_records'][mid]['raw']
assert check.A['body'][32][418]==9
start=8+(5+4*(swf[8]>>3)+7)//8+4;parts=[]
for kind,data,raw in b.tags(swf,start):
    if kind==82:
        pos=data.index(0,4)+1
        if swf.find(data)+pos==0x11186:raw=b.tag(kind,data[:pos]+abc)
    parts.append(raw)
updated=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',updated,4,len(updated));(D/'page.swf').write_bytes(updated)
target=D/'TeamManagementExpCapsuleScreen.big';target.write_bytes((I/target.name).read_bytes());b.ordered_big.replace_member(target,'data/ui/TeamManagementExpCapsuleScreen.gfx',b'CFX'+updated[3:8]+zlib.compress(updated[8:],9),0)
(D/'methods.json').write_text(json.dumps({str(mid):'\n'.join(dis(check.A,check.A['body'][mid])) for mid in (5,6,10,11,15,18,32)},ensure_ascii=False,indent=2),'utf8')
r=dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),changed_methods=[5,18,32],native_skin='Original linked BlueAquaButton',quantity_width=64,row_height=28,alignment='Centered above original useButton, consistent6-8px gaps',events='CLIK buttonClick for native buttons; TextField change for count',enabled_only_operand_changes=changes,working_loop_label_retained=True,native_visual_verified=False,prior_working_page_user_confirmed=True)
(D/'build.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf8');print(json.dumps(r))
