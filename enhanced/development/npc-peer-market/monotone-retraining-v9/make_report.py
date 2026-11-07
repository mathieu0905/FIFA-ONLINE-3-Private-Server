"""Record the completed training, latest user criteria and precise limits."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import inspect
import json
import re
import sys
import urllib.request

P = Path(__file__).resolve().parent
S = Path('D:/FO3ID/server')


def main():
    trained = json.loads((P / 'training-report.json').read_text('utf8'))
    local = json.loads((P / 'local-verification.json').read_text('utf8'))
    previous = json.loads((P / 'previous-test-baseline.json').read_text('utf8'))
    assert trained['status'] == local['status'] == 'PASS'
    assert not trained['single_attribute_violations'] and trained['new_dominance_inversions'] == 0
    assert trained['strictly_positive_displayed_price_sensitivity'] is True
    play = (S / 'play-local.bat').read_bytes()
    match = re.findall(rb'patches[\\/][a-z0-9_]+_preflight\.py', play)
    assert len(match) == 1
    top = S / match[0].decode().replace('\\', '/')
    spec = importlib.util.spec_from_file_location('_observed_current_top', top)
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    top_paths = [top, S / parent.MANIFEST, S / parent.RECEIPT, S / 'play-local.bat']
    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in top_paths}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8088/api/hot_update_status', timeout=3) as response:
        runtime = json.load(response)
    with opener.open('http://127.0.0.1:8088/api/market_price_store?spid=9138726&grade=1', timeout=3) as response:
        live_old_price = json.load(response)
    source_old, source_new = previous['metrics']['overall'], trained['real_test']['overall']
    summary = dict(status='GPU_RETRAINED_STRICT_CONSTRAINTS_PASS_NOT_ACTIVATED',
        completed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        latest_user_criterion='For the same player, if all 33 abilities and actual foot/skill stars do not decrease and at least one increases, fair price must strictly increase. Single foot and skill increases also apply to GK.',
        label_context='Price does not use identity, season, primary-position/body/animation/trait labels; best native role ability is a positive monotone maximum.',
        training=dict(device='remote A100 physical GPU 2', local_game_gpu_used=False, algorithm='GPU XGBoost with hard positive constraints',
                      selected=trained['selected'], source_sha256=trained['training_source_sha256'], synthetic_priors_disclosed=True),
        constraint_audit=dict(profiles=trained['current_profiles'], single_attribute_checks=trained['single_attribute_checks'],
                              single_attribute_failures=0, comparable_same_player_pairs=trained['dominance_pairs'],
                              old_price_inversions=trained['old_dominance_inversions'], new_strict_dominance_failures=trained['new_dominance_inversions'],
                              old_one_ep_prices=trained['old_one_ep_prices'], new_one_ep_prices=trained['new_one_ep_prices']),
        minimum_displayed_sensitivity=dict(EP_per_native_ability_point=1, EP_per_foot_star=25, EP_per_actual_skill_star=25,
                                          purpose='Break integer/tree plateaus; remaining price response is learned. These minimums are disclosed design constraints, not claimed learned causal premiums.'),
        source_price_accuracy=dict(test_rows=4321, previous=source_old, retrained=source_new,
                                   limitation='Held-out historical market-price fit is not uniformly better. Historical scarcity labels are not ground truth for actual play strength; no native match calibration was performed.'),
        local_verification=local,
        model=str(P / 'selected-model.json.gz'), model_sha256=trained['model_sha256'],
        formal_written=False, formal_activated=False, services_start_stop_restart='none', game_GUI='none',
        state_shop_and_historical_prices_written=False, official_sources_unchanged=local['formal_source_inputs_unchanged'],
        observed_formal_entry=str(top), observed_compose_api='compose_manifest' + str(inspect.signature(parent.compose_manifest)),
        observed_current_top_hashes=hashes, runtime_business_hot_update=runtime,
        live_price_probe_still_old={k: live_old_price.get(k) for k in ['spid', 'initial_price', 'current_price', 'value']},
        native_verified=False, deployment_boundary='Market backend valuation is outside ABI1 route updates. Do not stop/reload the current game/server; activation remains deferred.',
        previous_rule_only_installer_retired=True)
    (P / 'handback.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), 'utf8')
    lines = [
        'FO3 球员估值 GPU 重训与严格倒挂检查报告',
        '完成时间：' + summary['completed_at'],
        '',
        '结论：实际GPU重训完成，严格能力/逆足/花式上涨约束通过；当前正式服价格未切换。',
        '没有停服、重启、操作游戏或写真实存档/余额/卡/市场历史。',
        '',
        '本轮验收原则：同一球员各项能力和实际星级均不降低、至少一项提高时，基础身价必须严格提高。',
        '逆足和花式单独提高也必须严格更贵，门将同样覆盖；比较跨主位置和身体记录。',
        '模型使用33项能力、逆足、花式及按正权重计算的最佳位置能力；不使用姓名、赛季、位置/身体/动画标签。',
        '除模型的硬单调约束外，最终本地EP价格加入公开的最小上涨项以消除树叶和整数取整同价。',
        '最小涨幅：每个原生能力点至少1 EP；每档逆足/实际花式至少25 EP，其余涨幅由模型学习。',
        '这不是统一固定涨幅，也不是已由实机标定的溢价。两份历史花式code5模板按既有最高实际星档保留，不改数据库。',
        '',
        f"全量能力快照：{trained['current_profiles']}张卡。", 
        f"单项能力/逆足/花式严格上涨检查：{trained['single_attribute_checks']}次，失败0。",
        f"同人能力占优比较：{trained['dominance_pairs']}对；旧初价倒挂{trained['old_dominance_inversions']}对，新估值严格上涨失败0对。",
        f"1 EP卡：旧{trained['old_one_ep_prices']}张，新{trained['new_one_ep_prices']}张。",
        '',
        f"固定4321条真实测试样本：历史价格误差倍数中位数旧{source_old['median_error_factor']:.3f}，新{source_new['median_error_factor']:.3f}。",
        f"log-MAE旧{source_old['log_mae']:.4f}，新{source_new['log_mae']:.4f}。",
        '原始历史价格拟合并非所有指标改善，不能把零倒挂写成所有球员实际比赛强度已经精确标定。',
        '公开KR历史价格与已有声明的合成高端先验分开；训练/验证/测试按球员身份隔离，测试不参与选择。',
        '预测误差统计在历史价格原始单位上；最终基础EP包含连续货币转换和能力保底项，强化投资及市场溢价未在本次预览中叠加。',
        '',
        '原始三组坏样本（新训练模型基础EP，不是已上线价格）：']
    examples = {r['spid']: r for r in local['examples']}
    for name, strong, weak in [('莱斯科特', 9138726, 47138726), ('科洛·图雷', 9119152, 47119152), ('博内拉', 9045595, 47045595)]:
        lines.append(f"{name}：较强卡 {examples[strong]['new_fair_price']} EP，较弱卡 {examples[weak]['new_fair_price']} EP。")
    lines += ['', '训练模型SHA256：' + trained['model_sha256'],
              '完整证据：training-report.json、dominance-audit.json、local-verification.json、handback.json。',
              '推理入口：predict.py --spid <SPID>，只读正式球员属性，无GPU或训练库依赖。',
              '正式激活边界：当前ABI1不支持市场后台估值对象；本轮不重启或热改运行对象。',
              '旧的纯规则安装器已明确退役，不会误把之前方案上线。']
    (P / '训练与倒挂检查报告.txt').write_text('\n'.join(lines) + '\n', 'utf8')
    retired = Path('D:/fifaol3/value-diagnosis/superseded.json')
    retired.write_text(json.dumps(dict(status='SUPERSEDED_BY_REQUESTED_RETRAINING', new_work=str(P),
                                       model=str(P / 'selected-model.json.gz'), formal_activated=False), indent=2), 'utf8')
    print(json.dumps({k: summary[k] for k in ['status', 'constraint_audit', 'formal_activated', 'model_sha256']}, ensure_ascii=True))


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
