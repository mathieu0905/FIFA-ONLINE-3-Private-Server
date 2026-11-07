"""Private candidate: manager-bound, atomic, replay-safe local admin grants.

Install AFTER economy and the other admin adapters. No state migration on install.
Only cash/ep/give_pack are changed. Receipts never evict silently (4096 limit).
"""
import copy
import functools
import hashlib
import json
import re
import secrets

RECEIPT_LIMIT = 4096


def install(hc):
    if getattr(hc, '_admin_grant_guard_installed', False):
        return
    import admin

    # coach_id(slot) is reusable and appat has only second precision. A nonce
    # belongs to the coach lifecycle, including recreation in the same second.
    previous_save = hc._save

    @functools.wraps(previous_save)
    def save_with_generation(st):
        for current in st.get('coaches', []):
            generation = current.get('_admin_generation')
            if not isinstance(generation, str) or not re.fullmatch('[0-9a-f]{32}', generation):
                current['_admin_generation'] = secrets.token_hex(16)
        return previous_save(st)

    hc._save = save_with_generation

    def identity(current):
        return {'id': str(current['_id']), 'slot': current['slot'],
                'appat': current.get('appat'), 'generation': current['_admin_generation']}

    original_summary = admin.API['summary']

    def summary(params):
        with hc.STATE_LOCK:
            st = hc._state()
            current = hc.my_coach(st)
            if not isinstance(current.get('_admin_generation'), str) or not re.fullmatch('[0-9a-f]{32}', current['_admin_generation']):
                hc._save(st)  # metadata only, once for a pre-existing lifecycle
            out = original_summary(params)
            out['admin_target'] = identity(current)
            return out

    admin.API['summary'] = summary
    admin.summary = summary

    def grantables(params):
        # Keep the Bag pack selector's existing PACKS contract unchanged.
        rows = [{'itemid': item, 'name': name, 'type': 'PLAYER_PACK'}
                for item, (name, _) in hc.PACKS.items()]
        for item, (name, _, kind, effect, _) in hc.ITEMS.items():
            if kind == 'PLAYER_EXP_CAPSULE':
                name = f'球员经验券 {effect["exp"]:,} EXP · ' + name
            elif kind == 'COACH_EXP_CAPSULE':
                name = f'经理经验券 {effect["exp"]:,} EXP · ' + name
            rows.append({'itemid': item, 'name': name, 'type': kind})
        return {'items': rows}

    admin.API['grantables'] = grantables
    admin.READ_ONLY.add('grantables')
    admin.I18N['zh']['item_give'] = '发放道具或球员卡包'

    class Rejected(admin.AdminError):
        pass

    def fail(message):
        raise Rejected(message)

    def integer(value, low, high, name):
        if type(value) is not int or not low <= value <= high:
            fail(name + ' 必须是范围内的整数')
        return value

    def perform_grant(name, params):
        with hc.STATE_LOCK:
            st = hc._state()
            current = hc.my_coach(st)
            target = params.get('_admin_target')
            operation = params.get('_admin_operation')
            if (not isinstance(target, dict) or set(target) != {'id', 'slot', 'appat', 'generation'}
                    or type(target['slot']) is not int or not isinstance(target['id'], str)
                    or not isinstance(target['generation'], str)
                    or not re.fullmatch('[0-9a-f]{32}', target['generation'])):
                fail('请刷新后台，确认当前经理后再操作')
            if not isinstance(operation, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', operation):
                fail('操作编号无效，请刷新后台')
            payload = {k: v for k, v in params.items() if not k.startswith('_admin_')}
            digest = hashlib.sha256(json.dumps([name, target, payload], sort_keys=True,
                                               separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
            receipts = st.get('_admin_grant_receipts', {})
            old = receipts.get(operation)
            if old:
                if old['digest'] != digest:
                    fail('操作编号已用于其他发放，请刷新后台')
                return copy.deepcopy(old['result'])
            if not current.get('_admin_generation') or target != identity(current):
                fail('当前经理已切换，请刷新后台确认收件经理')
            if current.get('state') != 'active':
                fail('当前经理不在启用状态，不能发放')
            if len(receipts) >= RECEIPT_LIMIT:
                fail('发放审计记录已满；请先归档，记录不会自动清除')
            if name in ('cash', 'ep'):
                cap = 10 ** 9 if name == 'cash' else admin.EP_ADMIN_LIMIT
                def amount(value, low):
                    if name == 'cash':
                        return integer(value, low, cap, name)
                    try:
                        return admin.ep_integer(value, low, cap)
                    except admin.AdminError:
                        fail('EP 必须是 ' + str(low) + ' 到 ' + str(cap) + ' 范围内的整数')
                if 'set' in payload:
                    value = amount(payload['set'], 0)
                    current[name] = value
                else:
                    value = amount(payload.get('add'), -cap)
                    if name == 'cash':
                        hc.add_cash(st, value, 'admin:' + operation)
                    else:
                        hc.add_ep(st, value)
                        current['ep'] = max(0, current['ep'])
                result = {name: hc.cash_balance(current) if name == 'cash' else current['ep']}
                if name == 'ep':
                    result['ep_exact'] = str(current['ep'])
            else:
                item = integer(payload.get('itemid'), 1, 10 ** 10, '道具编号')
                count = integer(payload.get('count', 1), 1, 999, '数量')
                if item not in hc.PACKS and item not in hc.ITEMS:
                    fail('未知道具')
                admin.give_pack(st, item, count)
                result = {'ok': True}
            st.setdefault('_admin_grant_receipts', {})[operation] = {
                'digest': digest, 'target': target, 'api': name,
                'payload': copy.deepcopy(payload),
                'result': copy.deepcopy(result), 'at': hc.w3c(hc.time.time())}
            hc._save(st)  # grant and receipt persist in the SAME atomic state save
            return result

    def grant(name, params):
        try:
            return perform_grant(name, params)
        except Rejected as exc:
            # Only our PRE-SAVE checks are definite rejections. Persistence or
            # response exceptions are ambiguous and must keep the same UUID.
            return {'error': exc.text('zh'), 'admin_grant_rejected': True}

    for name in ('cash', 'ep', 'give_pack'):
        admin.API[name] = lambda p, n=name: grant(n, p)
    hc._admin_grant_guard_installed = True
