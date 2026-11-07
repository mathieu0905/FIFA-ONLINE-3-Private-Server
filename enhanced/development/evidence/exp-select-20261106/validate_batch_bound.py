from pathlib import Path
import sys,json
O=Path(__file__).parent;P=O/'batch-bound-v1'
W=Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work')
sys.path.insert(0,str(W/'experience_native_fix'))
s=Path('D:/FO3QA/xp_independent_native/strict_stack_scope.py').read_text().split("report={'status'")[0]
s=s.replace("Path('work/experience_native_fix/candidate/TeamManagementExpCapsuleScreen.swf')",repr(str(P/'page.swf'))).replace('source.read_bytes()', 'Path(source).read_bytes()')
s=s.replace('0x68,0x46,0x4f,0x4a','0x68,0x45,0x46,0x4f,0x4a').replace('elif op==0x55:pop=2*r.u30();push=1','elif op==0x56:pop=r.u30();push=1\n  elif op==0x55:pop=2*r.u30();push=1').replace('0xa3,0xaf,0xab','0xa3,0xaf,0xab,0x87')
ns={};exec(compile(s,'<bound CFG audit>','exec'),ns)
checks=[ns['verify'](m) for m in (5,6,10,11,15,18,32)]
assert not any(c['errors'] for c in checks),checks
(P/'cfg.json').write_text(json.dumps(checks,indent=2),'utf8')
s=Path('D:/FO3QA/experience30_release/plus-minus-preparation-v1/test_snapshot_bytecode.py').read_text('utf8')
s=s.replace("OUT=ROOT/'candidate-v3'",'OUT=Path('+repr(str(P))+')').replace("OUT/'TeamManagementExpCapsuleScreen.swf'","OUT/'page.swf'")
s=s.replace("VM=ns['VM'];", "VM=ns['VM'];\noriginal_get=VM.get\ndef get(self,obj,key):\n if key=='fo3BatchRefresh':return lambda *args:self.run(32,args)\n return original_get(self,obj,key)\nVM.get=get\n")
exec(compile(s,'<bound actual bytecode replay>','exec'),{'__file__':str(O/'validate_batch_bound.py')})
print('CFG and 15 quantity/submit checks passed')
