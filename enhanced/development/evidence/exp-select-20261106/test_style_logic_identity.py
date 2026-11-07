from pathlib import Path
import json,sys
O=Path(__file__).parent
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
from avm_patch import ABC,u30
old=ABC((O/'loop-label-v5/page.swf').read_bytes()[0x11186:]);new=ABC((O/'native-style-v6/page.swf').read_bytes()[0x11186:])
build=json.loads((O/'native-style-v6/build.json').read_text('utf8'))
for mid in (18,32):
    restored=bytearray(new.A['body'][mid])
    for at in build['enabled_only_operand_changes'][str(mid)]:restored[at+1:at+3]=u30(old.name('mouseEnabled'))
    assert restored==old.A['body'][mid],mid
for mid,rec in old.A['body_records'].items():
    if mid not in (5,18,32):assert rec['raw']==new.A['body_records'][mid]['raw']
r=dict(status='PASS',quantity_and_submit_bytecode='Byte-exact with known-working version after restoring only native-button enabled operands',other_method_records='Byte-exact except configUI visualization',user_confirmed_working_base='657e82a5e3af97869e85b4d0050e35a2717deda7e0c5f582b7be7d75bb77be04',visual_native_pending=True)
(O/'native-style-v6/logic-identity.json').write_text(json.dumps(r,indent=2),'utf8');print(json.dumps(r))
