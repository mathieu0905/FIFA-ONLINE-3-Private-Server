"""FO3 chained-shop protocol repair. Install after the economy payment module.
No currency assumptions: purchases delegate to the already-installed payment handler.
"""
import functools
import json
import re


def install(hc):
    if getattr(hc, '_chain_packages_installed', False):
        return
    previous_purchase = hc.ep_shop_purchase
    previous_route = hc.route
    previous_from_file = hc.from_file

    def progress(st, first):
        steps = hc.CHAINED[first]
        try:
            done = int(hc.my_coach(st).get('chain', {}).get(str(first), 0))
        except (TypeError, ValueError, OverflowError):
            done = 0
        adapter=getattr(hc,'chain_account_progress',None)
        if callable(adapter):done=adapter(st,first,done)
        return min(len(steps), max(0, done))

    def status(st, first):
        steps = hc.CHAINED[first]
        done = progress(st, first)
        return {'step': min(done, len(steps) - 1), 'buy': done < len(steps),
                'remainedperaccount': int(done < len(steps)),
                'remained': int(done < len(steps))}

    def chained_entry(st, first):
        steps = hc.CHAINED[first]
        done = progress(st, first)
        parts = []
        for k, itemid in enumerate(steps):
            entry = dict(hc.shop_entry(itemid, 'CHAINED'),
                         index=k + 1, maxCount=len(steps),
                         limitcountperaccount=1, remainedperaccount=int(k >= done),
                         remained=int(k >= done), buy=k == done,
                         currentstep='complete' if k < done else 'activity' if k == done else 'default')
            parts.append(entry)
        # The root controls the whole chain. Marking the first bought stage as exhausted
        # makes ShopController.setChainedData incorrectly mark every later stage complete.
        # ShopChainedListItemRenderer reads this root-only field for its title;
        # it does not read product.staticdata.name (TileList.swf ABC 0xb23c2).
        title = (hc._SHOP.get('chain_names') or {}).get(str(first))
        if not isinstance(title, str) or not title.strip():
            title = hc.PACKAGES[first][0]
        return dict(parts[0], **status(st, first), chained=parts[1:], chainedproductname=title)

    def limited_rows(st=None, special=False):
        st = hc._state() if st is None else st
        if special:
            return [{'shopid': hc.STSHOPID + i, 'remained': hc.NO_LIMIT}
                    for i in hc.SPECIAL if i not in hc.SHOP_HIDDEN]
        return [dict(shopid=first, **status(st, first))
                for first in hc.CHAINED if first not in hc.SHOP_HIDDEN]

    def states(st):
        return {str(first): status(st, first) for first in hc.CHAINED}

    def reject(st):
        return hc._json({'result': False, 'reason': 'NOT_EXIST_PRODUCT', 'states': states(st)})

    @functools.wraps(previous_purchase)
    def purchase(query, body):
        try:
            req = json.loads(body or b'{}')
            if not isinstance(req, dict):
                return hc._json({'result': False, 'reason': 'INVALID_PARAM'})
            productid = int(req.get('productid') or 0)
            shopid = int(req.get('shopid') or 0)
            itemid = productid or shopid % hc.MP_SHOPID % hc.STSHOPID
        except (ValueError, TypeError, OverflowError):
            return hc._json({'result': False, 'reason': 'INVALID_PARAM'})
        if itemid not in hc.CHAIN_STEPS:
            return previous_purchase(query, body)
        # The HTTP handler serializes this validation and the delegated payment under
        # STATE_LOCK. Do not acquire its non-reentrant lock again here.
        st = hc._state()
        first, index = hc.CHAIN_STEPS[itemid]
        if first in hc.SHOP_HIDDEN or itemid in hc.SHOP_HIDDEN or index != progress(st, first):
            return reject(st)
        # The client uses the root shopid and the current stage productid. Accept the
        # stage's own id too, but never a foreign chain/storefront alias.
        if shopid and shopid not in (first, itemid):
            return reject(st)
        try:
            if isinstance(req.get('bunch'), bool) or float(req.get('bunch') or 0) != 0:
                return reject(st)
        except (ValueError, TypeError, OverflowError):
            return reject(st)
        result = previous_purchase(query, body)
        out = json.loads(result[1])
        if out.get('result'):
            current = hc._state()
            # Existing EP and the point-economy purchase implementations both update
            # progress; retain a compatible fallback for future payment handlers.
            if progress(current, first) != index + 1:
                hc.my_coach(current).setdefault('chain', {})[str(first)] = index + 1
                hc._save(current)
            out['states'] = states(current)
            resources = out.setdefault('resources', [])
            resources = [r for r in resources if r.get('uri') != '/shop/remained/limited']
            resources.append({'uri': '/shop/remained/limited', 'body': limited_rows(current)})
            out['resources'] = resources
            return hc._json(out)
        return result

    def products(itemid):
        st = hc._state()
        out = []
        for entry in hc.shop_list(st):
            if entry.get('shopcategory') == 'CHAINED' and isinstance(entry.get('chained'), list):
                if not entry.get('buy'):
                    continue
                steps = [entry] + entry['chained']
                current = dict(steps[entry['step']])
                current['shopid'] = entry['shopid']
                candidates = [current]
            else:
                candidates = [entry]
            for candidate in candidates:
                product = candidate.get('product', {}).get('staticdata', {})
                if product.get('itemid') == itemid or any(i.get('itemid') == itemid for i in product.get('items', [])):
                    out.append(candidate)
        return hc._json(out)

    def route(path):
        match = re.fullmatch(r'/shop/products/(\d+)', path)
        if match:
            return lambda q, b: products(int(match.group(1)))
        return previous_route(path)

    def from_file(path):
        # These are live per-manager resources; stale hand-edited fixture files must
        # not override their dynamic handlers.
        if path in ('/shop/remained/limited', '/shop/remained/limited/STSHOP') or re.fullmatch(r'/shop/products/\d+', path):
            return None
        return previous_from_file(path)

    hc.chained_entry = chained_entry
    hc.ep_shop_purchase = purchase
    hc.route = route
    hc.from_file = from_file
    hc.ENDPOINTS['/shop/purchase'] = purchase
    hc.ENDPOINTS['/shop/remained/limited'] = lambda q, b: hc._json(limited_rows())
    hc.ENDPOINTS['/shop/remained/limited/STSHOP'] = lambda q, b: hc._json(limited_rows(special=True))
    hc.chain_status = status
    hc._chain_packages_installed = True
