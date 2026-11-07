"""Observe the actual current release and prepared resource without changing live files."""
from pathlib import Path
import hashlib, importlib.util, json, re, sys, urllib.request
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
SERVER=Path(r'D:\FO3ID\server')
CLIENT=Path(r'D:\FO3ID\32795')
sys.path.insert(0,str(ROOT))
import install

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

build=install.read(ROOT/'client/install-build.json')
tests=install.read(ROOT/'client/client-tests.json')
fonts=install.read(ROOT/'client/stacks-fonts.json')
assert tests['status']==fonts['status']=='PASS'
assert install.read(ROOT/'installer-tests.json')['status']=='PASS'
installed=(ROOT/'installed-handback.json').exists()
if not installed:
    install.check_payloads(build)
else:
    assert all(sha(CLIENT/r['relative'])==r['after'] for r in build['files'])
play=(SERVER/'play-local.bat').read_bytes()
matches=re.findall(rb'patches[\\/][A-Za-z0-9_]+_preflight\.py',play)
assert len(matches)==1 and b'tools\\player_import\\check.py' in play
helper=matches[0].decode().replace('\\','/')
parent=install.load(SERVER/helper,'dual_current_handback')
proof=parent.preflight(SERVER,CLIENT)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8088/api/hot_update_status',timeout=5) as response:
    hot=json.load(response)
assert hot['abi']==2 and hot['watcher_running'] and hot['error'] is None
assert '/item/{item_id}/use' in hot['routes']
game_running=False
try: install.closed()
except RuntimeError: game_running=True
locks=[p.name for p in SERVER.glob('.*lock') if p.name in ('.shop-release.lock','.fo3-publish.lock')]
assert not locks,'Another transaction now owns formal files; preserve it'
result=dict(status='FORMAL_INSTALLED_NATIVE_PENDING' if installed else 'BUILT_VERIFIED_NOT_INSTALLED',
            requested_modes=['单张开启','连续翻开','一键全开'],new_client_resource_installed=installed,
            game_running=game_running,preflight=proof,top_preflight=str(SERVER/helper),
            top_manifest=str(SERVER/parent.MANIFEST),top_receipt=str(SERVER/parent.RECEIPT),
            composition_api='compose_manifest(server=None,client=None)',
            files={str(SERVER/p):sha(SERVER/p) for p in (helper,parent.MANIFEST,parent.RECEIPT,'play-local.bat')},
            hot_status=hot,hot_business_written=False,state_shop_written=False,
            services_action='No service start/stop/restart',locks_held=False,automatic_installer_running=False,
            client_build=build,client_tests=tests,client_stack_font_status=fonts['status'],
            installer_game_guard='PASS',native_gui_verified=False,
            evidence=[str(ROOT/'client/client-tests.json'),str(ROOT/'client/stacks-fonts.json'),str(ROOT/'installer-tests.json')])
(ROOT/'handback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
