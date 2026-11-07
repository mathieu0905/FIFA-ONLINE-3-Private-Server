from pathlib import Path
import hashlib,json
import install
R=install.R;S=install.S
names=['tests.json','integrated-live-tests.json','transaction-tests.json']
assert all(json.loads((R/n).read_text('utf8'))['status']=='PASS' for n in names)
baseline=json.loads((R/'input/baseline.json').read_text('utf8'))
for p,h in json.loads((R/'prepared-v3/source-baseline.json').read_text('utf8')).items():
 if Path(p).is_relative_to(S) or Path(p).is_relative_to(install.C):baseline[p]=h
for p in (S/'tools/player_import').iterdir():
 if p.is_file():baseline[str(p)]=install.sha(p)
baseline[str(S/'tools/value_v11/selected-model.json.gz')]=install.sha(S/'tools/value_v11/selected-model.json.gz')
paths=[p for p in R.rglob('*') if p.is_file() and (p.parent==R or p.is_relative_to(R/'prepared-v3') or p.is_relative_to(R/'input')) and '__pycache__' not in p.parts and p.name not in ('reviewed-payloads.json','deferred-install.json') and not p.name.endswith('.log')]
paths+=[R.parent/'ai-opponent-progression/install.py']
review=dict(schema=1,cards=32,season=327,model_strategy='explicit built-in generic',rating='+1 LV1 85-92, Li Haoyan92',files={str(p):install.sha(p) for p in paths},formal_baseline=baseline)
(R/'reviewed-payloads.json').write_bytes(install.encoded(review));install.check_inputs()
assert len(install.payloads())==42
print(json.dumps(dict(status='FROZEN_PASS',payloads=42,regression_cases=sum(json.loads((R/n).read_text('utf8'))['case_count'] for n in names))))
