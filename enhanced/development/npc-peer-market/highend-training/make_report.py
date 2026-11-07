from pathlib import Path
import collections,hashlib,json
P=Path(__file__).resolve().parent;F=P/'results'
r=json.loads((F/'training-report.json').read_text('utf8'));a=json.loads((P/'data-audit.json').read_text('utf8'));v=json.loads((F/'local-verification.json').read_text('utf8'));assert v['status']=='PASS';valuation=json.loads((P/'season-values.json').read_text('utf8'));assert valuation['model_sha256']==hashlib.sha256((F/'selected-model.json.gz').read_bytes()).hexdigest();values=valuation['rows'];rows=json.loads((P/'dataset.json').read_text('utf8'))
test_gk=[c for c in rows if c['kind']=='real' and c['partition']=='test' and c['attributes']['preferredposition1']==0 and (c['ovr']>=80 or c['season'] in (30,93))]
summary=dict(status='HIGHEND_SAMPLES_FILLED_AND_RETRAINED',price_region='kr',real_rows=a['real_rows'],synthetic_rows=a['synthetic_rows'],real_UL_cards=len(a['UL_real']),real_WL_cards=a['WL_real_count'],synthetic_missing_WL_cards=len(a['native_high_missing_quotes']),real_goalkeeper_cards=a['real_gk'],synthetic_rules=a['synthetic_rules'],final_real_training_rows=r['final_real_training_rows'],final_synthetic_training_rows=r['final_synthetic_training_rows'],real_test_rows=r['selected_refit_test']['overall']['rows'],synthetic_test_rows=0,real_test=r['selected_refit_test'],top_gk_test_unique_players=len({c['playerid'] for c in test_gk}),top_gk_test_card_names=[c['name'] for c in test_gk],independent_real_validation_UL=r['model_results']['highend_augmented']['validation'].get('UL'),verification=v,remote='/home/zhihao/fo3_value_training/run-20261107-highend-kr-v7b',production_changed=False)
(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),'utf8')
def money(x):return f'{x/1e12:.2f}万亿' if x>=1e12 else f'{x/1e8:.2f}亿' if x>=1e8 else f'{x/1e4:.2f}万' if x>=1e4 else f'{x:,}'
lines=['本轮已补齐高端样本并完成GPU重训、原始编码及本地推理核验。正式市场、存档、真实卡与余额未改动。','',f"所有真实标签统一为韩服历史EP，共{a['real_rows']:,}条。UL五张均有真实报价；WL有72条真实报价，缺价的索尔斯克亚另列为合成样本。共有{a['real_gk']:,}张真实门将卡，包含雅辛、范德萨、舒梅切尔、卡恩等高端门将。此前同输入同人价格相差十倍以上的三组异常记录继续隔离。",'',f"合成样本{a['synthetic_rows']:,}条，与真实报价明确区分：按正式强化属性增量和身价倍率生成强化区间；怀旧卡优先锚定同人UL/WL并作有限属性调整；传奇时刻按对应模板+8的1090倍基础价建立设计先验。原始档位价格是游戏规则，不是额外观察到的交易。",'', '同一球员及派生样本保持同组。初始训练只使用训练球员的真实与合成数据；验证阶段只根据真实报价选择轮数。验证球员的合成样本仅在最终重训时使用。测试集仅包含4,321条真实报价。模型仍只接收58项属性，308维编码，不使用姓名、ID或赛季作为输入。','',f"最终训练：真实{r['final_real_training_rows']:,}条、合成{r['final_synthetic_training_rows']:,}条。高端加权策略、网络、随机种子和停止指标均保存在training-report.json。真实报价对照网络复用相同权重；修正怀旧锚点优先级后重跑增强网络。",'', '| 真实留出测试 | 卡数 | 中位误差倍数 | 误差2倍以内 |','|---|---:|---:|---:|']
for key,label in [('overall','全体'),('high','高端卡'),('top_gk','顶级门将卡'),('WL','世界传奇')]:
 q=r['selected_refit_test'].get(key)
 if q:lines.append(f"| {label} | {q['rows']} | {q['median_error_factor']:.3f} | {q['within_2x']:.2%} |")
lines+=['',f"顶级门将测试的{len(test_gk)}张卡仅来自{summary['top_gk_test_unique_players']}名球员，结果波动很大。样本覆盖已经补上，不意味着门将泛化问题已解决。纯真实报价对照、增强网络验证、增强网络测试、最终重训测试分别列出，没有将合成拟合率混入真实市场准确率，也不与旧印尼模型的测试数字直接比较。",'', '以下金额统一按韩服原始EP÷1000展示为游戏EP参考；没有做跨区换算，也尚未用于正式市场。UL五张已进入最终训练，下面是锚点检查，不是独立泛化成绩。','', '| UL球员 | 模型基础估值 | 真实韩服报价，按同口径展示 |','|---|---:|---:|']
for c in values:
 if c['season']==30:lines.append(f"| {c['name']} | {money(c['game_ep'])} | {money(c['observed_kr_ep']//1000)} |")
lines+=['', '| 同球员档位对照 | 怀旧神兽+1 | UL+1 | 传奇时刻+1 |','|---|---:|---:|---:|']
for pid,name in [(1625,'亨利'),(28130,'罗纳尔迪尼奥')]:
 amounts=[]
 for s in (19,30,84):
  c=next(c for c in values if c['playerid']==pid and c['season']==s);amounts.append(money(c['game_ep']))
 lines.append('| '+name+' | '+' | '.join(amounts)+' |')
lines+=['', '传奇时刻≈对应传奇+8、怀旧与UL同档是合成训练先验，模型不保证逐卡严格满足。逐卡属性、真实报价、锚点及模型输出见season-values.json。缺价合成并不证明该价格在历史市场实际存在；源站也未提供逐卡报价日期或可成交证明。','',f"核验：{v['encoding_probes']}条编码一致、{v['gpu_parity_probes']}条GPU与本地数值一致，最大对数差{v['maximum_gpu_log_error']:.8g}；另核对标准推理路径并复算真实测试指标。",'', '文件：dataset.json保留每条样本的real/synthetic、partition、rule与anchor；data-audit.json和quarantine.json记录来源与排除；results/selected-model.json.gz为本轮模型。']
(P/'高端样本补齐与重训报告.md').write_text('\n'.join(lines),'utf8')
files=['dataset.json','data-audit.json','encoder.json','season-values.json','summary.json','results/training-report.json','results/selected-model.json.gz','results/local-verification.json']
(P/'artifact-sha256.json').write_text(json.dumps({f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in files},indent=2),'utf8');print(json.dumps(summary,ensure_ascii=False,indent=2))
