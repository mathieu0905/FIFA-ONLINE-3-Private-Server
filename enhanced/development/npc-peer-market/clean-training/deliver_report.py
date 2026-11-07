from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;F=P/'results/final'
clean=json.loads((P/'cleaning-report.json').read_text('utf8'));extra=json.loads((P/'extra-audit.json').read_text('utf8'));train=json.loads((F/'training-report.json').read_text('utf8'));verify=json.loads((F/'local-verification.json').read_text('utf8'));assert verify['status']=='PASS'
rows=json.loads((P/'clean-data.json').read_text('utf8'));new=json.loads((P/'extra-data.json').read_text('utf8'));fields=json.loads((P/'encoder.json').read_text())['raw_fields'];combined=[]
for r in rows:combined.append(dict(spid=r['spid'],playerid=r['playerid'],name=r['name'],attributes={f:r[f] for f in fields},price=r['price'],region='id',final_partition='test' if r['split']=='test' else 'refit_train',source_url=r['source_url'],source_page_sha256=r['source_page_sha256'],origin='original_cohort'))
for r in new:combined.append(dict(spid=r['spid'],playerid=r['playerid'],attributes=r['raw'],price=r['price'],region='id',final_partition='refit_train' if r['refit_eligible'] else 'extra_test',source_url=r['source_url'],source_page_sha256=r['source_sha256'],origin='newly_collected'))
assert len({r['spid'] for r in combined})==len(combined)
assert not {r['playerid'] for r in combined if r['final_partition']=='refit_train'}&{r['playerid'] for r in combined if r['final_partition']!='refit_train'}
(P/'final-clean-data.json').write_text(json.dumps(combined,ensure_ascii=False),'utf8')
old=train['old_model_on_same_test'];now=train['selected_refit_test']
summary=dict(status='CLEANED_RETRAINED_AND_VERIFIED',price_region='id',dataset_cards=len(combined),final_training_cards=train['final_refit_rows'],primary_same_cards_test=train['original_test_cards'],extra_heldout_cards=train['extra_test_cards'],raw_fields=len(fields),encoded_dimensions=clean['encoded_dimensions'],original_rows=clean['original_rows'],original_region_fallback_rows=sum(clean['legacy_region_reconstruction_from_fresh_quotes'].get(k,0) for k in ('kr','th','vn','sg')),removed_counts=clean['removed_counts'],added_native_cards=extra['native_extra_cards'],old_model_same_test=old,new_model_same_test=now,extra_test=train['extra_test'],within_2x_improvement_percentage_points=(now['within_2x']-old['within_2x'])*100,selected_on_validation=train['selected_on_validation'],parameters_per_member=train['model_results'][train['selected_on_validation']]['parameters_per_model'],raw_encoding_probes=verify['raw_encoding_probes'],portable_gpu_probes=verify['portable_gpu_probes'],maximum_log_prediction_difference=verify['maximum_log_prediction_difference'],quote_timestamp_available=False,production_changed=False,remote_directory='/home/zhihao/fo3_value_training/run-20261107-single-region-v6')
(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),'utf8')
text=f'''已完成数据源核查、单一区服清洗、补采和GPU重训。正式游戏定价、真实存档和资产没有改动。

旧训练集的16,041张卡全部重新查到。16,040张的58项训练输入与早期客户端数据库一致，唯一差异是本地修改过的CC博格巴，已排除。源站按赛季抽查40张卡的33项完整能力值全部与客户端源一致；其余样本逐卡核对源站公开的5项能力值。没有发现大面积串季证据，但这不等于独立证明每条原始历史记录都正确。

曼丹达2010与10WC的33项能力在源站、客户端源中均相同。韩服44,000与6,700,000 EP的报价差距152倍，属于可疑记录，未将它解释为正常价值差。10WC缺印尼报价，新数据将其排除。另有巴莱隆、博沃的韩服同输入异常报价，也保存在source-conclusions.json中。

旧数据包含{summary['original_region_fallback_rows']:,}条跨区换算标签（约{summary['original_region_fallback_rows']/16041:.1%}）。现在只保留印尼区原始报价，不补价、不换算：旧样本保留{clean['kept_rows']:,}张；排除5,599张缺印尼报价的卡，以及1张本地修改卡。又补采并核验{extra['native_extra_cards']:,}张本地卡，合计{len(combined):,}张。

最终训练{train['final_refit_rows']:,}张，原测试集{train['original_test_cards']:,}张，补采留出{train['extra_test_cards']}张。相同球员的不同赛季不跨训练与测试。网络规模、轮数和学习率计划由原清洗数据的验证集决定，补采后保持这些设置；没有根据最终测试分数选择版本。58项原始输入编码为296维，仍不使用姓名、球员ID或赛季来定价。

同一批{train['original_test_cards']:,}张测试卡、同一套印尼报价的比较：

| 指标 | 旧混区模型 | 清洗补采后模型 |
|---|---:|---:|
| 误差在2倍以内 | {old['within_2x']:.2%} | {now['within_2x']:.2%} |
| 误差在3倍以内 | {old['within_3x']:.2%} | {now['within_3x']:.2%} |
| 中位误差倍数，越低越好 | {old['median_error_factor']:.3f} | {now['median_error_factor']:.3f} |
| 90分位误差倍数，越低越好 | {old['p90_error_factor']:.3f} | {now['p90_error_factor']:.3f} |

初始清洗队列重训的结果另存于results/training-report.json，补采后的最终结果在results/final/training-report.json。补采独立留出48张的结果也单列，不与原测试卡混算。不能拿旧16,041张混区全测试集的52%左右，直接与当前印尼子集的成绩作比较。

已通过100条原始属性编码一致性检查、20条GPU与本地推理一致性检查，并重新计算测试指标；最大对数预测差{verify['maximum_log_prediction_difference']:.8g}。新增样本中有少量未知体型/动作类别，继续采用既有未知类别编码规则，计数见extra-audit.json。

源站没有逐卡报价日期、成交量或可成交证明。这仍然是统一口径的历史报价模型，不能保证没有过期报价，也不能把属性价值与市场溢价完全分开。异常门槛在训练前固定：同一球员、58项输入完全相同、同区价格相差至少10倍则隔离；合并后未发现这种冲突。未按模型误差或绝对高价删样本。

最终模型：results/final/selected-model.json.gz
完整清洗数据：final-clean-data.json
来源和排除证据：regional-source.json、attribute-audit.json、cleaning-report.json、removed-rows.json、source-conclusions.json、extra-audit.json。
'''
(P/'清洗与训练报告.md').write_text(text,'utf8')
files=['final-clean-data.json','encoder.json','cleaning-report.json','extra-audit.json','attribute-audit.json','regional-source.json','results/final/training-report.json','results/final/local-verification.json','results/final/selected-model.json.gz']
manifest={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in files}
(P/'artifact-sha256.json').write_text(json.dumps(manifest,indent=2),'utf8');print(json.dumps(summary,ensure_ascii=False,indent=2))
