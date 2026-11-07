"""Prove a running-game rejection cannot enter payload checks or formal locks."""
from pathlib import Path
import importlib.util, json, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dual_installer_guard',ROOT/'install.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
calls=[]
def reject():
    raise RuntimeError('更新已延后，当前游戏继续运行')
module.closed=reject
module.check_payloads=lambda build:calls.append('payload')
module.locks=lambda *args:calls.append('lock')
try:
    module.install(None)
    raise AssertionError('Expected running-game deferral')
except RuntimeError as exc:
    assert str(exc)=='更新已延后，当前游戏继续运行'
assert not calls
report=dict(status='PASS',game_gate_before_locks_and_formal_writes=True,service_actions=False)
(ROOT/'installer-tests.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
