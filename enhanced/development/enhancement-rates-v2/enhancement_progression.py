"""Twenty-grade progression: approachable +13 and increasingly scarce final grades.

Install defaults/value projection before enhancement_settings and market creation;
install runtime rules after other hooks, before protection service installation.
Existing paid booster effects and non-enhancement card_price anchors are retained.
"""
from fractions import Fraction

VERSION = 'progression20-v2'
RATES = (1., 1., .95, .90, .85, .80, .75, .70, .65, .60,
         .55, .20, .15, .12, .10, .08, .06, .05, .04, .03, 0.)
PRICE_STEPS = (125, 135, 145, 155, 170, 185, 210, 240, 280, 320)
# Includes headroom for the existing market quote factor of at most 1.6.
MAX_DISPLAY_PRICE = 5_600_000_000_000_000


def failure_grade(grade):
    if grade <= 5:
        return grade
    return max(10 if grade >= 10 else 5, grade - 1)


def install(h):
    if getattr(h, '_enhancement_progression_defaults_installed', False):
        return
    if h.MAX_GRADE != 20:
        raise ValueError('Progression20 requires the +20 client/profile')
    h.ENHANCE_RATE = RATES
    h.ENHANCE_DROP_FROM = 6
    h.enhancement_failure_grade = lambda target: failure_grade(h.grade_of(target))
    old_value = h.player_value_price
    factors = {10: Fraction(1)}
    for grade, percent in enumerate(PRICE_STEPS, 11):
        factors[grade] = factors[grade - 1] * Fraction(percent, 100)

    def player_value_price(spid, grade=1):
        g = min(h.MAX_GRADE, max(0, int(grade)))
        if g <= 10:
            return old_value(spid, g)
        amount = old_value(spid, 10) * factors[g]
        value = (amount.numerator + amount.denominator - 1) // amount.denominator
        # No currently indexed card reaches this safety boundary. Retain a
        # Number-safe response if later editor changes add an extreme card.
        return min(MAX_DISPLAY_PRICE, value)

    h.player_value_price = player_value_price
    h.enhance_cost = lambda target: max(1000, (h.player_value_price(target['spid'], h.grade_of(target)) * 2 + 99) // 100)
    h.PROGRESSION20 = dict(version=VERSION, default_probabilities={str(g): round(RATES[g] * 100, 8) for g in range(1, 20)},
                          safe_floors=[5, 10], no_drop_through=5,
                          protection_percent=40, normal_fee_percent=2, normal_fee_minimum=1000,
                          price_steps={str(g): p / 100 for g, p in enumerate(PRICE_STEPS, 11)},
                          maximum_display_price=MAX_DISPLAY_PRICE,
                          high_grade_point_bonus='From current +12: relative 10% of material-adjusted base chance',
                          legacy_paid_boosters='Original additive item effects retained; exclusive with protection')
    h._enhancement_progression_defaults_installed = True


def install_runtime(h):
    if getattr(h, '_enhancement_progression_runtime_installed', False):
        return
    old_rate = h.enhance25_rate

    def enhance25_rate(pa, pb, use_point, item, eventid):
        if h.grade_of(pa) < 12 or not use_point or h.grade_of(pb) == 0:
            return old_rate(pa, pb, use_point, item, eventid)
        # Booster items retain already sold effects. The repeatable free point
        # system no longer adds a flat ten percentage points at the rare end.
        rate = old_rate(pa, pb, False, item, eventid)
        return min(1., rate + h.enhance_rate(pa, pb) * h.ES_BOOST)

    h.enhance25_rate = enhance25_rate
    old_restore = h.ep_enhance25_restore

    def restore(query, body):
        with h.STATE_LOCK:
            state = h._state()
            pending = state.get('enhance_restore')
            if pending:
                team = state['teams'][str(h._default_slot(state))]
                card = next((p for p in team['players'] if h.iid(p) == str(pending['id'])), None)
                if card is not None and h.grade_of(card) >= pending['grade']:
                    return h._json({'result': False, 'reason': 'RESTORE_NOT_REQUIRED'})
            return old_restore(query, body)

    h.ep_enhance25_restore = restore
    h.ENDPOINTS.update({path: restore for path, fn in h.ENDPOINTS.items() if fn is old_restore})
    h.ENDPOINTS['/info/enhancement/progression/rules'] = lambda query, body: h._json({
        **h.PROGRESSION20, 'active_probabilities': h.enhancement_settings_get()['rates'],
        'failure_grades': {str(g): failure_grade(g) for g in range(1, 21)}})
    h._enhancement_progression_runtime_installed = True
