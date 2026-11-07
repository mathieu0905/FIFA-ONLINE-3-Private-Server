from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;O=R/'screen-currency';S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
raw=(S/'play-local.bat').read_bytes();needle=b'patches\\moments_display_preflight.py';assert raw.count(needle)==1
(O/'payload/play-local.bat').write_bytes(raw.replace(needle,b'patches\\currency_screen_preflight.py'))
rows=[]
paths=[('server','play-local.bat','play-local.bat'),('server','patches/currency_screen_preflight.py','player_value_preflight.py')]
paths += [('client','data/ui/'+n,n) for n in ('MenuScreen.big','StartupCoachCreationScreen.big','StartupTest.big')]
for root,name,payload in paths:rows.append(dict(root=root,relative=name,payload=payload,parent_sha256=sha((S if root=='server' else C)/name),sha256=sha(O/'payload'/payload)))
m=dict(schema=1,release_id='20261106-currency-screen-comma-paths-v1',phase='CURRENCY_SCREEN_COMMA_PATHS',state_shop_replaced=False,client_root=str(C),files=rows,
    parent_files={n:sha(S/n) for n in ('patches/moments_display_preflight.py','patches/moments-display-release-manifest.json','patches/moments-display-release-installed.json')},
    reports={'build-test.json':sha(O/'build-test.json'),'gate-test.json':sha(O/'gate-test.json')})
(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'install.py').write_text((R/'install.py').read_text(encoding='utf-8').replace("status='INSTALLED_PLAYER_VALUE_DIV1000'","status='INSTALLED_CURRENCY_SCREEN'"),encoding='utf-8')
print(json.dumps(dict(status='BUILT',display_targets=3,prices_or_wallet_changed=False)))
