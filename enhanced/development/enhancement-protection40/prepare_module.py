from pathlib import Path
import sys
W=Path(r'D:\fifaol3\enhancement-protection40')
s=Path(r'D:\fifaol3\bp-settings-live-compat\20261106-200325\bp_protection_live_rates.py').read_text(encoding='utf-8')
s=s.replace('"""Private opt-in EP protection; install after breakthrough and before client handlers run."""','"""Optional client protection: 40% pre-attempt displayed value replaces normal fee."""')
s=s.replace('from decimal import Decimal, ROUND_CEILING\n','')
a=s.index("VERSION=");b=s.index('\ndef canonical',a)
s=s[:a]+"VERSION='protection40-v1'\nDEFAULT=dict(enabled=True,version=VERSION,ttl=180,fraction_percent=40,ordinary_fee_replaced=True)\n"+s[b:]
a=s.index('def fee(');b=s.index('    secret=secrets.token_bytes(32)',a)
s=s[:a]+'''def fee(value):
    if type(value) is not int or value <= 0:
        raise ValueError('PROTECTION_INVALID_VALUE')
    amount = (value * 2 + 4) // 5
    if amount > 2**53 - 1:
        raise ValueError('PROTECTION_PRICE_TOO_LARGE')
    return amount


def install(h):
    if getattr(h,'_protection40_installed',False):return
    cfg=dict(DEFAULT)
    if not isinstance(h.STATE_LOCK,type(threading.RLock())):raise RuntimeError('Protection requires RLock')
'''+s[b:]
a=s.index('    # Freeze all stable');b=s.index('    def fail(',a)
s=s[:a]+s[b:]
s=s.replace("        bvalue=base_value(pa['spid']);protect=fee(h.grade_of(pa),bvalue,cfg)\n        normal=h.enhance_cost(pa)\n        if normal+protect>2**53-1:raise ValueError('PROTECTION_PRICE_TOO_LARGE')", "        bvalue=h.player_value_price(pa['spid'],h.grade_of(pa));protect=fee(bvalue)\n        normal=0")
s=s.replace("rules=digest([cfg,h.BREAKTHROUGH_BALANCE,getattr(h,'GROWTH_V2',None)]))", "rules=digest(cfg))")
s=s.replace("    def label(data):\n", '''    def restore_status(st):
        pending=st['enhance_restore']
        p=next((p for p in st['teams'][str(h._default_slot(st))]['players'] if h.iid(p)==str(pending['id'])),None)
        current=h.grade_of(p) if p else -1
        target=pending.get('grade',-1)
        return dict(current_grade=current,restore_grade=target,can_restore=p is not None and 0<=current<target<=h.MAX_GRADE)
    def label(data):
''')
s=s.replace("'BP保级保护：保护费 '","'强化保护：目标卡强化前身价 '+format(data['base'],',')+' EP × 40% = '")
s=s.replace("' EP（含普通强化费）。成功失败均收费，成功正常升1；失败主卡保级、经验/角色保留，材料仍消耗。概率不提升；占用Gold槽。勾选ES失败仅退本次所耗，不额外赠ES，不产生ES恢复。'", "' EP（已替代原强化手续费，不再另收）。每次尝试均收费，成功失败不退款；成功升1、失败主卡保级、经验保留，材料仍消耗。概率不提升；与加成道具互斥，强化点数按原规则结算，不产生恢复报价。'")
s=s.replace("name='BP保级保护（消耗EP，失败保级，材料照耗）'", "name='强化保护（身价40%，替代手续费）'")
s=s.replace("description='可选付费服务，不是免费道具。+5至+19的会掉级且可失败组合可用；+1至+4本已保级无需付费。选中后看费用并二次确认；保护占Gold槽。'", "description='可选强化保护：每次收目标卡强化前身价40%，替代原手续费；失败保级、材料照耗。仅会掉级且可能失败的+5至+19组合可用；与加成道具互斥。'")
s=s.replace('status=h.enhancement_restore_status(st)','status=restore_status(st)')
s=s.replace("            if success and points=='1':h.add_es(st,-need)","            if points=='1':h.add_es(st,-need)")
s=s.replace("            h.merge_into(team,pa,pb)\n            out=", "            h.merge_into(team,pa,pb)\n            grant=0 if success else need\n            h.add_es(st,grant)\n            out=")
s=s.replace("grantes=need if not success and points=='1' else 0", "grantes=grant")
s=s.replace("base_policy='Boot-frozen +1 stable OVR price; never dynamic market quote'", "base_policy='Target current pre-attempt player_value_price; ceil(value * 40 / 100); replaces ordinary fee'")
s=s.replace("failure='Keeps target grade/XP/role; consumes material; refunds only ES spent, no restore quote'", "failure='Keeps target grade/XP; consumes material; original ES rules; no restore quote'")
s=s.replace('gold_exclusive=True,base_count=len(frozen)', 'boost_item_exclusive=True')
s=s.replace("h.BP_PROTECTION=copy.deepcopy(cfg);h.bp_protection_fee=lambda grade,spid:fee(grade,base_value(spid),cfg)", "h.PROTECTION40=copy.deepcopy(cfg);h.protection40_fee=lambda grade,spid:fee(h.player_value_price(spid,grade))")
s=s.replace('h._bp_protection_installed=True','h._protection40_installed=True')
compile(s,'enhancement_protection40.py','exec')
(W/'enhancement_protection40.py').write_text(s,encoding='utf-8')
print('generated module',len(s))
