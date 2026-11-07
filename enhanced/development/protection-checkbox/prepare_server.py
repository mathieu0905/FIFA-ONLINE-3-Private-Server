from pathlib import Path
import hashlib,json
W=Path(__file__).parent;S=Path(r'D:\FO3ID\server')
p=S/'enhancement_protection40.py';before=p.read_bytes();s=before.decode('utf8').replace('\r\n','\n')
(W/'enhancement_protection40.before.py').write_bytes(before)
s=s.replace("VERSION='protection40-v1'", "VERSION='protection40-v2-stack'")
s=s.replace('def context(st,a,b,points,event):','def context(st,a,b,points,event,item):')
needle="        if h.enhancement_failure_grade(pa)==h.grade_of(pa)"
at=s.index(needle)
s=s[:at]+'''        booster_id='-1' if str(item)==str(ITEM) else str(item)
        booster=h.boost_stack(st,booster_id) if booster_id!='-1' else None
        if booster_id!='-1' and (booster is None or booster.get('expired') or booster.get('__expired')):
            raise ValueError('BOOST_ITEM_UNAVAILABLE')
        rate=h.enhance25_rate(pa,pb,points=='1',booster,event)
'''+s[at:]
s=s.replace("h.enhance25_rate(pa,pb,points=='1',None,event)>=1", "rate>=1")
s=s.replace("normal_ep=normal,total_ep=normal+protect,rate=h.enhance25_rate(pa,pb,points=='1',None,event),", "normal_ep=normal,total_ep=normal+protect,rate=rate,boost_itemid=booster_id,\n                  boost_snapshot=digest(booster) if booster else None,\n                  boost_name=({1000052:'黄金强化加成',1000053:'白银强化加成',1000054:'青铜强化加成'}.get(int(booster_id),h.item_def(int(booster_id)).get('name','强化加成道具')) if booster else None),")
s=s.replace('return pa,pb,data','return pa,pb,data,booster')
s=s.replace("' EP（已替代原强化手续费，不再另收）。", "' EP（已替代原强化手续费，不再另收）。")
old="' EP（已替代原强化手续费，不再另收）。每次尝试均收费，成功失败不退款；成功升1、失败主卡保级、经验保留，材料仍消耗。概率不提升；与加成道具互斥，当前+12起（冲+13）点数按材料加成后基础概率相对提高10%，ES扣取/失败发放保持，不产生恢复报价。')"
new="' EP（已替代原强化手续费，不再另收）。每次尝试均收费，成功失败不退款；成功升1、失败主卡保级、经验保留，材料仍消耗。保护本身不提高概率，可与加成道具、强化点数及适用活动叠加；最终成功率 '+format(data['rate']*100,'.3f').rstrip('0').rstrip('.')+'%。'+(' 本次同时使用'+data['boost_name']+'，无论成功失败均消耗1个。' if data['boost_name'] else '')+' ES扣取/失败发放保持，不产生恢复报价。')"
assert old in s;s=s.replace(old,new)
s=s.replace('与加成道具互斥。','可与黄金等强化加成道具同时使用。')
a=s.index('    def coach_items(');b=s.index('    h.coach_items=coach_items',a)
s=s[:a]+'''    def coach_items(st,slot,where='items'):
        # Protection is now an independent checkbox, never a booster inventory row.
        return [row for row in original_items(st,slot,where) if str(row.get('itemid'))!=str(ITEM)]
'''+s[b:]
needle='    old_preview=h.ep_enhance25_preview;old_enhance=h.ep_enhance25\n'
s=s.replace(needle,needle+'''    def requested(item,query):
        params=parse_qs(query)
        return str(item)==str(ITEM) or params.get('protection')==['1'] or 'protection_ack' in params or 'protection_token' in params
''')
s=s.replace("if str(item)!=str(ITEM):return old_preview", "if not requested(item,query):return old_preview")
s=s.replace("if str(item)!=str(ITEM):return old_enhance", "if not requested(item,query):return old_enhance")
s=s.replace('def blocked_preview(st,a,b,reason,points,event,**protection):',"def blocked_preview(st,a,b,reason,points,event,item='-1',**protection):")
s=s.replace("probability=round(h.enhance25_rate(pa,pb,points=='1',None,event)*100,3) if valid else 0,", "probability=round(h.enhance25_rate(pa,pb,points=='1',h.boost_stack(st,str(item)) if str(item)!=str(ITEM) else None,event)*100,3) if valid else 0,")
s=s.replace("points,event,can_restore", "points,event,item=item,can_restore").replace("points,event,label=message", "points,event,item=item,label=message")
s=s.replace("points,event,label='该等级", "points,event,item=item,label='该等级")
s=s.replace('请将加成道具改选“不用”继续。','请取消勾选“强化保护”后继续。')
s=s.replace('保护预览条件无效，请重新选择。','加成道具不足、已失效或保护条件无效，请重新选择。')
s=s.replace('try:pa,pb,data=context(st,a,b,points,event)', 'try:pa,pb,data,booster=context(st,a,b,points,event,item)')
s=s.replace("rate=h.enhance25_rate(pa,pb,points=='1',None,event)", "rate=data['rate']")
s=s.replace("success=h.random.random()<h.enhance25_rate(pa,pb,points=='1',None,event)", "success=h.random.random()<data['rate']")
needle="            if points=='1':h.add_es(st,-need)\n"
assert s.count(needle)==1
s=s.replace(needle,needle+'''            if booster:
                booster['remains']-=1
                if not booster['remains']:h.my_coach(st)['items'].remove(booster)
''')
s=s.replace("fee_on='Every confirmed attempt, success or failure',boost_item_exclusive=True", "fee_on='Every confirmed attempt, success or failure',boost_item_exclusive=False,independent_checkbox=True")
compile(s,'enhancement_protection40.py','exec')
(W/'enhancement_protection40.py').write_text(s,encoding='utf8')
(W/'server-build.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(before).hexdigest(),sha256=hashlib.sha256((W/'enhancement_protection40.py').read_bytes()).hexdigest(),state_written=False),indent=2),encoding='utf8')
print('Prepared independent protection plus booster transaction; official files unchanged')
