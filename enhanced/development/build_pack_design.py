"""Build a design catalogue from the frozen pack pools; never writes game files."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path(r'D:\FO3ID\server')
labels = {}
tree = ast.parse((SOURCE / 'shop_season_names.py').read_text(encoding='utf-8'))
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('SEASONS', 'NAMES'):
        labels[node.targets[0].id] = ast.literal_eval(node.value)
short = {13: 'FC精选', 21: 'Tiger', 22: 'CP', 23: 'LP', 24: 'CC',
         27: 'EL', 28: 'UB', 30: 'UL', 31: 'CEL-A', 33: 'CEL-B',
         35: '16EC', 48: 'MUL', 53: '14T', 55: 'MUA', 91: 'WB', 93: 'WL'}
cfg_path = SOURCE / 'gamedata/pack_cadence.json'
raw = cfg_path.read_bytes()
cfg = json.loads(raw)
positions = {97010010: '前锋', 97010011: '中场', 97010012: '后卫', 97010013: '门将'}
top = {97010100: 100, 97010130: 30, 97010110: 10}
rows = []
for key, data in cfg['items'].items():
    itemid = int(key)
    cards = {int(r[0]) for tier in data['tiers'] for r in tier['pool'] if r[1] > 0}
    codes = sorted({spid // 1_000_000 for spid in cards})
    assert cards and all(code in short and code in labels['SEASONS'] for code in codes)
    grades = [(g, weight) for g, weight in enumerate(data['grades'], 1) if weight > 0]
    fixed = len(grades) == 1
    grade = f'固定+{grades[0][0]}' if fixed else f'+{grades[0][0]}～+{grades[-1][0]}'
    season_text = '/'.join(short[code] for code in codes)
    selector = positions.get(itemid, '')
    if itemid in top:
        selector = f'TOP{top[itemid]}'
    if itemid == 97010006:
        selector = '印记兑换'
    elif itemid == 97010209:
        selector = '连锁专属'
    name = season_text + ('·' + selector if selector else '') + '球员包·' + grade
    full_seasons = '、'.join(labels['SEASONS'][code] for code in codes)
    conditions = [f'每包随机获得1名球员；{grade}。']
    if itemid in positions:
        conditions.append('仅包含' + positions[itemid] + '位置球员。')
    if itemid in top:
        conditions.append(f'仅包含本期全卡池原生等级1、+1能力TOP{top[itemid]}赛季卡；同一真人的不同赛季分别计数。')
    elif itemid == 97010209:
        assert cards.isdisjoint({int(r[0]) for t in cfg['items']['97010100']['tiers'] for r in t['pool']})
        conditions.append('不含本期原生等级1、+1能力TOP100赛季卡；仅通过本期连锁第3档获得。')
    if itemid == 97010006:
        conditions.append(f"{cfg['mark_exchange']['cost']}印记自动兑换，奖励发到背包，不在商城单独出售。")
    if not fixed:
        conditions.append('强化概率：' + '、'.join(f'+{g}为{w / sum(v for _, v in grades):.2%}' for g, w in grades) + '；最高强化为随机上限。')
    pity = data.get('pity')
    if pity:
        conditions.append(f"连续{pity['after']-1}包未中进阶档，第{pity['after']}包必出进阶档；此保底不保证最高强化。")
    rows.append(dict(itemid=itemid, old_name=labels['NAMES'][itemid], name=name,
                     type='赛季限定随机球员包' if itemid not in top else '赛季限定能力TOP球员包',
                     season_codes=codes, season_scope=season_text, season_labels=[labels['SEASONS'][c] for c in codes],
                     candidate_cards=len(cards), description='赛季：' + full_seasons + '。\n' + '\n'.join(conditions),
                     current_price=data['price'], grades=[dict(grade=g, weight=w) for g, w in grades]))

assert len(rows) == 14 and len({r['name'] for r in rows}) == 14
document = '''# 卡包名称与类型定稿

本聊天负责卡包设计。本方案以当前发行的实际冻结卡池为依据，不修改卡池、概率、价格、已售库存或玩家数据。

## 命名规则

- 正式名称：**赛季缩写列表＋位置/TOP/领取用途（如有）＋球员包＋强化等级**。
- 不再使用“多赛季”“巅峰”“精英”等无法单独确认赛季范围的名称。
- 名字列出的赛季必须与实际可抽卡池完全一致。位置包分别核对，不能沿用通用包的赛季列表。
- 强化范围统一写“+5～+7”；固定强化写“固定+8”。TOP是球员能力筛选，不是强化等级，也不是抽取数量。
- CEL-A和CEL-B分别对应内部赛季31和33；只包含其中一个时不得统称包含两个的CEL。FC精选对应内部赛季13，Tiger对应Ultimate Tiger（21）；这两个简称用于本方案，不新增游戏赛季。

## 14种卡包

| 原名称 | 新正式名称 | 候选赛季卡数量 |
|---|---|---:|
'''
for row in rows:
    document += f"| {row['old_name']} | {row['name']} | {row['candidate_cards']} |\n"
document += '\n## 每个卡包的介绍文案\n\n'
for row in rows:
    document += f"### {row['name']}\n\n编号：{row['itemid']}。\n\n{row['description']}\n\n"
document += '''## 界面显示规则

正式名称完整保存在商品名中；列表、背包、推荐页、礼包内容使用同一套名称。长名称需要换行或通过悬停显示完整名称，不能截断后只剩泛称。

如果列表采用紧凑布局，固定使用两行：第一行显示位置/TOP/领取用途和强化等级；第二行单独显示完整“赛季：缩写列表”。赛季行必须直接可见，不让玩家进购买确认窗口才知道卡池。名称不可擅自改回“精选包”。原生界面实际空间和换行能力尚待实现时验证。

详情第一段列出全部赛季的缩写与全称，之后说明一包一人、筛选范围和固定/随机强化。完整概率、档位、保底、印记及限购规则沿用真实发行数据；简短文案不能替代发行规则披露。

套装或连锁展示每种奖励包的新正式名称与真实数量；“连锁第几档”属于礼包信息，不取代卡包自身赛季信息。旧库存保持原版本规则；如果其卡池与本期不同，按旧版本卡池另生成名称，不套用本期名称。

## 数据来源与交付状态

来源为D:\\FO3ID\\server中的gamedata/pack_cadence.json（实际卡池、强化、用途）、shop_season_names.py（已有赛季映射和显示名）。14种名称均已逐项从非零权重卡池复算赛季，并校验名称唯一。

本次交付为设计定稿和结构化目录；没有修改游戏文件、重启服务或宣称客户端已经显示新名称。当前443端口运行的是独立私有验证目录，未将本方案混入该验证环境。
'''
(ROOT / '卡包命名方案.md').write_text(document, encoding='utf-8')
(ROOT / '卡包设计目录.json').write_text(json.dumps(dict(
    status='design_final_not_deployed', edition=cfg['edition'], source=str(cfg_path),
    source_sha256=hashlib.sha256(raw).hexdigest(), packs=rows), ensure_ascii=False, indent=2), encoding='utf-8')
assert hashlib.sha256(cfg_path.read_bytes()).hexdigest() == hashlib.sha256(raw).hexdigest()
print(json.dumps(dict(status='PASS', packs=len(rows), game_files_written=False,
                     outputs=[str(ROOT / '卡包命名方案.md'), str(ROOT / '卡包设计目录.json')]), ensure_ascii=False))
