from pathlib import Path
W=Path(r'D:\fifaol3\enhancement-progression');S=Path(r'D:\FO3ID\server')
s=(S/'http_config.py').read_text(encoding='utf-8-sig')
a='enhancement20.install(sys.modules[__name__])\n';assert s.count(a)==1
s=s.replace(a,a+'\nimport enhancement_progression\nenhancement_progression.install(sys.modules[__name__])\n')
a='before - 1 if before >= ENHANCE_DROP_FROM else before';assert s.count(a)==2
s=s.replace(a,'enhancement_failure_grade(pa)')
a='import enhancement_protection40\n';assert s.count(a)==1
s=s.replace(a,'enhancement_progression.install_runtime(sys.modules[__name__])\n\n'+a)
s=s.replace('round(rate * 100)', 'round(rate * 100, 3)').replace('round(enhance_rate(pa, pb) * 100)', 'round(enhance_rate(pa, pb) * 100, 3)')
s=s.replace('"attribPlus": GRADE_BOOST[after] - GRADE_BOOST[before],', '"attribPlus": GRADE_BOOST[after] - GRADE_BOOST[before], "protection": {"applied": not success and after == before, "paid": False, "kind": "safe_floor"},')
s=s.replace('"attribPlus": GRADE_BOOST[g] - GRADE_BOOST[before], "grantes": grant,', '"attribPlus": GRADE_BOOST[g] - GRADE_BOOST[before], "grantes": grant, "protection": {"applied": not success and g == before, "paid": False, "kind": "safe_floor"},')
compile(s,'http_config.py','exec');(W/'http_config.py').write_text(s,encoding='utf-8')
s=(S/'enhancement_protection40.py').read_text(encoding='utf-8')
a="h.grade_of(pa)<h.ENHANCE_DROP_FROM";assert s.count(a)==1
s=s.replace(a,"h.enhancement_failure_grade(pa)==h.grade_of(pa)")
s=s.replace('mingrade=6,maxgrade=20','mingrade=7,maxgrade=20')
s=s.replace('+5至+19','+6至+19（+10阶段线除外）').replace('+1至+4','+1至+5及+10')
s=s.replace("概率不提升；与加成道具互斥，强化点数按原规则结算", "概率不提升；与加成道具互斥，当前+13起点数按材料加成后基础概率相对提高10%，ES扣取/失败发放保持")
s=s.replace('protection=dict(applied=True,fee=', 'protection=dict(applied=True,paid=True,fee=')
(W/'enhancement_protection40.py').write_text(s,encoding='utf-8')
s=(S/'admin/index.html').read_text(encoding='utf-8')
s=s.replace('材料卡等级倍率、强化点数、加成道具和活动加成仍按现有规则叠加，最终成功率最高 100%。+0 材料保留原等级且必定成功；+20 已满级。','材料卡倍率与已有道具效果保留；当前 +13 起，强化点数按材料加成后的基础成功率相对提高 10%，低档仍加 10 个百分点，最终最高 100%。+0 材料保留原等级且必定成功；+20 满级。')
s=s.replace('<form id="enhancementForm">','<p class="muted">失败：+5 及以下保级，普通失败最多掉一级且不跌破 +5、+10。保护选项按当前身价 40% 收费并保级，替代普通手续费；普通手续费为当前身价 2%，最低 1000 BP。+10 阶段线无需另买保护。+11 至 +20 的身价升级倍率逐步由 1.25 提高至 3.2 倍；不改变旧包卡池/概率和已成交合同。</p>\n      <form id="enhancementForm">')
s=s.replace('原默认值（%）','新版默认值（%）')
(W/'index.html').write_text(s,encoding='utf-8')
print('Prepared minimal production deltas; no formal files written')
