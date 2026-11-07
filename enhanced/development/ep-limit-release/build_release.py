from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
rows=[]
for relative in ('admin.py','admin_grant_guard.py','admin/index.html','http_config.py','market_simulation.py'):
    payload=relative.replace('/','-');shutil.copyfile(ROOT/'server'/relative,ROOT/'payload'/payload)
    rows.append(dict(root='server',relative=relative,payload=payload,parent_sha256=sha(S/relative),sha256=sha(ROOT/'payload'/payload)))
play=(S/'play-local.bat').read_bytes();needle=b'patches\\console_backpressure_preflight.py';assert play.count(needle)==1
play=play.replace(needle,b'patches\\player_value_preflight.py');(ROOT/'payload/play-local.bat').write_bytes(play)
for root,relative,payload in [('server','play-local.bat','play-local.bat'),
        ('server','patches/player_value_preflight.py','player_value_preflight.py'),
        ('server','patches/Label.big','Label.big'),
        ('client','data/ui/components/Label.big','Label.big')]:
    rows.append(dict(root=root,relative=relative,payload=payload,parent_sha256=sha((S if root=='server' else C)/relative),sha256=sha(ROOT/'payload'/payload)))
m=dict(schema=1,release_id='20261106-player-value-div1000-ep18-compact-v1',phase='PLAYER_VALUE_DIV1000_EP_ADMIN_COMPACT',
       client_root=str(C),state_shop_replaced=False,player_value_divisor=1000,balance_scaled=False,
       shop_prices_changed=False,enhancement_fees_changed=False,ep_admin_limit=10**18,
       parent_files={n:sha(S/n) for n in ('patches/console_backpressure_preflight.py','patches/console-backpressure-release-manifest.json','patches/console-backpressure-release-installed.json')},files=rows,
       test_reports={n:sha(ROOT/n) for n in ('test-result.json','admin-test-result.json','native/compact-label-build.json','native/compact-label-test.json','install-test-result.json')})
(ROOT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status='BUILT',targets=len(rows),manifest_sha256=sha(ROOT/'manifest.json')),indent=2))
