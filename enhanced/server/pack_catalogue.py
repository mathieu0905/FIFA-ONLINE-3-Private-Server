"""Frozen season packs and native one-player choices. Install after shop adapters."""
import copy
import datetime
import functools
import hashlib
import hmac
import json
import math
import re
from pathlib import Path
from urllib.parse import parse_qs


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def install(h):
    if getattr(h, '_pack_catalogue_installed', False):
        return
    config = json.loads((Path(h.HERE) / 'gamedata/pack_catalogue.json').read_text(encoding='utf-8'))
    if config['schema'] != 1 or config['hash'] != signature({k: v for k, v in config.items() if k != 'hash'}):
        raise ValueError('Invalid season pack catalogue signature')
    entries = {int(k): v for k, v in config['items'].items()}
    eligible = set(h.market_spids())
    for itemid, data in entries.items():
        if itemid in h.PACKS or itemid in h.ITEMS or itemid in h.PACKAGES:
            raise ValueError('Season pack ID collision')
        if not data['pool'] or not set(data['pool']) <= eligible or len(set(data['pool'])) != len(data['pool']):
            raise ValueError('Invalid frozen season pool')
        if not isinstance(data['price'], int) or data['price'] < 1 or data['mode'] not in ('random', 'choice'):
            raise ValueError('Invalid season pack rule')
    previous_pool, previous_grades, previous_price = h.pack_pool, h.pack_grades, h.product_price
    previous_item, previous_entry, previous_apply = h.item_def, h.shop_entry, h.apply_shop
    previous_policy, previous_remaining = h.pack_cadence.policy, h.pack_cadence.remaining
    previous_inventory, previous_move = h.coach_items, h.stack_move
    original_use = h.ep_item_use

    def period(group):
        day = datetime.date.fromisoformat(h.today_wib())
        return (day - datetime.timedelta(days=day.weekday())).isoformat() if group == 'choice_week' else day.isoformat()

    def remaining(st, itemid):
        if getattr(h, '_per_product_limits', False) and itemid in entries:
            return h.item_purchase_remaining(st, itemid)
        if itemid not in entries:
            return previous_remaining(st, itemid)
        group = entries[itemid]['supply']
        saved = st.get('pack_catalogue_supply', {}).get(group, {})
        used = saved.get('used', 0) if saved.get('period') == period(group) else 0
        return max(0, config['limits'][group] - used)

    def policy(itemid, trail=()):
        # These separately versioned packs have their own account quotas.
        return ({}, False) if itemid in entries else previous_policy(itemid, trail)

    def register():
        for itemid, data in entries.items():
            h.PACKS[itemid] = (data['name'], {'all': True, 'grade': 1, 'icon': data['icon']})
        order = sorted(entries, key=lambda i: (entries[i]['order'], i))
        h.SHOP_NEW = tuple(order) + tuple(i for i in h.SHOP_NEW if i not in entries)

    def pool(itemid):
        return [(spid, 1.0) for spid in entries[itemid]['pool']] if itemid in entries else previous_pool(itemid)

    def grades(itemid):
        return [(1, 1)] if itemid in entries else previous_grades(itemid)

    def price(itemid, count, value=lambda: 0):
        return entries[itemid]['price'] * count if itemid in entries else previous_price(itemid, count, value)

    def definition(itemid):
        if itemid not in entries:
            return previous_item(itemid)
        data = entries[itemid]
        out = previous_item(itemid)
        out.update(name=data['name'], description=data['description'], itemicon=data['icon'], bundleicon=data['icon'],
                   category='DRAFTPACK' if data['mode'] == 'choice' else 'PLAYERPACK',
                   type='CUSTOM', bunches=[{'bunch': 1, 'price': data['price']}])
        if data['mode'] == 'choice':
            out['draft'] = {'season': data['seasons'][0] if len(data['seasons']) == 1 else 0, 'grade': 1, 'availables': 1}
        return out

    def entry(itemid, category='PLAYERPACK', shopid=None):
        out = previous_entry(itemid, category, shopid)
        if itemid in entries:
            left = remaining(h._state(), itemid)
            cap = h.item_purchase_limit(itemid)['count'] if getattr(h, '_per_product_limits', False) else config['limits'][entries[itemid]['supply']]
            out.update(visible=True, buy=left > 0, forceenable=False, remained=left, remainedperaccount=left,
                       limittotalcount=cap, limitcountperaccount=cap)
        return out

    def validate_purchase(st, context):
        if getattr(h, '_per_product_limits', False):
            return None
        itemid = context['itemid']
        if itemid in entries and context['bunch'] > remaining(st, itemid):
            return '本类卡包的账号共享额度已用完，请等待刷新。'

    def commit_purchase(st, context):
        if getattr(h, '_per_product_limits', False):
            return None
        itemid = context['itemid']
        if itemid in entries:
            group = entries[itemid]['supply']
            supply = st.setdefault('pack_catalogue_supply', {})
            saved = supply.get(group)
            if not saved or saved['period'] != period(group):
                saved = {'period': period(group), 'used': 0}
                supply[group] = saved
            saved['used'] += context['bunch']

    def token(coach, item):
        text = f"{coach['slot']}:{coach.get('_id', coach.get('id', ''))}:{item['_id']}:{item['itemid']}:{item['remains']}:{config['edition']}"
        digest = hmac.new(bytes.fromhex(config['token_key']), text.encode(), hashlib.sha256).hexdigest()[:24]
        return item['_id'] + '_pc_' + digest

    def inventory(st, slot, where='items'):
        out = previous_inventory(st, slot, where)
        coach = next(c for c in st['coaches'] if c['slot'] == slot)
        raw = {i['_id']: i for i in coach.get(where, [])}
        for row in out:
            data = entries.get(row['itemid'])
            if data and row['_id'] in raw:
                row['_id'] = row['id'] = token(coach, raw[row['_id']])
        return out

    def move(coach, item_id, src, dst):
        for item in coach.get(src, []):
            if item['itemid'] in entries and token(coach, item) == item_id:
                return previous_move(coach, item['_id'], src, dst)
        return previous_move(coach, item_id, src, dst)

    def owned(coach, itemid):
        return next((i for i in coach.get('items', []) if i['itemid'] == itemid and i['remains'] > 0), None)

    def choices(itemid, count, query, body):
        itemid, count = int(itemid), int(count)
        data = entries.get(itemid)
        with h.STATE_LOCK:
            coach = h.my_coach(h._state())
            if not data or data['mode'] != 'choice' or not owned(coach, itemid):
                return h._json([])
            # The native draft screen keeps the chosen one locally. Count=1 initializes an empty selection.
            spids = [] if count == 1 else data['pool']
            return h._json([{'spid': s, 'grade': 1, 'expandme': 'player'} for s in spids])

    def search(itemid, query, body):
        itemid = int(itemid)
        data = entries.get(itemid)
        with h.STATE_LOCK:
            if not data or data['mode'] != 'choice' or not owned(h.my_coach(h._state()), itemid):
                return h._json([])
            q = parse_qs(query.lstrip('?'))
            text = q.get('q', [''])[0].strip().casefold()
            try:
                league = int(q.get('league', ['255'])[0])
                team = int(q.get('team', ['255'])[0])
            except (ValueError, TypeError):
                return h._json([])
            rows = data['pool']
            if text or league not in (255, -1, 0) or team not in (255, -1, 0):
                rows = [s for s in rows if (not text or text in data['search'][str(s)]['name'].casefold())
                        and (league in (255, -1, 0) or data['search'][str(s)]['league'] == league)
                        and (team in (255, -1, 0) or data['search'][str(s)]['team'] == team)]
            return h._json([{'spid': s, 'grade': 1, 'price': h.card_price(s, 1), 'expandme': 'player'} for s in rows])

    def use(item_id, query, body):
        with h.STATE_LOCK:
            st = h._state()
            coach = h.my_coach(st)
            receipts = coach.get('pack_catalogue_receipts', {})
            try:
                req = json.loads(body or b'{}')
                chosen = req.get('spids')
                if not isinstance(req, dict):
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                return h._json({'result': False, 'reason': 'INVALID_PARAM'})
            if item_id in receipts:
                saved = receipts[item_id]
                if chosen != saved['chosen']:
                    return h._json({'result': False, 'reason': 'INVALID_PARAM'})
                return h._json({'result': True, 'player': saved['player'], 'replayed': True,
                                'resources': h.coach_me_resources(st, h._default_slot(st))})
            item = next((i for i in coach.get('items', []) if i['remains'] > 0 and
                         (i['_id'] == item_id or (i['itemid'] in entries and token(coach, i) == item_id))), None)
            if item is None or item['itemid'] not in entries:
                if '_pc_' in item_id:
                    return h._json({'result': False, 'reason': 'INVALID_ITEM'})
                return original_use(item_id, query, body)
            data = entries[item['itemid']]
            if token(coach, item) != item_id:
                return h._json({'result': False, 'reason': 'INVALID_PARAM'})
            slot = h._default_slot(st)
            team = st['teams'][str(slot)]
            if len(team['players']) >= h.MAX_PLAYERS:
                return h._json({'result': False, 'reason': 'Exceed plyer limit'})
            if data['mode'] == 'choice':
                if token(coach, item) != item_id or not isinstance(chosen, list) or len(chosen) != 1 or type(chosen[0]) is not int or chosen[0] not in data['pool']:
                    return h._json({'result': False, 'reason': 'INVALID_PARAM'})
                spid = chosen[0]
            else:
                spid = h.random.choice(data['pool'])
            card = h.add_player(team, spid, 1)
            card['pack_catalogue_origin'] = {'itemid': item['itemid'], 'edition': config['edition'], 'mode': data['mode']}
            result = {'_id': card['_id'], 'spid': spid, 'grade': 1, 'price': h.card_price(spid, 1)}
            coach.setdefault('pack_catalogue_receipts', {})[item_id] = {'player': result, 'chosen': chosen}
            item['remains'] -= 1
            if item['remains'] == 0:
                coach['items'].remove(item)
            h._save(st)
            return h._json({'result': True, 'player': result, 'resources': h.coach_me_resources(st, slot)})

    @functools.wraps(previous_apply)
    def apply_shop(cfg=None):
        result = previous_apply(cfg)
        register()
        return result

    h.pack_pool, h.pack_grades, h.product_price = pool, grades, price
    h.item_def, h.shop_entry, h.apply_shop = definition, entry, apply_shop
    h.pack_cadence.policy, h.pack_cadence.remaining = policy, remaining
    h.coach_items, h.stack_move = inventory, move
    h.ep_item_use = use
    h.ROUTES[:] = [(pattern, use if fn is original_use else fn) for pattern, fn in h.ROUTES]
    h.ROUTES.extend([(re.compile(r'/item/draftpack/(\d+)/players/(\d+)'), choices),
                     (re.compile(r'/packchoice/(\d+)/search'), search)])
    h.register_shop_purchase_hook('validate', validate_purchase)
    h.register_shop_purchase_hook('before_commit', commit_purchase)
    h.pack_catalogue = config
    register()
    h._pack_catalogue_installed = True
