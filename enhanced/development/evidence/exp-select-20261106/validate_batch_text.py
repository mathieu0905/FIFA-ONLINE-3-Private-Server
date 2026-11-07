from pathlib import Path
import sys,json
O=Path(__file__).parent
s=(O/'validate_batch_bound.py').read_text('utf8').replace("P=O/'batch-bound-v1'","P=O/'batch-text-v2'")
# The test itself invokes the shared calculation directly. UI events now use raw
# TextField click/mouseEnabled instead of timeline ButtonEvent/enabled.
s=s.replace("s=s.replace(\"OUT=ROOT/'candidate-v3'\"", "s=s.replace(\"get('enabled') for n in\",\"get('mouseEnabled') for n in\")\ns=s.replace(\"OUT=ROOT/'candidate-v3'\"")
anchor="exec(compile(s,'<bound actual bytecode replay>'"
s=s.replace(anchor,"s=s.replace(\"['fo3ExpPlus']['enabled']\",\"['fo3ExpPlus']['mouseEnabled']\")\n"+anchor)
exec(compile(s,'<TextField control CFG and quantity replay>','exec'),{'__file__':str(O/'validate_batch_text.py')})
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
from avm_patch import ABC,dis,R,instructions
a=ABC((O/'batch-text-v2/page.swf').read_bytes()[0x11186:])
constructs=[]
for at,_,op,_ in instructions(a.A['body'][5]):
    if op==0x4a:
        r=R(a.A['body'][5],at+1);constructs.append(a.A['mn'][r.u30()])
assert 'BlueAquaButton' not in constructs and constructs.count('TextField')==5,constructs
assert 'setproperty mouseEnabled' in '\n'.join(dis(a.A,a.A['body'][32]))
(O/'batch-text-v2/entry-controls.json').write_text(json.dumps(dict(status='TEXTFIELD_ENTRY_CONTROLS_STATIC_PASS_NATIVE_PENDING',configUI_constructs=constructs,new_timeline_skin_instances=0,events='TextField click and change; mouseEnabled for quantity controls',old_failure='User reported 2555 page-entry hang and subsequent CLIENT_CRASH; no experience-use POST observed',native_pass=False),indent=2),'utf8')
print('No dynamically constructed BlueAqua timelines; five native TextFields; native test still required')
