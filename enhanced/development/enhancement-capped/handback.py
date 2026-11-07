"""Record an observation of the live entry without changing release metadata."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,re,subprocess,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
play=(S/'play-local.bat').read_bytes();match=re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py',play);assert len(match)==1
relative=match[0].decode().replace('\\','/')
spec=importlib.util.spec_from_file_location('observed_enhancement_parent',S/relative);parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
check=parent.preflight(S,Path('D:/FO3ID/32795'))
tests=json.loads((R/'tests.json').read_text('utf8'))
status=json.loads(subprocess.check_output([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'hot_update_control.py')],cwd=S,text=True))
assert (S/'play-local.bat').read_bytes()==play,'Entry changed during observation; retry'
result=dict(status='DEFERRED_GAME_RUNNING',observed_at=datetime.datetime.now().astimezone().isoformat(),
    formal_files_written=False,services_restarted=False,state_shop_written=False,
    top_preflight=str(S/relative),top_manifest=str(S/parent.MANIFEST),top_receipt=str(S/parent.RECEIPT),
    composition_api='compose_manifest(server=None,client=None)',
    hashes={str(p):sha(p) for p in (S/relative,S/parent.MANIFEST,S/parent.RECEIPT,S/'play-local.bat')},
    preflight=check,hot_status=status,development_tests=tests,
    activation='Pending a fresh locked install after game naturally closes; no background installer started',
    native_verified=False,match_verified=False)
(R/'handback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:result[k] for k in ('status','top_preflight','hot_status','formal_files_written','services_restarted')},ensure_ascii=True))
