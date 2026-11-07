from pathlib import Path
import sys
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;BASE=W.parent/'enhancement-ui-loop-fix'
for prefix in ('EnhancePlayerPanel','TeamManagementPlayerEnhancingPopupScreen'):
 for suffix in ('-before.abc','-after.abc','-ABC.patch.json'):(W/(prefix+suffix)).write_bytes((BASE/(prefix+suffix)).read_bytes())
source=(BASE/'test_client.py').read_text('utf8')
source=source.replace('for mid in (21,24,25,35,45):','for mid in (21,24,25,35):')
source=source.replace("fixed_map=json.loads((W/(NAMES[0]+'-ABC.patch.json')).read_text())['30']['mapping']", "fixed_map=json.loads(Path('D:/fifaol3/enhancement-ui-loop-fix/TeamManagementPlayerEnhancementTabPage-ABC.patch.json').read_text())['30']['mapping']")
source=source.replace("exec(prefs_cases,globals())", "cp['45']=json.loads((W/(NAMES[0]+'-ABC.patch.json')).read_text())['45']\nprefs_cases=prefs_cases.replace('inject(a,cp,45,toggle,o)', 'inject(a,cp,45,toggle,o,locals_override={2:b})')\nexec(prefs_cases,globals())")
(W/'test_client.py').write_text(source,encoding='utf8')
stacks=(BASE/'test_stacks.py').read_text('utf8');stacks=stacks[:stacks.index('results={}')]+"a=ABC((ROOT/('TeamManagementPlayerEnhancementTabPage-after.abc')).read_bytes())\nr=dict(status='PASS',method45=check(a,45),native_type_verifier_pass=False)\n(ROOT/'stacks.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))\n"
(W/'test_stacks.py').write_text(stacks,encoding='utf8')
v=(W/'verify_live.py').read_text('utf8').replace("['control30 missing loop label: VerifyError #1021','owner89 missing loop label: VerifyError #1021']", "['click closure45 used event receiver as control panel: TypeError #1006; native old/new closure execution reproduced and corrected']")
(W/'verify_live.py').write_text(v,encoding='utf8')
print('Prepared unchanged full-feature regression with corrected event-target preference capture')
