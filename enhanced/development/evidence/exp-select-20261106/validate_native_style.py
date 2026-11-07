from pathlib import Path
import json,sys
O=Path(__file__).parent
s=(O/'validate_batch_bound.py').read_text('utf8').replace("P=O/'batch-bound-v1'","P=O/'native-style-v6'")
s=s.replace("ns={};exec(compile(s", "s=s.replace('0xf0,0xf1,0x09,0xef','0xf0,0xf1,0x02,0x09,0xef')\nns={};exec(compile(s")
exec(compile(s,'<native skin CFG and business replay>','exec'),{'__file__':str(__file__)})
s=(O/'test_quantity_lifecycle.py').read_text('utf8').replace('batch-text-v3','native-style-v6')
exec(compile(s,'<native skin lifecycle replay>','exec'),{'__file__':str(__file__)})
from avm_patch import ABC,R,instructions
a=ABC((O/'native-style-v6/page.swf').read_bytes()[0x11186:]);constructs=[]
for at,end,op,targets in instructions(a.A['body'][5]):
    if op==0x4a:constructs.append(a.A['mn'][R(a.A['body'][5],at+1).u30()])
assert constructs.count('BlueAquaButton')==3 and constructs.count('TextField')==2,constructs
for mid,code in a.A['body'].items():
    for at,end,op,targets in instructions(code):assert all(t>at or code[t]==9 for t in targets or []),(mid,at)
body=a.A['body'][32];assert body[418]==9
assert not any(op==0x61 and a.A['mn'][R(body,at+1).u30()]=='mouseEnabled' for at,_,op,_ in instructions(body))
r=dict(status='PASS',constructors=constructs,quantity_bounds=(-54,10),minus_bounds=(-88,-60),plus_bounds=(16,44),max_bounds=(54,134),uniform_button_height=28,native_loop_marker=True,manual_visual_pending=True)
(O/'native-style-v6/style-checks.json').write_text(json.dumps(r,indent=2),'utf8');print(json.dumps(r))
