"""Replay early callbacks against actual method32; never touches production."""
from pathlib import Path
import json,copy
O=Path(__file__).parent;P=O/'batch-text-v3'
source=Path('D:/FO3QA/experience30_release/plus-minus-preparation-v1/test_snapshot_bytecode.py').read_text('utf8').split('tests=[]')[0]
source=source.replace("OUT=ROOT/'candidate-v3'",'OUT=Path('+repr(str(P))+')').replace("OUT/'TeamManagementExpCapsuleScreen.swf'","OUT/'page.swf'")
scope={'__file__':str(__file__)}
exec(compile(source,'<quantity lifecycle replay definitions>','exec'),scope)
scene,VM,a=scope['scene'],scope['VM'],scope['a']
tests=[]
for missing in ('fo3ExpCount','fo3ExpMinus','fo3ExpPlus','fo3ExpMax'):
    owner,fields,globals,calls=scene()
    del fields[missing]
    before=copy.deepcopy(owner['_capsuleData'])
    VM(a,owner,globals).run(32,(None,))
    assert owner['_capsuleData']==before and not calls and 'previews' not in owner
    assert not owner['_playerUpdateLocked']
    tests.append('early refresh with absent '+missing+' returns without preview, snapshot mutation or RPC')
report=dict(status='EARLY_CALLBACK_BYTECODE_REPLAY_PASS',tests=tests,native_pass=False,production_writes=False)
(P/'lifecycle-results.json').write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps(report))
