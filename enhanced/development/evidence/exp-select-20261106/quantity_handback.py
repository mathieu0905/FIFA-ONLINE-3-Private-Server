from pathlib import Path
import importlib.util,hashlib,json,datetime
O=Path(__file__).parent;S=Path('D:/FO3ID/server')
p=S/'patches/exp_quantity_preflight.py'
sp=importlib.util.spec_from_file_location('quantity_gate',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
verification=m.preflight()
files=[p,S/'patches/exp-quantity-installed.json',S/'patches/exp-quantity-receipt.json',S/'play-local.bat',Path('D:/FO3ID/32795/data/ui/TeamManagementExpCapsuleScreen.big')]
transaction=json.loads((O/'quantity-install-result.json').read_text('utf8'))
r=dict(status='EXP_QUANTITY_INSTALLED_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),top_preflight=str(p),top_manifest=str(files[1]),top_receipt=str(files[2]),files={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},composition_available=callable(m.compose_manifest),function_signatures={'preflight':'server=None, client=None','compose_manifest':'server=None, client=None'},preflight=verification,state_shop_written=False,asset_hashes_before=transaction['asset_hashes_before'],asset_hashes_after=transaction['asset_hashes_after'],services_action='No service stop/start/reload; existing services unchanged',GUI_status='User will manually test; no GUI operation or client launch',native_verified=False,match_verified=False,locks_released=not (S/'.shop-release.lock').exists(),handoff=str(O/'quantity-handback.json'))
raw=json.dumps(r,ensure_ascii=False,indent=2)
(O/'quantity-handback.json').write_text(raw,'utf8')
# Observer only; physical check above is evidence, not native success.
Path('D:/fifaol3/root-current-top.json').write_text(raw,'utf8')
print(raw)
