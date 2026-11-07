"""Guard quantity callbacks until all three controls exist, including early setup calls."""
from pathlib import Path
import sys,struct,zlib,json,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
import build_client as b
from avm_patch import ABC,Code,R,instructions
O=Path(__file__).parent;I=O/'batch-text-v2';D=O/'batch-text-v3';D.mkdir(exist_ok=True)
swf=(I/'page.swf').read_bytes();a=ABC(swf[0x11186:]);ins=list(instructions(a.A['body'][32]));point=None
for index,(at,end,op,_) in enumerate(ins):
    if op==0x63 and R(a.A['body'][32],at+1).u30()==3:
        assert ins[index+1][2]==0x62 and ins[index+2][2]==0x12
        point=ins[index+2][1];break
assert point is not None
c=Code(a)
for i,name in enumerate(('fo3ExpMinus','fo3ExpPlus','fo3ExpMax')):
    c.local(0).string(name).call('getChildByName',1).jump(0x11,'ready'+str(i)).op(0x47).label('ready'+str(i))
a.modify(32,{point:c.done()});abc=a.output();check=ABC(abc)
for mid,record in a.A['body_records'].items():
    if mid!=32:assert record['raw']==check.A['body_records'][mid]['raw']
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
(D/'methods.json').write_text(json.dumps({str(mid):'\n'.join(b.dis(check.A,check.A['body'][mid])) for mid in (5,6,10,11,15,18,32)},ensure_ascii=False,indent=2),'utf8')
print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),inserted_guard_offset=point,early_callback_safe=True,native_pass=False)))
