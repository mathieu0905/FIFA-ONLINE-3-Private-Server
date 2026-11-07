"""Capped enhancement chances and a compact valuation curve; no asset migration."""
from fractions import Fraction
from functools import lru_cache
import json

VERSION = 'progression20-material-gradient-v5'
RATES = (1., .90, .85, .75, .65, .55, .45, .38, .32, .28,
         .25, .20, .15, .12, .10, .08, .06, .05, .04, .03, 0.)
MAX_DISPLAY_PRICE = 5_600_000_000_000_000


def failure_grade(grade):
    if grade <= 5:
        return grade
    return max(10 if grade >= 10 else 5, grade - 1)


def material_factor(target_grade, material_grade):
    """Interpolate between existing integer tier starts, never lower a tier."""
    if material_grade >= target_grade:
        return 1.
    if material_grade <= 0:
        return .35  # Native +0 merges are handled separately.
    # ceil(g/3), ceil(2*g/3); duplicate starts use the higher native tier.
    anchors = {1: .35, (target_grade + 2) // 3: .50,
               (target_grade * 2 + 2) // 3: .75, target_grade: 1.}
    starts = sorted(anchors)
    for lower, upper in zip(starts, starts[1:]):
        if lower <= material_grade <= upper:
            return anchors[lower] + (anchors[upper] - anchors[lower]) * (material_grade - lower) / (upper - lower)
    return anchors[starts[0]]


@lru_cache(maxsize=8192)
def expected_curve(base, rates):
    """Minimum expected EP cost, without optional ES/items, including failed rebuilds.

    V(next) = V(main) + [V(material) + fee + (1-p)*rebuild_loss] / p.
    Protected failures keep both cards: material is paid only once, on success.
    Each quoted grade is rounded up once and the native display ceiling is retained.
    """
    values = [0, max(0, min(MAX_DISPLAY_PRICE, int(base)))]
    choices = []
    for grade in range(1, 20):
        best, selected = None, None
        ceiling = Fraction(str(rates[grade]))
        for material in range(1, grade + 1):
            probability = ceiling * Fraction(str(material_factor(grade, material)))
            if probability <= 0:
                continue
            for protected in (False, True):
                failed_grade = grade if protected else failure_grade(grade)
                fee = (values[grade] * 2 + 4) // 5 if protected else max(1000, (values[grade] * 2 + 99) // 100)
                rebuild = values[grade] - values[failed_grade]
                material_cost = probability * values[material] if protected else values[material]
                cost = values[grade] + (material_cost + fee + (1 - probability) * rebuild) / probability
                if best is None or cost < best:
                    best = cost
                    selected = (material, protected, float(probability))
        value = MAX_DISPLAY_PRICE if best is None else min(MAX_DISPLAY_PRICE, (best.numerator + best.denominator - 1) // best.denominator)
        values.append(max(values[-1], value))
        choices.append(selected)
    return tuple(values), tuple(choices)


def install(h):
    if getattr(h, '_enhancement_progression_defaults_installed', False):
        return
    if h.MAX_GRADE != 20:
        raise ValueError('Progression20 requires the +20 client/profile')
    h.ENHANCE_RATE = RATES
    h.ENHANCE_DROP_FROM = 6
    h.enhancement_failure_grade = lambda target: failure_grade(h.grade_of(target))
    original_value = h.player_value_price

    def expected_value(base, grade):
        g = min(h.MAX_GRADE, max(0, int(grade)))
        if g == 0 or base <= 0:
            return 0
        if g == 1:
            return min(MAX_DISPLAY_PRICE, int(base))
        return expected_curve(int(base), tuple(h.ENHANCE_RATE))[0][g]

    def player_value_price(spid, grade=1):
        g = min(h.MAX_GRADE, max(0, int(grade)))
        return expected_value(original_value(spid, 1), g)

    def enhance_rate(pa, pb):
        tg, mg = h.grade_of(pa), h.grade_of(pb)
        if mg == 0:
            return 1.  # Original +0 merge does not increase the grade.
        return h.ENHANCE_RATE[tg] * material_factor(tg, mg)

    h.player_value_price = player_value_price
    h.enhancement_expected_value = expected_value
    h.enhance_rate = enhance_rate
    h.enhance_cost = lambda target: max(1000, (h.player_value_price(target['spid'], h.grade_of(target)) * 2 + 99) // 100)
    h.PROGRESSION20 = dict(version=VERSION,
        probability_semantics='Current grade -> next grade; equal-grade material is the final ceiling',
        default_probabilities={str(g): round(RATES[g] * 100, 8) for g in range(1, 20)},
        safe_floors=[5, 10], no_drop_through=5,
        protection_percent=40, normal_fee_percent=2, normal_fee_minimum=1000,
        material_factors=dict(mode='linear_between_integer_tier_starts', lowest=.35, one_third=.50, two_thirds=.75, equal_or_higher=1., rounding='ceil each threshold; duplicate starts keep higher factor'),
        value_model=dict(kind='minimum_expected_EP_cost', materials='All material grades 1..main; choose cheapest expected EP strategy',
            ordinary_fee_percent=2, ordinary_fee_minimum=1000, protection_fee_percent=40,
            failed_rebuild='V(main)-V(failed_grade); zero with protection', protected_material='Consumed only on success; priced once, not once per attempt',
            optional_points=False, optional_boost_items=False, rounding='Ceil each grade', market_base='Live persistent +1 market price'),
        maximum_display_price=MAX_DISPLAY_PRICE,
        point_bonus='Relative 10%, all grades, capped; no ES consumed when no benefit',
        booster_bonus='Relative bronze/silver/gold 5/10/15%; additive with point percentage; capped; protection itself adds no chance',
        event_probability_bonus=0)
    h._enhancement_progression_defaults_installed = True


def install_runtime(h):
    if getattr(h, '_enhancement_progression_runtime_installed', False):
        return

    def enhance25_rate(pa, pb, use_point, item, eventid):
        if h.grade_of(pb) == 0:
            return 1.
        ceiling = h.ENHANCE_RATE[h.grade_of(pa)]
        bonus = .10 if use_point else 0.
        if item:
            bonus += h.ITEMS[item['itemid']][3]['boost']
        return min(ceiling, h.enhance_rate(pa, pb) * (1. + bonus))

    def point_effective(pa, pb, selected):
        return bool(selected and h.grade_of(pb) > 0 and h.enhance_rate(pa, pb) < h.ENHANCE_RATE[h.grade_of(pa)])

    h.enhance25_rate = enhance25_rate
    h.enhancement_point_effective = point_effective
    h.EVENT_BOOST = 0.
    h.ENHANCE_EVENT = dict(h.ENHANCE_EVENT, active=False,
        reward=[[{'boosts': {'BOOST_PLUS_ENHANCE': 0}}]],
        messages={'main': {'name': '强化概率规则', 'description': '同等级材料达到本阶段上限；无额外活动概率。'}})
    for itemid in (1000052, 1000053, 1000054):
        value = list(h.ITEMS[itemid])
        value[-1] = '强化成功率相对提高' + str(round(value[3]['boost'] * 100)) + '%，与点数比例相加；不超过同等级材料上限，已满上限不消耗。'
        h.ITEMS[itemid] = tuple(value)

    old_preview, old_enhance = h.ep_enhance25_preview, h.ep_enhance25

    def effective(st, a, b, points, item):
        pa, pb = h.enhance_pair(st['teams'][str(h._default_slot(st))], a, b)
        if pa is None:
            return points, item, False
        effective_points = '1' if point_effective(pa, pb, points == '1') else '0'
        capped = h.grade_of(pb) > 0 and h.enhance_rate(pa, pb) >= h.ENHANCE_RATE[h.grade_of(pa)]
        if capped and h.boost_stack(st, item) is not None:
            item = '-1'
        return effective_points, item, capped

    def preview(a, b, points, item, event, query, body):
        with h.STATE_LOCK:
            points, item, capped = effective(h._state(), a, b, points, item)
            kind, raw = old_preview(a, b, points, item, event, query, body)
            data = json.loads(raw)
            if data.get('result'):
                if capped:
                    data['needes'] = 0
                data['enhancement_bonus'] = dict(capped=capped, points_effective=points == '1', booster_effective=item != '-1',
                    label='已达到同等级材料成功率上限，点数和加成道具不生效、不消耗。' if capped else '点数/道具按相对比例提高概率，最终不超过同等级材料上限。')
            return h._json(data)

    def enhance(a, b, points, item, event, query, body):
        with h.STATE_LOCK:
            points, item, capped = effective(h._state(), a, b, points, item)
            return old_enhance(a, b, points, item, event, query, body)

    replacements = {old_preview: preview, old_enhance: enhance}
    h.ROUTES[:] = [(pat, replacements.get(fn, fn)) for pat, fn in h.ROUTES]
    h.ENDPOINTS.update({uri: replacements.get(fn, fn) for uri, fn in h.ENDPOINTS.items()})
    h.ep_enhance25_preview, h.ep_enhance25 = preview, enhance
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
    h.ENDPOINTS.update({uri: restore for uri, fn in h.ENDPOINTS.items() if fn is old_restore})
    h.ENDPOINTS['/info/enhancement/progression/rules'] = lambda query, body: h._json({
        **h.PROGRESSION20, 'active_probabilities': h.enhancement_settings_get()['rates'],
        'failure_grades': {str(g): failure_grade(g) for g in range(1, 21)}})
    h._enhancement_progression_runtime_installed = True
