"""654420 cash-popup compatibility; no wallet, price, probability or save mutations.

CoachProxy rounds usable mileage with mp - mp % mp_base_unit.  A missing
STATICVALUES/mp_base_unit is coerced to zero and poisons every cash popup with NaN.
"""
import functools
import json

BASE_UNIT = 1
ROOT_URI = '/static/db/STATICVALUES'
UNIT_URI = ROOT_URI + '/mp_base_unit'


def install(hc):
    if getattr(hc, '_shop_popup_compat_installed', False):
        return
    original_file = hc.from_file
    original_item = hc.item_def

    @functools.wraps(original_file)
    def from_file(path):
        if path == UNIT_URI:
            return hc._json(BASE_UNIT)
        response = original_file(path)
        if path == ROOT_URI and response is not None:
            content_type, raw = response
            if content_type == 'application/json':
                value = json.loads(raw)
                value['mp_base_unit'] = BASE_UNIT
                return hc._json(value)
        return response

    def no_mileage(value):
        if isinstance(value, list):
            return [no_mileage(v) for v in value]
        if not isinstance(value, dict):
            return value
        result = {k: no_mileage(v) for k, v in value.items()}
        if result.get('currency') == 'cash':
            # This server charges the full cash price and offers no MP co-payment.
            result.update(mileage_use_min=0, mileage_use_max=0)
        return result

    @functools.wraps(original_item)
    def item_def(itemid):
        return no_mileage(original_item(itemid))

    hc.from_file = from_file
    hc.item_def = item_def
    hc.ENDPOINTS[UNIT_URI] = lambda query, body: hc._json(BASE_UNIT)
    hc._shop_popup_compat_installed = True
