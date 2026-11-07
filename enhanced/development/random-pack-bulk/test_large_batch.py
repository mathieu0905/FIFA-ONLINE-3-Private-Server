"""Large result contract and full native resource serialization, disposable state only."""
from pathlib import Path
import json, time
root = Path(__file__).resolve().parent
namespace = {'__file__': str(root/'test_bulk.py'), '__name__': 'bulk_large_regression'}
source = (root/'test_bulk.py').read_text('utf8').split('\nrisk_ids = ')[0]
exec(compile(source, str(root/'test_bulk.py'), 'exec'), namespace)
h = namespace['h']
sample = next(int(i) for i, data in h.product_packs['risk_packs'].items()
              if data.get('mode') != 'choice' and h.item_def(int(i))['category'] == 'PLAYERPACK')
token = namespace['reset'](sample, 300, 1000)
h.coach_me_resources = namespace['original_resources']
started = time.monotonic()
out = namespace['call'](token, namespace['request'](300, 'bulk-large-batch-300'))
elapsed = time.monotonic() - started
assert out['result'] and out['opened'] == 300 and len(out['players']) == 300
assert out['remaining'] == 0 and out['playerCount'] == 300
assert len({row['_id'] for row in out['players']}) == 300
assert out['resources'] and namespace['saved_count'] == 1
replay = namespace['call'](token, namespace['request'](300, 'bulk-large-batch-300'))
assert replay['replayed'] and replay['players'] == out['players'] and namespace['saved_count'] == 1
report = dict(status='PASS', opened=300, complete_result_array=True, native_resources=True,
              one_commit=True, replay_without_additional_cards=True, elapsed_seconds=round(elapsed,3),
              real_state_written=False, native_gui_verified=False,
              source_sha256=namespace['hashlib'].sha256((root/'bulk_business.py').read_bytes()).hexdigest())
(root/'large-batch-tests.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
