"""Keep native Special Offers aligned with the currently published cash catalogue."""
import copy
import functools

PATHS = ('/specifictarget', '/shop/list/STSHOP', '/shop/remained/limited/STSHOP')


def install(h):
    if getattr(h, '_shop_recommendation_fix_installed', False):
        return
    original_file = h.from_file

    def rows():
        st = h._state()
        cadence = getattr(h, 'pack_cadence', None)
        candidates = []
        seen = set()
        for order, row in enumerate(h.shop_list(st)):
            i = int(row['product']['itemid'])
            data = row['product']['staticdata']
            if (i in seen or i in h.SHOP_HIDDEN or row.get('shopcategory') != 'PLAYERPACK'
                    or not row.get('visible', True) or row.get('buy') is False
                    or data.get('currency') != 'cash'
                    or not any(b.get('price', 0) > 0 for b in data.get('bunches', []))):
                continue
            if cadence and (not cadence.active(i) or cadence.policy(i)[1]):
                continue
            seen.add(i)
            candidates.append((row.get('new', 1000000 + order), order, row))
        result = []
        for _, _, row in sorted(candidates, key=lambda x: x[:2])[:4]:
            entry = copy.deepcopy(row)
            special_id = h.STSHOPID + int(entry['product']['itemid'])
            entry.update(_id=str(special_id), shopid=special_id, stid=special_id)
            result.append(entry)
        return result

    def response(path):
        entries = rows()
        if path == PATHS[0]:
            return h._json({'issell': bool(entries), 'targets': [
                {'stid': e['stid'], 'endtime': e['saleend']} for e in entries]})
        if path == PATHS[1]:
            return h._json(entries)
        return h._json([{'shopid': e['shopid'], 'remained': e.get('remained',
                        e.get('remainedperaccount', 2147483647))} for e in entries])

    @functools.wraps(original_file)
    def from_file(path):
        # HTTP dispatch gives response files priority over ENDPOINTS. Override both.
        if path in PATHS:
            return response(path)
        return original_file(path)

    h.from_file = from_file
    for path in PATHS:
        h.ENDPOINTS[path] = lambda q, b, path=path: response(path)
    h.ep_specifictarget = h.ENDPOINTS[PATHS[0]]
    h.ep_stshop = h.ENDPOINTS[PATHS[1]]
    h.shop_recommendation_rows = rows
    h._shop_recommendation_fix_installed = True
