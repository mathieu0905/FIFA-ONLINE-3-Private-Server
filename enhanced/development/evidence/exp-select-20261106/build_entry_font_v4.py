"""Remove selected-player font dependency from configUI, without changing layout or business code."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
import build_client as b
from avm_patch import ABC,Code,u30,dis
O=Path(__file__).parent;I=O/'batch-text-v3';D=O/'entry-font-v4';D.mkdir(exist_ok=True)
swf=(I/'page.swf').read_bytes();a=ABC(swf[0x11186:]);old=a.A['body'][5]
before=Code(a).local(5).local(0).ownprop('selectedPlayerInfo').prop('player').prop('playerLevelTextField').prop('defaultTextFormat').set('defaultTextFormat')
before.local(5).local(0).ownprop('selectedPlayerInfo').prop('player').prop('playerLevelTextField').prop('embedFonts').set('embedFonts')
needle=before.done();assert old.count(needle)==1;at=old.index(needle)
after=Code(a).local(5).op(0x5d,a.name('TextFormat','flash.text')).string('$NormalFont').number(14).number(0xffffff).op(0x4a,a.name('TextFormat','flash.text'),3).set('defaultTextFormat').done()
assert len(after)<=len(needle)
new=old[:at]+after+b'\x02'*(len(needle)-len(after))+old[at+len(needle):]
rec=a.A['body_records'][5];a.changed[5]=u30(5)+b''.join(u30(f) for f in rec['fields'])+u30(len(new))+new+rec['suffix']
abc=a.output();checked=ABC(abc)
assert not any('getproperty selectedPlayerInfo' in x for x in dis(checked.A,checked.A['body'][5]))
for mid,record in a.A['body_records'].items():
    if mid!=5:assert record['raw']==checked.A['body_records'][mid]['raw']
start=8+(5+4*(swf[8]>>3)+7)//8+4;parts=[];found=False
for kind,body,raw in b.tags(swf,start):
    if kind==82:
        pos=body.index(0,4)+1
        if swf.find(body)+pos==0x11186:raw=b.tag(kind,body[:pos]+abc);found=True
    parts.append(raw)
assert found
updated=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',updated,4,len(updated));(D/'page.swf').write_bytes(updated)
target=D/'TeamManagementExpCapsuleScreen.big';target.write_bytes((I/target.name).read_bytes())
b.ordered_big.replace_member(target,'data/ui/TeamManagementExpCapsuleScreen.gfx',b'CFX'+updated[3:8]+zlib.compress(updated[8:],9),0)
(D/'methods.json').write_text(json.dumps({str(mid):'\n'.join(dis(checked.A,checked.A['body'][mid])) for mid in (5,6,10,11,15,18,32)},ensure_ascii=False,indent=2),'utf8')
r=dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),changed_method=5,start=at,end=at+len(needle),previous_sha256=hashlib.sha256((I/target.name).read_bytes()).hexdigest(),native_pass=False,root_cause='Early dereference risk reproduced offline; exact native crash cause unproven')
(D/'build.json').write_text(json.dumps(r,indent=2),'utf8');print(json.dumps(r))
