from pathlib import Path
import json
import install as m
R=m.R
names=['tests.json','transaction-tests.json']
assert all(json.loads((R/n).read_text('utf8'))['status']=='PASS' for n in names)
paths=[p for p in R.iterdir() if p.is_file() and p.name not in ('reviewed-payloads.json','deferred-install.json')]
paths+=list((R/'native').glob('*.png'))+[R.parent/'china-future/install.py',R.parent/'ai-opponent-progression/install.py']
review=dict(schema=1,files={str(p):m.sha(p) for p in paths},photos=32,checks=sum(json.loads((R/n).read_text('utf8'))['case_count'] for n in names))
(R/'reviewed-payloads.json').write_bytes(m.encoded(review));m.check_inputs()
print(json.dumps(dict(status='REVIEW_FROZEN_PASS',photos=32,checks=review['checks'],game_running=m.d.game_running())))
