"""Atomic same-SKU random player-pack opening; normal and choice use stay native."""

def open_pack(host, query, body):
    import json
    try:
        request = json.loads(body or b'{}')
    except (ValueError, TypeError, UnicodeError):
        return host._json({'result': False, 'reason': 'INVALID_PARAM'})
    if not isinstance(request, dict):
        return host._json({'result': False, 'reason': 'INVALID_PARAM'})
    if 'bulk' not in request:
        return host.ep_item_use(host.hot_path_params['item_id'], query, body)
    return bulk_open(host, request, host.hot_path_params['item_id'])

def bulk_open(host, request, token):
    import copy
    import re
    if (request.get('bulk') is not True or set(request) != {'bulk', 'requestId', 'expectedRemains'}
            or not isinstance(request.get('requestId'), str)
            or not re.fullmatch(r'[A-Za-z0-9_-]{16,96}', request['requestId'])
            or type(request.get('expectedRemains')) is not int or request['expectedRemains'] <= 0):
        return host._json({'result': False, 'reason': 'INVALID_PARAM'})
    with host.STATE_LOCK:
        # A detached transaction is also safe when a host caches its read snapshot.
        state = copy.deepcopy(host._state())
        coach = host.my_coach(state)
        slot = host._default_slot(state)
        owner = [str(coach['_id']), str(coach.get('appat')), str(coach.get('_admin_generation'))]
        fingerprint = {'token': token, 'expectedRemains': request['expectedRemains'], 'owner': owner}
        saved = coach.get('bulk_player_pack_receipts', {}).get(request['requestId'])
        if saved is not None:
            if saved['request'] != fingerprint:
                return host._json({'result': False, 'reason': 'INVALID_PARAM'})
            return host._json(dict(saved['response'], replayed=True,
                                   items=host.coach_items(state, slot),
                                   playerCount=len(state['teams'][str(slot)]['players']),
                                   resources=host.coach_me_resources(state, slot)))
        visible = next((row for row in host.coach_items(state, slot)
                        if str(row['_id']) == token and row.get('remains', 0) > 0), None)
        if visible is None:
            return host._json({'result': False, 'reason': 'INVALID_ITEM'})
        itemid = int(visible['itemid'])
        definition = host.item_def(itemid)
        product = host.product_packs
        risk = product.get('risk_packs', {}).get(str(itemid)) or product.get('strength_packs', {}).get(str(itemid))
        catalogue = host.pack_catalogue.get('items', {}).get(str(itemid))
        if (itemid not in host.PACKS or definition.get('category') != 'PLAYERPACK'
                or definition.get('draft') or risk and risk.get('mode') == 'choice'
                or catalogue and catalogue.get('mode') == 'choice'):
            return host._json({'result': False, 'reason': 'INVALID_ITEM'})
        stacks = [item for item in coach.get('items', []) if item['itemid'] == itemid and item['remains'] > 0]
        available = sum(item['remains'] for item in stacks)
        if available != request['expectedRemains']:
            return host._json({'result': False, 'reason': 'PACK_STOCK_CHANGED',
                               'resources': host.coach_me_resources(state, slot)})
        team = state['teams'][str(slot)]
        count = min(available, max(0, host.MAX_PLAYERS - len(team['players'])))
        if count == 0:
            return host._json({'result': False, 'reason': 'Exceed plyer limit'})
        players = []
        # Capture the original stock: any cadence exchange reward is for a later click.
        left = count
        for item in stacks:
            take = min(item['remains'], left)
            for unused in range(take):
                players.append(bulk_draw(host, state, coach, team, itemid))
            if take:
                if risk:
                    item['product_open_seq'] = item.get('product_open_seq', 0) + take
                item['remains'] -= take
                if item['remains'] == 0:
                    coach['items'].remove(item)
            left -= take
            if not left:
                break
        remaining = sum(item['remains'] for item in coach.get('items', []) if item['itemid'] == itemid)
        response = {'result': True, 'players': players, 'opened': count, 'remaining': remaining,
                    'itemid': itemid, 'limitedByCapacity': count < available,
                    'playerCount': len(team['players'])}
        coach.setdefault('bulk_player_pack_receipts', {})[request['requestId']] = {
            'request': fingerprint, 'response': copy.deepcopy(response)}
        resources = host.coach_me_resources(state, slot)
        items = host.coach_items(state, slot)
        # Cards, inventory, pity/marks, and replay receipt commit exactly once together.
        host._save(state)
        return host._json(dict(response, items=items, resources=resources))

def bulk_draw(host, state, coach, team, itemid):
    product = host.product_packs
    risk = product.get('risk_packs', {}).get(str(itemid)) or product.get('strength_packs', {}).get(str(itemid))
    catalogue = host.pack_catalogue.get('items', {}).get(str(itemid))
    cadence = host.pack_cadence
    data = cadence.items.get(itemid)
    origin = None
    if risk:
        tier = host.random.choices(risk['tiers'], [row['weight'] for row in risk['tiers']])[0]
        spid = host.random.choice(tier['pool'])
        grade = host.random.choices(range(1, len(risk['grades']) + 1), risk['grades'])[0]
        origin = ('product_pack_origin', {'edition': product['edition'], 'itemid': itemid, 'tier': tier['name']})
    elif catalogue:
        spid = host.random.choice(catalogue['pool'])
        grade = 1
        origin = ('pack_catalogue_origin', {'itemid': itemid, 'edition': host.pack_catalogue['edition'], 'mode': catalogue['mode']})
    elif data:
        ledger = cadence.ledger(coach)
        pity = data.get('pity')
        if pity and ledger['pity'].get(pity['key'], 0) >= pity['after'] - 1:
            tier = next(row for row in data['tiers'] if row['name'] == pity['tier'])
        else:
            tier = host.random.choices(data['tiers'], [row['chance'] for row in data['tiers']])[0]
        row = host.random.choices(tier['pool'], [row[1] for row in tier['pool']])[0]
        spid = row[0]
        grade = host.random.choices(range(1, len(data['grades']) + 1), data['grades'])[0]
        origin = ('pack_cadence_origin', {'edition': data['version'], 'itemid': data['itemid'],
                  'tier': tier['name'], 'issued_at': host.w3c(host.time.time())})
        if pity:
            ledger['pity'][pity['key']] = 0 if tier['name'] == pity['tier'] else ledger['pity'].get(pity['key'], 0) + 1
        ledger['marks'] += data['marks']
        ledger['opens'][str(data['itemid'])] = ledger['opens'].get(str(data['itemid']), 0) + 1
    else:
        pool = host.pack_pool(itemid)
        if not pool:
            raise ValueError('Random pack pool is empty')
        spid = host.random.choices([row[0] for row in pool], [row[1] for row in pool])[0]
        grade = host.pack_grade(itemid)
    card = host.add_player(team, spid, grade)
    if origin:
        card[origin[0]] = origin[1]
    if data and not risk and not catalogue:
        cadence.exchange(state)
    price = host.player_value_price(spid, grade) if risk or not catalogue and not data else host.card_price(spid, grade)
    return {'_id': card['_id'], 'spid': spid, 'grade': grade, 'price': price}
