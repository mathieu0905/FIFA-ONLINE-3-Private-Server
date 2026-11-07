from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=('enhancement_protection40.py','enhancement_progression.py')
baseline={rel:sha(S/rel) for rel in files}
p=(S/files[0]).read_text('utf8')
assert "VERSION='protection40-v2-stack'" in p
p=p.replace("VERSION='protection40-v2-stack'","VERSION='protection40-v3-both'")
p=p.replace('ordinary_fee_replaced=True)',"ordinary_fee_replaced=True,protect_material=True,material_on_failure='keep',material_on_success='consume')")
p=p.replace("h.enhancement_failure_grade(pa)==h.grade_of(pa) or h.grade_of(pb)==0 or rate>=1","h.grade_of(pb)==0 or rate>=1")
p=p.replace('成功升1、失败主卡保级、经验保留，材料仍消耗。','成功主卡升1并消耗副卡；失败主卡、副卡均保留，双方等级、经验与阵容位置不变。')
p=p.replace('失败保级、材料照耗。仅会掉级且可能失败的+6至+19（+10阶段线除外）组合可用','失败主副卡均保留，成功消耗副卡。主卡+1至+19且可能失败的有效组合可用')
p=p.replace('该等级原本已保级或组合必成功，无需付费保护','该组合不提升强化等级或原本必成功，无需付费保护')
needle="            params=parse_qs(query)\n            if params.get('protection_ack')!=[VERSION] or not verify((params.get('protection_token') or [''])[0],data):return fail('PROTECTION_REPREVIEW_REQUIRED')"
assert p.count(needle)==2
p=p.replace(needle,needle+"\n            receipt_key=hashlib.sha256(params['protection_token'][0].encode()).hexdigest()\n            attempt_coach=h.my_coach(st)\n            if receipt_key in attempt_coach.get('protection_attempt_receipts',{}):return fail('PROTECTION_ALREADY_USED')",1)
needle='            h.merge_into(team,pa,pb)'
assert p.count(needle)==1
p=p.replace(needle,"            if success:h.merge_into(team,pa,pb)\n            else:pa.pop('_market_merge_snapshot',None)")
needle="kept_grade=not success,version=VERSION)"
assert p.count(needle)==1
p=p.replace(needle,"kept_grade=not success,material_kept=not success,protected_cards='main_and_material',version=VERSION)")
needle="            h._save(st)\n            return h._json(out)"
assert p.count(needle)==1
p=p.replace(needle,"            stamp=time.time()\n            receipts={key:expiry for key,expiry in attempt_coach.get('protection_attempt_receipts',{}).items() if expiry>=stamp}\n            receipts[receipt_key]=stamp+cfg['ttl']\n            attempt_coach['protection_attempt_receipts']=receipts\n"+needle)
p=p.replace("failure='Keeps target grade/XP; consumes material; original ES rules; no restore quote'", "failure='Keeps both main and material instances, grades, XP and squad slots; original ES rules; no restore quote',success='Upgrade main; consume material',protected_cards='main_and_material'")
(R/files[0]).write_text(p,encoding='utf8')
p=(S/files[1]).read_text('utf8').replace("VERSION = 'progression20-capped-v3'","VERSION = 'progression20-capped-both-v4'")
p=p.replace('A protected failure has zero rebuild loss; natural floors need no protection.','Protected failures keep both cards: material is paid only once, on success.')
p=p.replace("                if protected and failed_grade == failure_grade(grade):\n                    continue\n",'')
p=p.replace('                cost = values[grade] + (values[material] + fee + (1 - probability) * rebuild) / probability',
    '                material_cost = probability * values[material] if protected else values[material]\n                cost = values[grade] + (material_cost + fee + (1 - probability) * rebuild) / probability')
p=p.replace("failed_rebuild='V(main)-V(failed_grade); zero with protection',", "failed_rebuild='V(main)-V(failed_grade); zero with protection', protected_material='Consumed only on success; priced once, not once per attempt',")
(R/files[1]).write_text(p,encoding='utf8')
for rel in files:compile((R/rel).read_bytes(),rel,'exec')
(R/'build.json').write_text(json.dumps(dict(baseline=baseline,outputs={rel:sha(R/rel) for rel in files},value_model='minimum_expected_EP_cost_material_kept_on_protected_failure'),indent=2),encoding='utf8')
print('Built mandatory main/material protection and matched expected-cost model')
