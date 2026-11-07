"""EXP capsule audit additions and player EXP transfer, for FO3ID 654420.
Install once after http_config's definitions, before server startup. Does not write state
on install; all mutation happens through the normal /item/<id>/use transaction.
"""
import functools
import math

TRANSFER = 'PLAYER_EXP_TRANSFERENCE'


def install(hc):
    if getattr(hc, '_experience_transfer_installed', False):
        return
    hc.SHOP_ITEM_TYPES = tuple(dict.fromkeys((*hc.SHOP_ITEM_TYPES, TRANSFER)))
    original_from, original_to = hc.item_from, hc.item_to
    original_def, original_use = hc.use_item_def, hc.use_item

    def valid_rate(v):
        if isinstance(v, bool):
            raise ValueError('invalid EXP transfer rate')
        rate = float(v)
        if not math.isfinite(rate) or not 0 < rate <= 1:
            raise ValueError('EXP transfer rate must be between 0 and 1')
        return rate

    @functools.wraps(original_from)
    def item_from(v):
        if v['type'] != TRANSFER:
            return original_from(v)
        return (str(v['name']), v.get('icon') or '', TRANSFER,
                {'rate': valid_rate(v.get('rate', 1))}, str(v.get('description') or ''))

    @functools.wraps(original_to)
    def item_to(entry):
        result = original_to(entry)
        if entry[2] == TRANSFER:
            result['rate'] = entry[3]['rate']
        return result

    @functools.wraps(original_def)
    def use_item_def(itemid, prizes=True):
        result = original_def(itemid, prizes)
        if hc.ITEMS[itemid][2] == TRANSFER:
            result['transferencerate'] = hc.ITEMS[itemid][3]['rate']
        return result

    @functools.wraps(original_use)
    def use_item(st, slot, coach, it, req):
        if hc.ITEMS[it['itemid']][2] != TRANSFER:
            return original_use(st, slot, coach, it, req)
        failure = {'result': False, 'reason': 'ITEM_USE_ERROR'}
        count = req.get('count', 1)
        # One transfer has exactly two selected cards. Bulk requests cannot repeat it.
        if isinstance(count, bool):
            return failure
        try:
            if float(count) != 1:
                return failure
        except (TypeError, ValueError, OverflowError):
            return failure
        players = st.get('teams', {}).get(str(slot), {}).get('players', [])
        target = next((p for p in players if hc.iid(p) == str(req.get('targetid'))), None)
        material = next((p for p in players if hc.iid(p) == str(req.get('materialid'))), None)
        if target is None or material is None or target is material:
            return failure
        if target.get('locked') or material.get('locked'):
            return failure
        target_before = hc.player_levelinfo(target)
        material_before = hc.player_levelinfo(material)
        if target_before['level'] >= hc.PLAYER_MAX_LEVEL:
            return failure
        total = sum(hc.player_need(lv) for lv in range(1, material_before['level'])) + material_before['exp']
        if total <= 0:
            return {'result': False, 'reason': 'PLAYER_EXP_TRANSFERENCE_ERROR_LEVEL0'}
        rate = valid_rate(hc.ITEMS[it['itemid']][3]['rate'])
        gained = math.floor(total * rate)
        if gained <= 0:
            return failure
        _, target_after = hc.gain_exp(target, gained, hc.player_need, hc.PLAYER_MAX_LEVEL)
        material['levelinfo'] = {'level': 1, 'exp': 0}
        material_after = hc.player_levelinfo(material)
        it['remains'] -= 1
        if not it['remains']:
            coach['items'].remove(it)
        return {'result': True, 'exp': gained,
                'transference': {'material': {'before': material_before, 'after': material_after},
                                 'target': {'before': target_before, 'after': target_after}}}

    hc.item_from, hc.item_to = item_from, item_to
    hc.use_item_def, hc.use_item = use_item_def, use_item
    # SHOP_KINDS stores converter callables, so update its two cached references too.
    table, _, _ = hc.SHOP_KINDS['items']
    hc.SHOP_KINDS['items'] = (table, item_from, item_to)
    hc._experience_transfer_installed = True

    import admin
    original_check = admin.check_def

    @functools.wraps(original_check)
    def check_def(kind, d, itemid):
        if kind != 'items' or d.get('type') != TRANSFER:
            return original_check(kind, d, itemid)
        try:
            rate = valid_rate(d.get('rate', 1))
        except (TypeError, ValueError, OverflowError):
            raise admin.AdminError('e_range', 'rate', 0.01, 1)
        # Reuse the existing name/icon/description validation, without bypassing it.
        result = original_check(kind, {**d, 'type': 'ENHANCEMENT_BOOST', 'boost': rate}, itemid)
        result.pop('boost', None)
        result.update(type=TRANSFER, rate=rate)
        return result

    admin.check_def = check_def
    extend_admin_labels(admin.I18N)
    # Restore any configured transfer definitions parsed before the extension was installed.
    hc.apply_shop()


def extend_admin_labels(tables):
    labels = {
        'id': ('Transfer EXP pemain', 'Rasio EXP (%)'),
        'en': ('Player EXP transfer', 'EXP transfer (%)'),
        'zh': ('球员经验转移券', '转移经验比例（%）'),
        'th': ('โอน EXP นักเตะ', 'อัตราโอน EXP (%)'),
        'vi': ('Chuyển EXP cầu thủ', 'Tỷ lệ chuyển EXP (%)'),
        'ko': ('선수 경험치 이전', '경험치 이전 비율 (%)'),
    }
    for lang, (title, label) in labels.items():
        tables[lang].update(t_PLAYER_EXP_TRANSFERENCE=title, f_transfer_rate=label)
