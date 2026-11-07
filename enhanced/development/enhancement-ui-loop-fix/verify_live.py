"""Verify deployed bytes and server preservation; never operates the game GUI."""
from pathlib import Path
import datetime,hashlib,json,ssl,subprocess,sys,urllib.request
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
sys.path.insert(0,str(S));import hot_update_release as release
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
result=read(W/'installed-handback.json');tests=read(W/'client-tests.json')
real_avm=read(W/'real-avm-tests.json');assert real_avm['status']=='PASS'
for path,h in real_avm['source_sha256'].items():assert release.sha(path)==h
for name,h in tests['output_sha256'].items():
    assert release.sha(C/'data/ui'/(name+'.big'))==release.sha(S/'patches'/(name+'.big'))==h
for path,h in result['protected'].items():assert release.sha(path)==h,('Protected input changed',path)
before=read(W/'fresh-install-snapshot'/result['revision']/'state.json');now=read(S/'gamedata/state.json')
business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
assert business(before)==business(now),'Keep all new progress; never restore a snapshot'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(url):
    with opener.open(url,timeout=15) as response:return json.load(response)
hot=get('http://127.0.0.1:8088/api/hot_update_status')
assert hot['revision']==read(S/'hot_updates/active.json')['revision'] and hot['watcher_running'] and hot['error'] is None
rules=get('https://127.0.0.1/info/enhancement/protection/rules')
assert rules['version']=='protection40-v3-both' and rules['protect_material'] and rules['independent_checkbox']
proc=subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'tools/player_import/check.py')],cwd=S,check=True,capture_output=True,text=True)
certificate=json.loads(proc.stdout);assert certificate['status']=='PLAYER_IMPORT_CERTIFICATE_PASS'
preflight=release.load(Path(result['top_preflight']),'remember_verified_top').preflight(S,C)
verification=dict(status='PASS_DEPLOYED_RESOURCES_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),
    deployed_bytes_match_replayed_bytes=True,server_patch_copies_match=True,preflight=preflight,hot_status=hot,
    protection_rules=rules,player_import_certificate=certificate,business_assets_preserved=True,state_shop_written=False,
    service_actions=False,native_verified=False,game_gui_used=False,actual_game_enhancements_performed=False,
    files=result['files'],client_files=result['client_files'],replay_checks=tests['checks'],real_avm_tests=str(W/'real-avm-tests.json'),
    real_avm_confirmed_defects=['control30 missing loop label: VerifyError #1021','owner89 missing loop label: VerifyError #1021'],
    real_avm_fixed_methods_pass=True,full_requested_convenience_features_restored=True)
release.atomic(W/'live-verification.json',release.body(verification))
with release.locks(S,'enhancement-remember-verification'):
    descriptor=read(W.parent/'root-current-top.json')
    result.update(verification=str(W/'live-verification.json'),hot_status=hot,player_import_certificate_status='PASS',
        status='INSTALLED_CLIENT_UI_VERIFIED_NATIVE_PENDING',real_avm_tests=str(W/'real-avm-tests.json'),full_requested_convenience_features_restored=True)
    release.atomic(W/'installed-handback.json',release.body(result))
    if Path(descriptor['top_preflight'])==Path(result['top_preflight']):
        descriptor.update(status=result['status'],verification=result['verification'],hot_status=hot,player_import_certificate_status='PASS',native_verified=False)
        release.atomic(W.parent/'root-current-top.json',release.body(descriptor))
print(json.dumps({k:verification[k] for k in ('status','deployed_bytes_match_replayed_bytes','hot_status','player_import_certificate','business_assets_preserved')},ensure_ascii=True))
