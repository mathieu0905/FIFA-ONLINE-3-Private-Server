from pathlib import Path
import sys,json
O=Path(__file__).parent
sys.path.insert(0,'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_native_fix')
from avm_patch import ABC,instructions
def missing(folder):
    a=ABC((O/folder/'page.swf').read_bytes()[0x11186:])
    return [(mid,at,t) for mid,code in a.A['body'].items() for at,_,_,targets in instructions(code) for t in targets or [] if t<=at and code[t]!=9]
bad=missing('entry-font-v4');good=missing('loop-label-v5')
assert bad==[(32,466,418)] and good==[],(bad,good)
r=dict(status='PASS',failed_native_artifact_rejected=bad,repaired_artifact_issues=good,coverage='Every backward branch in every method of the page ABC',native_pass=False)
(O/'loop-label-v5/loop-marker-regression.json').write_text(json.dumps(r,indent=2),'utf8');print(json.dumps(r))
