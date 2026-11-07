"""Chinese native shop descriptions, derived from the actual immutable draw rules.

Install after economy, cadence, localization and popup compatibility adapters.
No draw weights, prices, inventory, player state or client archives are changed.
"""
import functools
import html


GROUP_LABELS = {
    'star_day': '每日名将', 'legend_week': '每周传奇',
    'peak_week': '每周巅峰', 'direct_week': '经典直达复刻',
    'high_grade_week': '经典高强',
    'classic_month': '经典精选固定+10月供应',
}
POSITION_LABELS = {'FW': '前锋', 'MF': '中场', 'DF': '后卫', 'GK': '门将'}
SEASON_LABELS = {13: 'FC精选移植', 88: '17赛季', 91: '世界最佳', 93: '世界传奇'}


def percentage(value):
    return f'{100 * value:.2f}'.rstrip('0').rstrip('.') + '%'


def probability_line(grades):
    total = sum(weight for _, weight in grades)
    if total <= 0:
        return '暂不可开启：强化概率配置无效。'
    return '；'.join(f'+{grade}：{percentage(weight / total)}'
                    for grade, weight in grades if weight > 0)


def install(hc):
    if getattr(hc, '_pack_descriptions_installed', False):
        return
    original_item = hc.item_def
    original_apply = hc.apply_shop
    cache = {}

    def escape(value):
        return html.escape(str(value), quote=False)

    def supply_lines(cadence, itemid):
        units, archived = cadence.policy(itemid)
        if archived:
            return ['旧版已停售；背包中已持有的卡包仍按原发行概率开启。']
        if not units:
            return []
        lines = ['共享供应以整个账号计算，切换经理不重置：']
        for group, used in sorted(units.items()):
            period = '自然WIB月' if group.endswith('_month') else '每日' if group.endswith('_day') else '每周'
            cap = cadence.config['limits'][group]
            lines.append(f'{GROUP_LABELS.get(group, escape(group))}：{period}{cap}份；购买本商品占{used}份。')
        if any(group.endswith('_day') for group in units):
            lines.append('日供应每日北京时间凌晨1点刷新。')
        if any(group.endswith('_week') for group in units):
            lines.append('周供应每周一北京时间凌晨1点刷新。')
        if any(group.endswith('_month') for group in units):
            lines.append('月供应按自然WIB月计算，每月月初北京时间凌晨1点刷新。')
        return lines

    def describe(itemid):
        if itemid in cache:
            return cache[itemid]
        name, rule = hc.PACKS[itemid]
        grades = [(int(g), float(w)) for g, w in hc.pack_grades(itemid) if w > 0]
        pool = [(int(s), float(w)) for s, w in hc.pack_pool(itemid) if w > 0]
        lines = [escape(name), '每包获得1名球员。']
        cadence = getattr(hc, 'pack_cadence', None)
        edition = cadence.items.get(itemid) if cadence else None
        if not pool:
            lines.append('当前卡池为空，暂不可开启；请勿购买。')
        elif edition:
            count = len({row[0] for tier in edition['tiers'] for row in tier['pool']})
            lines.append(f'本发行卡池共{count}张不同赛季卡；以下为未触发保底时的档位概率：')
            seasons = sorted({row[0] // 1000000 for tier in edition['tiers'] for row in tier['pool']})
            labels = dict(SEASON_LABELS)
            for label, codes, _ in getattr(hc, 'FA_SEASONS', ()):
                for code in codes:
                    labels.setdefault(code, label + '赛季')
            lines.append('实际赛季：' + '、'.join(escape(labels.get(s, f'{s}赛季')) + f'（{s}）' for s in seasons) + '。')
            if all(row[4] > 100 for tier in edition['tiers'] for row in tier['pool']):
                lines.append('不包含本期能力前100。')
            native_rank = edition.get('rank_basis') == 'native_plus1_ovr'
            if native_rank:
                lines.append('本期排名按原生等级1、+1能力降序，同分按球员卡编号升序；同一真人的不同赛季卡分别排名。')
            else:
                lines.append('本期排名按+1稳定参考价值排列，同价按球员卡编号排序。')
            for tier in edition['tiers']:
                rows = tier['pool']
                label = '进阶档' if tier['name'] in ('rare', 'hit') else '常规档'
                rating_min, rating_max = min(r[3] for r in rows), max(r[3] for r in rows)
                ranks = [r[4] for r in rows]
                rank_label = '原生+1能力排名' if native_rank else '参考价值排名'
                lines.append(f'{label} {percentage(tier["chance"])}：{rank_label}{min(ranks)}～{max(ranks)}，'
                             f'{len(rows)}张，基础OVR{rating_min - hc.GRADE_BOOST[1]:g}～{rating_max - hc.GRADE_BOOST[1]:g}，'
                             f'+1评分{rating_min:g}～{rating_max:g}。')
            if edition.get('card_weight_rule') == 'uniform_within_tier':
                lines.append('先按档位概率抽档，再在该档内等概率抽取球员。')
            lines.append(f'基础OVR为球员等级1的原始能力，已剔除+1强化的{hc.GRADE_BOOST[1]}点，不含经验与球队加成。')
            if edition.get('rotation') is not None:
                lines.append(f'定向位置：{POSITION_LABELS.get(("FW", "MF", "DF", "GK")[edition["rotation"]], "指定位置")}。')
                lines.append(f'主题每{cadence.config["rotation_days"]}天轮换；已购卡包仍按购买时发行规则开启。')
            pity = edition.get('pity')
            if pity:
                lines.append(f'连续{pity["after"] - 1}包未中进阶档，第{pity["after"]}包必出进阶档；自然命中后重新累计。')
                lines.append('保底只改变球员档位，强化等级仍按下方概率独立抽取。')
            if edition.get('marks'):
                exchange = cadence.config['mark_exchange']
                lines.append(f'每次成功开包获得{edition["marks"]}印记；满{exchange["cost"]}印记自动兑换1个奖励包，'
                             f'每周最多{exchange["weekly_limit"]}个，剩余印记保留。')
                lines.append('兑换包发到背包，不自动开启，也不额外扣点券。')
            elif itemid == cadence.reward_id:
                lines.append('印记自动兑换奖励，仅发到背包，不在商城直接出售。')
        else:
            frozen_legacy = cadence is not None and itemid in cadence.legacy
            ratings = hc.card_ovrs([s for s, _ in pool])
            low = min(ratings[s] for s, _ in pool) + hc.GRADE_BOOST[1]
            high = max(ratings[s] for s, _ in pool) + hc.GRADE_BOOST[1]
            seasons = sorted({s // 1000000 for s, _ in pool})
            labels = dict(SEASON_LABELS)
            for label, codes, _ in getattr(hc, 'FA_SEASONS', ()):
                for code in codes:
                    labels.setdefault(code, label + '赛季')
            if len(seasons) <= 8:
                lines.append('可出赛季：' + '、'.join(escape(labels.get(s, f'{s}赛季')) for s in seasons) + '。')
            else:
                lines.append(f'跨{len(seasons)}个可交易赛季，具体球员范围由本包卡池决定。')
            if rule.get('pos') and not frozen_legacy:
                lines.append('限定位置：' + POSITION_LABELS.get(rule['pos'], escape(rule['pos'])) + '。')
            if rule.get('league') and not frozen_legacy:
                lines.append('仅包含本包指定联赛的球员。')
            if rule.get('top') and not frozen_legacy:
                lines.append(f'在本包筛选范围内取评分前{rule["top"]}张（实际{len(pool)}张）。')
            else:
                lines.append(f'本包共有{len(pool)}张候选赛季卡。')
            lines.append(f'+1评分范围：{low:g}～{high:g}。')
        if grades:
            minimum = min(g for g, _ in grades)
            maximum = max(g for g, _ in grades)
            lines.append('强化概率：' + probability_line(grades) + '。')
            if minimum == maximum:
                lines.append(f'固定获得+{minimum}强化球员。')
            elif maximum > 1:
                lines.append(f'最低+{minimum}，最高+{maximum}。')
                lines.append(f'最高+{maximum}是随机上限，并非保证开出+{maximum}。')
        lines.append('评分按球员等级1、+1强化计算，不含经验成长与球队加成。')
        lines.append('球员按卡池权重随机，各球员概率可能不同；强化等级独立抽取。')
        if cadence:
            lines.extend(supply_lines(cadence, itemid))
        description = '<BR>'.join(lines)
        cache[itemid] = description
        return description

    def content_lines(itemid, count, definition, depth=0):
        prefix = '　' * depth
        lines = [f'{prefix}{escape(definition["name"])} ×{count}']
        if itemid in hc.PACKS:
            text = describe(itemid).split('<BR>')
            keep = ('本包共有', '本发行卡池', '可出赛季', '实际赛季', '基础OVR', '先按档位', '跨', '限定位置', '定向位置',
                    '+1评分', '强化概率', '最高+', '不包含', '进阶档', '常规档',
                    '最低+', '固定获得', '连续', '每次成功开包', '本期排名')
            lines.extend(prefix + line for line in text if line.startswith(keep))
            lines.append(prefix + '每个卡包单独开启获得1名球员；候选按权重随机。')
            cadence = getattr(hc, 'pack_cadence', None)
            if cadence and itemid in cadence.items and itemid != cadence.reward_id:
                lines.append(prefix + f'商城单包标价{hc.product_price(itemid, 1):,}点券；本档按礼包总价结算。')
        elif itemid in hc.ITEMS:
            _, _, kind, effect, _ = hc.ITEMS[itemid]
            if kind == 'ITEM_LOTTERY':
                prizes = effect.get('prizes', ())
                total = sum(w for w, _ in prizes)
                lines.append(prefix + '每个随机箱开启仅获得下列其中一项：')
                for weight, prize in prizes:
                    lines.append(prefix + '中奖概率' + percentage(weight / total) + '：')
                    if isinstance(prize, (tuple, list)):
                        lines.append(prefix + f'{prize[1]:,} EP')
                    else:
                        lines.extend(content_lines(prize, 1, hc.item_def(prize), depth + 1))
            elif kind == 'EP_LOTTERY' and 'ep' in effect:
                low, high = effect['ep']
                lines.append(prefix + f'每个开启获得{low:,}～{high:,} EP。')
            else:
                description = definition.get('description')
                if description:
                    lines.append(prefix + description)
        elif itemid in (getattr(hc, 'EP_ITEM', -1), getattr(hc, 'ES_ITEM', -1)):
            lines.append(prefix + '购买时直接入账。')
        else:
            for child in definition.get('items', ()):
                lines.extend(content_lines(child['itemid'], child['count'], child['staticdata'], depth + 1))
        return lines

    def chain_description(itemid, definition):
        first, index = hc.CHAIN_STEPS[itemid]
        steps = hc.CHAINED[first]
        price = hc.product_price(itemid, 1)
        cumulative = sum(hc.product_price(i, 1) for i in steps[:index + 1])
        lines = [escape(definition['name']), f'连锁第{index + 1}/{len(steps)}档。',
                 f'本档礼包1份：{price:,}点券；从第1档买到本档累计{cumulative:,}点券。',
                 f'整条连锁全部购买合计{sum(hc.product_price(i, 1) for i in steps):,}点券。',
                 '全账号每档终生仅可购买1次，切换经理不重置。',
                 '后续档位由首次购买本连锁的经理继续购买。',
                 '按顺序购买；需先购齐前面各档。' if index else '首档可直接购买，购买后解锁下一档。',
                 '以下为本档实际获得内容；卡包与随机箱发到背包，需自行开启，不会自动抽球员：']
        for child in definition.get('items', ()):
            lines.extend(content_lines(child['itemid'], child['count'], child['staticdata']))
        if index == 3 and getattr(hc, 'chain_five', {}).get('rotation') is False:
            lines.append('本档定向包固定为首期前锋卡池，不随商城主题轮换。')
        lines.append('评分按球员等级1、+1强化计算，不含经验成长与球队加成。')
        cadence = getattr(hc, 'pack_cadence', None)
        if cadence:
            children = definition.get('items', ())
            if children and all(child['itemid'] in cadence.items for child in children):
                reference = sum(hc.product_price(child['itemid'], 1) * child['count'] for child in children)
                lines.append(f'内容按商城单包标价合计{reference:,}点券；本档实际支付{price:,}点券。')
            lines.extend(supply_lines(cadence, itemid))
            if not cadence.policy(itemid)[0]:
                lines.append('本档不占普通卡包每日、每周供应额度。')
        return '<BR>'.join(lines)

    @functools.wraps(original_item)
    def item_def(itemid):
        out = dict(original_item(itemid))
        if itemid in hc.PACKS:
            description = describe(itemid)
            cadence = getattr(hc, 'pack_cadence', None)
            if not cadence or itemid != cadence.reward_id:
                prices = [f'{b["bunch"]}包合计{b["price"]:,}点券' for b in out.get('bunches', ())]
                if prices:
                    description += '<BR>当前购买价格：' + '；'.join(prices) + '。'
            out['description'] = description
        elif itemid in getattr(hc, 'CHAIN_STEPS', {}):
            out['description'] = chain_description(itemid, out)
        return out

    @functools.wraps(original_apply)
    def apply_shop(cfg=None):
        result = original_apply(cfg)
        cache.clear()
        return result

    hc.item_def = item_def
    hc.apply_shop = apply_shop
    hc.describe_player_pack = describe
    hc._pack_descriptions_installed = True
