from pathlib import Path
import datetime,hashlib,json
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
installation=json.loads((R/'installed-result.json').read_text(encoding='utf8'))
backup=Path(installation['backup'])
before=json.loads((backup/'evidence/gamedata/state.json').read_text(encoding='utf8'))
after=json.loads((S/'gamedata/state.json').read_text(encoding='utf8'))
assert before['coaches']==after['coaches'] and before['teams']==after['teams']
files={str(S/name):sha(S/name) for name in ('patches/product_packs_preflight.py','patches/product-packs-release-manifest.json','patches/product-packs-release-installed.json','play-local.bat','http_config.py','admin.py','admin/index.html','product_packs.py','pack_catalogue.py','pack_probability.py','gamedata/product_packs.json')}
value=dict(status='PRODUCT_PACKS_INSTALLED_LIVE_PROTOCOL_PASS_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),
 top_preflight=str(S/'patches/product_packs_preflight.py'),top_manifest=str(S/'patches/product-packs-release-manifest.json'),top_receipt=str(S/'patches/product-packs-release-installed.json'),files=files,
 API={'compose_manifest':'compose_manifest(server=None,client=None) returns dict','_compose':'_compose(server,client,m=None,installed=True) returns (composed,validator)','preflight':'preflight(server=None,client=None) verifies final physical payload'},
 services={'HTTPS_443_admin_8088_PID':90172,'messenger_28002_PID':85756,'start_all_PID':85208},
 protection={'coaches_and_teams_exactly_equal_install_snapshot':True,'players':sum(len(t.get('players',[])) for t in after['teams'].values()),'state_shop_restored':False,'purchases':0,'grants':0},
 evidence={'installation':str(R/'installed-result.json'),'live_protocol':str(R/'live-results.json'),'isolated_checks':str(R/'test-results.json'),'probability_checks':str(R/'probability-test-results.json'),'IO_checks':str(R/'install-test-results.json')},
 GUI={'game_closed':True,'game_restarted':False,'formal_admin_readonly_verified':True,'native_new_store_render':'PENDING_MODEL_WINDOW_HANDOFF'},
 next_scope='User just requested stronger chains; prepare additive new SKU/root release offline, do not rewrite this issued config.')
(R/'installed-handback.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
Path(r'D:\fifaol3\root-current-top.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
doc=S/'docs/工程经验与修改边界.txt'
with doc.open('a',encoding='utf8') as f:f.write('\nFO3-005 续（2026-11-06，独立次数与高强正式同步）：independent-product-packs-v1已接入player_editor_current最新父层，1179完整物理guard PASS。停售原54个+1商品并上架42个+6～+11随机、12个固定+8自选，附2冒险包/3多包礼包、两条10轮连锁；所有购买次数按SKU独立，旧计数/旧卡池/旧库存权益保留。新增min/max与six-anchor-v1概率编辑，默认30/28/25/10/6/1，手调须合计100%，预览和抽取共用公式，已发行概率锁定。新池过滤retired_cards，旧库存不改。37项隔离交易与连锁检查、10项概率检查、PowerShell5.1隔离安装回滚/幂等与1179guards通过；正式HTTP10项/181商品及8088表单视觉核对通过，无正式购买/发放。原127卡、经理、余额、阵容与安装前快照一致，主服务443/8088/28002恢复。证据D:\\fifaol3\\pack_limits\\v2\\installed-handback.json；失败样本test-release.log（调试转储timer时隔离Python异常，移除timer后37项通过），旧共享限购候选已废弃不可安装。完整回归命令：正式.venv\\Scripts\\python.exe patches\\product_packs_preflight.py；只读HTTP：python D:\\fifaol3\\pack_limits\\v2\\verify_live.py。新商城native显示/真实自选操作仍待后续独占游戏窗口，不把协议或后台视觉验收冒充游戏native验收。\n')
print(json.dumps({'status':value['status'],'protected_players':value['protection']['players'],'top':{key:files[str(S/key)] for key in ('patches/product_packs_preflight.py','patches/product-packs-release-manifest.json','patches/product-packs-release-installed.json')}},ensure_ascii=True))
