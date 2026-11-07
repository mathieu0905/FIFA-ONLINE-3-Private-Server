from pathlib import Path
import json
O=Path(__file__).parent
s=(O/'quantity_handback.py').read_text('utf8').replace('exp_quantity','exp_loop_label').replace('exp-quantity','exp-loop-label').replace('EXP_QUANTITY','EXP_LOOP_LABEL').replace('quantity-install-result','loop-label-install-result').replace('quantity-handback','loop-label-handback')
exec(compile(s,'<native loop marker installed handback>','exec'),{'__file__':str(__file__)})
for path in (O/'loop-label-handback.json',Path('D:/fifaol3/root-current-top.json')):
    r=json.loads(path.read_text('utf8'));r['native_fault_evidence']=str(O/'loop-label-v5/native-cause.json');r['identified_fault']='Callback32 backwards inventory branch target418 lacked AVM2 label; captured native tracer state is uninitialized at exact target'
    r['verification_scope']='Pre-install captured native failure identified; repaired native page entry/quantity/rendering pending user manual test'
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf8')
