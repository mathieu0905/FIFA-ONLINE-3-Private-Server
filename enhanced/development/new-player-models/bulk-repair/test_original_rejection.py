import json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parent
r=subprocess.run([sys.executable,'-B',str(R/'tooling/check.py'),'--server','D:/FO3ID/server','--client','D:/FO3ID/32795','--imports',str(R/'built/player-imports.json'),'--full'],capture_output=True,text=True,encoding='utf8',errors='replace',env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'})
(R/'original-rejection.txt').write_text(r.stdout+r.stderr,encoding='utf8')
assert r.returncode==1 and 'Missing native player record 243715' in r.stderr and 'Expected 252 bones, got 255' in r.stderr,r.stderr
result=dict(status='PASS',original_official_inputs_rejected=True,missing_native_record_detected=True,unconverted_rig_detected=True,formal_written=False)
(R/'original-rejection.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
