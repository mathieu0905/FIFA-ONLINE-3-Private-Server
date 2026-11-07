from pathlib import Path
import json,sys
sys.dont_write_bytecode=True
import install as d
p=d.plan()
assert p['prior']['files']>=5940
source=p['payloads'][d.SELF].decode()
assert 'store.verify_seed(' in source and 'receipt_policies' in source
assert p['payloads']['play-local.bat'].count(b'tools\\player_import\\check.py')==1
assert p['before']['enhancement_protection40.py']==(d.R/'enhancement_protection40.before.py').read_bytes()
# Code outside the read-only preview change must be exact, including execution.
before=p['before']['enhancement_protection40.py'].decode('utf8')
after=p['payloads']['enhancement_protection40.py'].decode('utf8')
marker='    @functools.wraps(old_enhance)'
assert before[before.index(marker):]==after[after.index(marker):]
c=json.loads(p['payloads'][d.MANIFEST])['composition']
result=dict(status='PASS',parent=p['parent'],parent_preflight=p['prior'],planned_files=list(p['payloads']),
 guard_count=len(c['guards']),receipt_policy_count=len(c['receipt_policies']),seed_validation_inherited=True,
 independent_player_import_check_preserved=True,execution_code_exact=True,formal_files_written=False,
 activation='DEFERRED_WHILE_GAME_RUNNING',planned_hashes={r:d.digest(b) for r,b in p['payloads'].items()})
(d.R/'plan-check.json').write_bytes(d.encoded(result));print(json.dumps(result))
