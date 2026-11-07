from pathlib import Path
import json
import install
R=install.R;S=install.S
names=['tests.json','chain-tests.json','transaction-tests.json']
assert all(json.loads((R/n).read_text('utf8'))['status']=='PASS' for n in names)
assert (R/'high8-business.py').stat().st_size<=131072
paths=[p for p in R.iterdir() if p.is_file() and p.name not in ('reviewed-payloads.json',) and not p.name.endswith('.log')]
paths+=list((R/'icons').glob('*.png'))
paths += [R.parent/'china-future/install.py',R.parent/'ai-opponent-progression/install.py']
review=dict(schema=1,files={str(p):install.sha(p) for p in paths},baseline=json.loads((R/'baseline.json').read_text('utf8')),tests=names)
(R/'reviewed-payloads.json').write_bytes(install.encoded(review));install.check_inputs()
print(json.dumps(dict(status='FROZEN_PASS',payloads=len(install.payloads()),regressions=sum(json.loads((R/n).read_text('utf8'))['case_count'] for n in names),game_running=install.d.game_running())))
