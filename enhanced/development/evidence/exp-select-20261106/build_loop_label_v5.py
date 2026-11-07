"""Repair the backwards inventory branch rejected by the native single-pass tracer."""
from pathlib import Path
import sys,json,struct,zlib,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
import build_client as b
from avm_patch import ABC,instructions,dis
O=Path(__file__).parent;I=O/'entry-font-v4';D=O/'loop-label-v5';D.mkdir(exist_ok=True)
swf=(I/'page.swf').read_bytes();a=ABC(swf[0x11186:]);back={}
for mid,code in a.A['body'].items():
    missing=sorted({t for at,end,op,targets in instructions(code) for t in targets or [] if t<=at and code[t]!=0x09})
    if missing:back[mid]=missing
assert back=={32:[418]},back
a.modify(32,{418:b'\x09'});abc=a.output();check=ABC(abc)
for mid,rec in a.A['body_records'].items():
    if mid!=32:assert rec['raw']==check.A['body_records'][mid]['raw']
for code in check.A['body'].values():
    for at,end,op,targets in instructions(code):
        assert all(t>at or code[t]==9 for t in targets or [])
start=8+(5+4*(swf[8]>>3)+7)//8+4;parts=[];found=False
for kind,body,raw in b.tags(swf,start):
    if kind==82:
        pos=body.index(0,4)+1
        if swf.find(body)+pos==0x11186:raw=b.tag(kind,body[:pos]+abc);found=True
    parts.append(raw)
assert found
updated=bytearray(swf[:start]+b''.join(parts));struct.pack_into('<I',updated,4,len(updated));(D/'page.swf').write_bytes(updated)
target=D/'TeamManagementExpCapsuleScreen.big';target.write_bytes((I/target.name).read_bytes());b.ordered_big.replace_member(target,'data/ui/TeamManagementExpCapsuleScreen.gfx',b'CFX'+updated[3:8]+zlib.compress(updated[8:],9),0)
(D/'methods.json').write_text(json.dumps({str(mid):'\n'.join(dis(check.A,check.A['body'][mid])) for mid in (5,6,10,11,15,18,32)},ensure_ascii=False,indent=2),'utf8')
r=dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),previous_sha256=hashlib.sha256((I/target.name).read_bytes()).hexdigest(),only_changed_method=32,insertion_offset=418,instruction='label (0x09)',old_backward_jump=466,all_original_method_records_preserved=True,native_pass=False)
(D/'build.json').write_text(json.dumps(r,indent=2),'utf8');print(json.dumps(r))
