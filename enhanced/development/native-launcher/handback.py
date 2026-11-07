from pathlib import Path
import json,hashlib,datetime,importlib.util
O=Path(__file__).parent;S=Path('D:/FO3ID/server');p=S/'patches/native_launcher_preflight.py'
spec=importlib.util.spec_from_file_location('installed_native_gate',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
files=[p,S/'patches/native-launcher-installed.json',S/'patches/native-launcher-receipt.json',S/'play-local.bat',S/'launcher/FO3Control.exe',S/'launcher/fo3_control.py']
tx=json.loads((O/'install-result.json').read_text('utf8'))
r=dict(status='NATIVE_LAUNCHER_INSTALLED',observed_at=datetime.datetime.now().astimezone().isoformat(),top_preflight=str(p),top_manifest=str(files[1]),top_receipt=str(files[2]),files={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in files},composition_available=callable(m.compose_manifest),function_signatures={'preflight':'server=None, client=None','compose_manifest':'server=None, client=None'},preflight=m.preflight(),services_action='No service start/stop/restart executed during installation or verification',state_shop_written=False,asset_hashes_before=tx['asset_hashes_before'],asset_hashes_after=tx['asset_hashes_after'],GUI_status='No game or launcher GUI automation; exe check-only ran without displaying form',native_check_log=str(S/'captures/native-launcher-check.log'),native_verified=False,match_verified=False,locks_released=not(S/'.shop-release.lock').exists(),handoff=str(O/'handback.json'))
raw=json.dumps(r,ensure_ascii=False,indent=2);(O/'handback.json').write_text(raw,'utf8')
Path('D:/fifaol3/root-current-top.json').write_text(raw,'utf8');print(raw)
