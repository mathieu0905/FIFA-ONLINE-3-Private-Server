from pathlib import Path
import datetime,hashlib,json,re,sys,urllib.request
R=Path(__file__).resolve().parent;W=R.parent;S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795')
def read(p):return json.loads(p.read_text('utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf8')
top=W/'root-current-top.json';baseline=top.read_bytes();result=json.loads(baseline)
play=(S/'play-local.bat').read_bytes();relative='patches/'+re.findall(rb'patches\\(\w+_preflight\.py)',play)[0].decode()
assert str(S/relative)==result['top_preflight']
for p,digest in result['files'].items():assert sha(Path(p))==digest
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8088/api/hot_update_status',timeout=10) as response:hot=json.load(response)
assert hot['watcher_running'] and hot['error'] is None and hot['revision']=='shop_cleanup_20261107_01'
result.update(status='STARTUP_RECOVERED_USER_HOME_CONFIRMED',observed_at=datetime.datetime.now().astimezone().isoformat(),
    human_verification=dict(home=True,statement='可以进入主页了',match=False,all_players_rendered=False),
    services_restored=True,hot_update_status=hot,locks_released=not any((S/n).exists() for n in ('.shop-release.lock','.fo3-publish.lock')),
    retained=dict(ucl25_cards=360,registered_custom_cards=1776,native_player_rows=62513,households=True,card_attributes=True,real_assets=True),
    temporary_display_fallback=dict(new_25U_PlayerListUtil_delta_withdrawn=True,new_25U_badge_withdrawn=True,season_filter_label_and_all_team_names_preserved=True),
    root_cause_scope='Second recovery (old Label + stored TEAMNAMES JSON) restored boot. Exact separation of those two resource changes not proven. First name-only recovery did not resolve black screen.',
    formal_full_player_import='PASS; same database/data0/certificate as before both UI recovery layers',
    game_GUI_automated=False,game_force_closed=False,market_migration_evidence=str(R/'market-migration.json'),
    combined_install_evidence=str(W/'all-custom-households/combined-installed-handback.json'),handback=str(R/'installed-handback.json'))
write(R/'installed-handback.json',result)
if top.read_bytes()==baseline:write(top,result)
write(R/'work-status.json',dict(status=result['status'],formal_writer=False,handback=result['handback'],home_human_verified=True,match_verified=False))
print(json.dumps(dict(status=result['status'],locks_released=result['locks_released'],hot_revision=hot['revision'],triad={str(S/p):sha(S/p) for p in (relative,relative.replace('startup_resource_recovery_20261107_preflight.py','startup-resource-recovery-20261107-installed.json'),relative.replace('startup_resource_recovery_20261107_preflight.py','startup-resource-recovery-20261107-receipt.json'))})))
