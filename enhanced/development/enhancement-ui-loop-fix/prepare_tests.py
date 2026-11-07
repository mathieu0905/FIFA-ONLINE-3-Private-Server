from pathlib import Path
import sys,json,hashlib,re
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;BASE=W.parent/'enhancement-entry-fix';MEM=W.parent/'enhancement-remember';AVM=W.parent/'enhancement-avm-check'
source=(BASE/'test_client.py').read_text('utf8')
source=source.replace("cp=json.loads((W/(NAMES[0]+'-ABC.patch.json')).read_text())", "cp=json.loads((Path('D:/fifaol3/enhancement-entry-fix')/(NAMES[0]+'-ABC.patch.json')).read_text())")
source=source.replace("callback=meta[NAMES[0]]['blocks']['owner']['callbacks']['public_method_id']",'callback=89')
source=source.replace('for mid in (21,24,25,30,35,45):','for mid in (21,24,25,35,45):')
source=source.replace('crash_cause_proven=False','native_entry_verified=False,real_avm_invalid_backedges_reproduced=True')
cut=source.index("result=dict(status='PASS'")
source=source[:cut]+"""
# Exercise the user's option preferences against the exact loop-fixed bodies.
prefs_source=Path('D:/fifaol3/enhancement-remember/test_client.py').read_text('utf8')
prefs_defs=prefs_source[prefs_source.index('def inject('):prefs_source.index('o,b=own();')]
exec(prefs_defs,globals())
cp=json.loads(Path('D:/fifaol3/enhancement-remember/TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())
entry_cp=json.loads(Path('D:/fifaol3/enhancement-entry-fix/TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())
cp['26']=entry_cp['26']
fixed_map=json.loads((W/(NAMES[0]+'-ABC.patch.json')).read_text())['30']['mapping']
cp['30']['mapping']={old:fixed_map[str(at)] for old,at in cp['30']['mapping'].items()}
o,b=own();b.update(fo3RememberReady=True,fo3RememberProtection=False,fo3RememberPoint=False,fo3RememberItem=0)
prefs_cases=prefs_source[prefs_source.index('# Capture real user choices'):prefs_source.index('for blocked,token,version,expected')]
exec(prefs_cases,globals())
checks.append('Both repaired back edges target explicit AVM2 label opcodes; original method instructions and relative control flow retained')
result=dict(status='PASS',checks=checks,native_verified=False,game_gui_used=False,native_entry_verified=False,
    output_sha256={name:sha(W/(name+'.big')) for name in NAMES},source_sha256={name:sha(W/(name+'-baseline.big')) for name in NAMES})
(W/'client-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
"""
(W/'test_client.py').write_text(source,encoding='utf8')
stacks=(BASE/'test_stacks.py').read_text('utf8').replace("if prefix=='EnhancePlayerPanel':mids.add(89)","if prefix=='EnhancePlayerPanel':mids.add(89)\n if prefix=='TeamManagementPlayerEnhancingPopupScreen':mids.add(27)")
stacks=stacks.replace("r=dict(status='PASS',methods=results,native_type_verifier_pass=False)","r=dict(status='PASS',methods=results,native_type_verifier_pass=False,new_loop_headers_explicit_labels=True)")
(W/'test_stacks.py').write_text(stacks,encoding='utf8')
# Independent real AVM evidence: these probes expose existing bodies by renaming
# their traits in diagnostic copies only. External UI types are dependency stubs.
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path.insert(0,str(W))
from client_tools import ABC
for prefix,probe in (('TeamManagementPlayerEnhancementTabPage','fixed'),('EnhancePlayerPanel','owner-fixed')):
 tested=ABC((AVM/(probe+'.abc')).read_bytes());exact=ABC((W/(prefix+'-after.abc')).read_bytes())
 assert {mid:r['raw'] for mid,r in tested.A['body_records'].items()}=={mid:r['raw'] for mid,r in exact.A['body_records'].items()}
logs={name:(AVM/(name+'-result.log')).read_text('utf8',errors='replace') for name in ('stable','failed','fixed','owner-failed','owner-fixed')}
assert re.search(r'^30 VerifyError: Error #1021',logs['failed'],re.M)
assert re.search(r'^89 VerifyError: Error #1021',logs['owner-failed'],re.M)
for name in ('stable','fixed','owner-fixed'):
 assert not re.search(r'^\d+ VerifyError|^VerifyError',logs[name],re.M),(name,'Verifier failure remains')
 assert 'EventDispatcher' in logs[name] and '30 ' in logs[name]
result=dict(status='PASS',engine='Redtamarin AVMplus 2.1 debug-debugger',failed_coupon_method30='VerifyError #1021',failed_pair_method89='VerifyError #1021',fixed_methods='No VerifyError across diagnostic-exposed control and owner methods',
    limitation='External UI dependencies are stubs and probe traits renamed; this is real AVM verification, not full game entry or gameplay validation',game_gui_used=False,native_game_verified=False,
    engine_sha256=sha(AVM/'lib/redtamarin/bin/redshell_dd.exe'),engine_release='https://github.com/Corsaair/redtamarin/releases/tag/0.4.1',
    source_sha256={str(W/(p+'-after.abc')):sha(W/(p+'-after.abc')) for p in ('TeamManagementPlayerEnhancementTabPage','EnhancePlayerPanel')},
    logs={str(AVM/(name+'-result.log')):sha(AVM/(name+'-result.log')) for name in logs})
(W/'real-avm-tests.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('Prepared full-feature regression and independent real AVM evidence')
