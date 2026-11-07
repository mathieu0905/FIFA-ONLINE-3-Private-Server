from pathlib import Path
import json,hashlib,datetime
S=Path('D:/FO3ID/server');C=Path('D:/FO3ID/32795');O=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((O/'repair-result.json').read_text('utf8'))
b=json.loads((Path(r['backup'])/'state.json').read_text('utf8'));a=json.loads((S/'gamedata/state.json').read_text('utf8'))
result=dict(status='INSTALLED_NATIVE_SELECTION_PREVIEW_CANCEL_PASS',recorded_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),scope='Original native EXP page restored; broken batch controls removed; cap30 retained. Full batch feature remains unfinished.',backup=r['backup'],preflight=r['preflight'],parent='patches/player_database_preflight.py',API='compose_manifest(server=None,client=None); preflight(server=None,client=None)',triple=['patches/exp_selection_preflight.py','patches/exp-selection-installed.json','patches/exp-selection-receipt.json'],cases=[dict(itemid=94000003,stock=3,player='Bellingham',before_level=1,preview_level=3,preview_percent=66,checkbox=True,card=True,use_enabled=True),dict(itemid=94000003,stock=3,player='Yashin',before_level=2,preview_level=4,preview_percent=0,checkbox=True,card=True,use_enabled=True)],initialization_pass=True,cancel_return_to_inventory_pass=True,inventory500_after=3,final_use_clicked=False,actual_consumption_verified=False,cap30_HTTP_verified=True,changed_state_top_fields=[k for k in a if a.get(k)!=b.get(k)],coaches_equal=a['coaches']==b['coaches'],teams_equal=a['teams']==b['teams'],shop_equal=sha(S/'gamedata/shop.json')==r['asset_hashes_before']['shop.json'],services_restarted=False,game_pid=88700,GUI_released=True,production_writes_frozen_after_handoff=True)
paths=[S/p for p in result['triple']]+[S/'play-local.bat',C/'data/ui/TeamManagementExpCapsuleScreen.big',C/'data/ui/libs/Module.big',S/'experience_levels.py',S/'http_config.py']
result['hashes']={str(p):sha(p) for p in paths}
(O/'native-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(result,ensure_ascii=True,indent=2))
