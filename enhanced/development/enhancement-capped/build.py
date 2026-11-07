from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
S=Path('D:/FO3ID/server')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
payload=['enhancement_progression.py','enhancement_protection40.py','enhancement_settings.py','npc_exchange.py','admin/index.html','gamedata/enhancement_rates.json']
baseline={rel:sha(S/rel) for rel in payload}
p=(S/'enhancement_protection40.py').read_text('utf8')
independent_checkbox='independent_checkbox=True' in p
p=p.replace("settings=h.enhancement_settings_get()", "settings=h.enhancement_settings_get()\n        effective_points=h.enhancement_point_effective(pa,pb,points=='1')")
p=p.replace("points=points=='1',event=str(event)", "points=effective_points,event=str(event)")
p=p.replace("'当前+12起（冲+13）点数按材料加成后基础概率相对提高10%，ES扣取/失败发放保持，不产生恢复报价。'", "'所有等级点数相对提高10%，不超过同等级材料上限；已达上限不扣点数，失败ES发放保持，不产生恢复报价。'")
# The original label joins this sentence without a preceding quote boundary.
p=p.replace('当前+12起（冲+13）点数按材料加成后基础概率相对提高10%，ES扣取/失败发放保持，不产生恢复报价。', '所有等级点数相对提高10%，不超过同等级材料上限；已达上限不扣点数，失败ES发放保持，不产生恢复报价。')
p=p.replace("needes=h.enhance_es(pa),\n                protection=", "needes=h.enhance_es(pa) if h.enhancement_point_effective(pa,pb,True) else 0,\n                protection=")
p=p.replace("if points=='1' and h.my_coach(st).get('es',0)<need", "if data['points'] and h.my_coach(st).get('es',0)<need")
p=p.replace("if points=='1':h.add_es(st,-need)", "if data['points']:h.add_es(st,-need)")
if independent_checkbox:
 needle="        rate=h.enhance25_rate(pa,pb,points=='1',booster,event)"
 assert p.count(needle)==1
 p=p.replace(needle,"        # At the ceiling, keep the checkbox protection but do not spend a useless booster.\n        if not h.enhancement_point_effective(pa,pb,True):\n            booster=None;booster_id='-1'\n"+needle)
 p=p.replace('可与加成道具、强化点数及适用活动叠加','可与加成道具及强化点数叠加，点数/道具均为相对加成且不突破同级材料上限；已满上限不扣点数或加成道具，无活动概率加成')
(R/'enhancement_protection40.py').write_text(p,encoding='utf8')
p=(S/'enhancement_settings.py').read_text('utf8').replace('Persistent base enhancement chances', 'Persistent equal-material enhancement ceilings')
p=p.replace('0 <= value <= 100','0 <= value <= 90').replace('0 到 100','0 到 90')
p=p.replace("'rates': dict(active_rates), 'defaults': dict(default_percent)", "'rates': dict(active_rates), 'defaults': dict(default_percent), 'semantics': 'equal_material_ceiling', 'maximum': 90")
(R/'enhancement_settings.py').write_text(p,encoding='utf8')
p=(S/'npc_exchange.py').read_text('utf8')
needle='        graded=self.market.reference(spid,grade)'
assert p.count(needle)==1
p=p.replace(needle, "        if hasattr(self.market.h,'enhancement_expected_value'):\n            return self.market.h.enhancement_expected_value(base,grade)\n"+needle)
(R/'npc_exchange.py').write_text(p,encoding='utf8')
p=(S/'admin/index.html').read_text('utf8')
p=p.replace('按目标卡当前等级设置合卡基础成功率。', '按主卡当前等级设置同等级材料的成功率上限。')
p=p.replace('材料卡倍率与已有道具效果保留；当前 +12 起（冲 +13），强化点数按材料加成后的基础成功率相对提高 10%，低档仍加 10 个百分点，最终最高 100%。', '材料低于主卡的 ⅓、⅔、同级时分别取上限的 35%、50%、75%，同级及以上取 100%。所有等级点数相对 +10%，铜/银/金道具相对 +5%/+10%/+15%，比例相加且不超过本阶段上限；已满不消耗点数或加成道具，无活动概率加成。')
p=p.replace('基础成功率', '同级材料上限').replace('max="100" step="any" required data-enhancement-grade', 'max="90" step="any" required data-enhancement-grade')
(R/'admin').mkdir(exist_ok=True)
(R/'admin/index.html').write_text(p,encoding='utf8')
rates=(90,85,75,65,55,45,38,32,28,25,20,15,12,10,8,6,5,4,3)
(R/'gamedata').mkdir(exist_ok=True)
(R/'gamedata/enhancement_rates.json').write_text(json.dumps(dict(version=1,max_grade=20,rates={str(g):v for g,v in enumerate(rates,1)}),indent=2)+'\n',encoding='utf8')
for rel in payload:
 if rel.endswith('.py'):compile((R/rel).read_bytes(),rel,'exec')
result=dict(baseline=baseline,outputs={rel:sha(R/rel) for rel in payload},probabilities_by_current_grade={str(g):v for g,v in enumerate(rates,1)},value_model='minimum_expected_EP_cost')
(R/'build.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('Built capped enhancement rules, protection integration, settings UI and compact value curve')
