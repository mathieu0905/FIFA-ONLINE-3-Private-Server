from pathlib import Path
import datetime,hashlib,inspect,json,subprocess
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
installation=json.loads((R/'installed-result.json').read_text(encoding='utf8'));backup=Path(installation['backup'])
before=json.loads((backup/'evidence/gamedata/state.json').read_text(encoding='utf8'))
after=json.loads((S/'gamedata/state.json').read_text(encoding='utf8'))
assert before['coaches']==after['coaches'] and before['teams']==after['teams']
names=('patches/elite_chains_preflight.py','patches/elite-chains-release-manifest.json','patches/elite-chains-release-installed.json','product_packs.py','gamedata/product_chain_elite.json','gamedata/product_packs.json','play-local.bat')
files={str(S/name):sha(S/name) for name in names}
value=dict(status='ELITE_CHAINS_INSTALLED_LIVE_PROTOCOL_PASS_NATIVE_PENDING',observed_at=datetime.datetime.now().astimezone().isoformat(),
 top_preflight=str(S/names[0]),top_manifest=str(S/names[1]),top_receipt=str(S/names[2]),files=files,
 API={'compose_manifest':'compose_manifest(server=None,client=None) returns dict','_compose':'_compose(server,client,m=None,installed=True) returns (composed,validator)','preflight':'preflight(server=None,client=None) final physical verification'},
 protection={'coaches_and_teams_exactly_equal_install_snapshot':True,'players':sum(len(team.get('players',[])) for team in after['teams'].values()),'state_shop_restored':False,'purchases':0,'grants':0},
 evidence={'installation':str(R/'installed-result.json'),'live':str(R/'live-results.json'),'regression':str(R/'test-results.json'),'IO':str(R/'install-test-results.json')},
 current_launcher=(S/'play-local.bat').read_text(encoding='utf8'),root_descriptor_written=False)
(R/'installed-handback.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
with (S/'docs/工程经验与修改边界.txt').open('a',encoding='utf8') as f:
    f.write('\nFO3-005 续（2026-11-06 20:38，elite-product-chains-v1，正式已安装/服务重启/协议通过，native待验证）：人类明确允许现在重启直接上线。继承nostalgia_name完整父层，仅4个server目标增量发布，1388物理guards通过；Windows PowerShell5.1安装边界12项、回滚/幂等及3种并发坏样本通过。备份见本次installed-result.json，不覆盖任何旧manifest/receipt。旧97300011/97300012及97400020/97400100停止未来购买，已持有旧池、强化、礼包及receipt规则保持；新97310011纯经典传奇115人，95%其它经典传奇/5%UL大罗，强化6..11为30/28/25/10/6/1%，新97310012主流85+能力池75%/经典传奇25%，独立每日100份。单卖时刻97310084固定+1、600000点券、每经理每周1份。三条新10轮链：传奇登顶68包/轮、传奇百包873包/轮、怀旧神兽52包/轮（50随机19季+1固定19季11+1时刻1），逐档价格与奖励实时协议验证通过。原54高强度/自选包和原两条10轮连锁仍在，14项实时检查通过。修复同一堆栈补购后token复用导致旧receipt回放而不开新包：monotonic product_open_seq与扣包/发卡/receipt同事务，旧待用token兼容、新iid序号0，13项失败/并发/重放/经理生命周期样本通过；不改旧概率。原始坏样本和回归：pack_limits/elite/reproduce_nonce_bug.py、test_nonce_sequence.py、test_moments_rights.py、test_controlled_moments.py、test.py及verify_live.py。全部67项针对性功能检查通过，真实验收只读无购买/赠送，经理/卡/余额/库存/阵容与fresh安装快照保持，未恢复state/shop。未启动/操作游戏，原生画面与真实开包未冒称通过。证据D:/fifaol3/pack_limits/elite/installed-handback.json、live-results.json及installed-result.json。\n')
print(json.dumps({'status':value['status'],'players':value['protection']['players'],'top':{name:files[str(S/name)] for name in names[:3]}},ensure_ascii=True))
