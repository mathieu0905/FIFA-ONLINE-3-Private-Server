from pathlib import Path
import json,struct,sys
O=Path(__file__).parent
ns={'__file__':str(O/'decode_trace_state.py')};exec(compile((O/'decode_trace_state.py').read_text('utf8').replace('print(json.dumps(out,indent=2))',''),'<bounded captured trace decoding>','exec'),ns)
read,u,reg=ns['read'],ns['u'],ns['reg']
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
from avm_patch import ABC,instructions
a=ABC((O/'entry-font-v4/page.swf').read_bytes()[0x11186:]);code=a.A['body'][32]
assert reg['eip']==0x7917c3 and u(reg['ebx']+0x28)==0
assert u(reg['ebx']+0x30)==418 and u(reg['ebx']+0x34)==0
assert u(reg['edi']+0x24)==len(code)==1010
ptr=u(reg['edi']+0x20);n=128
assert read(ptr,n)==code[:n], 'Captured VM is not processing the installed callback32'
assert code[418]!=9 and any(at==466 and targets==[418] for at,_,_,targets in instructions(code))
r=dict(status='NATIVE_LOOP_ENTRY_FAULT_IDENTIFIED',native_exception='0xC0000005 at0x7917c3',callback=32,code_prefix_bytes_match=n,code_length=len(code),block_start=418,block_end=0,block_state_pointer=0,backwards_jump_from=466,target_opcode=hex(code[418]),required_loop_marker='label 0x09',conclusion='Captured native verifier processes exact callback32; backwards loop-entry block418 is uninitialized. Generated backwards target omits AVM2 label marker.',scope='Runtime evidence identifies this fault; repaired game page still requires manual native verification')
(O/'loop-label-v5/native-cause.json').write_text(json.dumps(r,indent=2),'utf8');print(json.dumps(r))
