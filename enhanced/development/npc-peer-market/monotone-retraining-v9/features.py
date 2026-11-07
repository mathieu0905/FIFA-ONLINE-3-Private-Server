"""Strict ability-only value features, independent of identity and role labels."""
import math

EXTRA = {'agility', 'balance', 'curve', 'freekickaccuracy', 'penalties'}


def ability_fields(config):
    return sorted(set().union(*(set(x) for x in config['role_weights'].values())) | EXTRA)


def schema(config, family='ALL'):
    names = ability_fields(config) + ['native_best_role_rating', 'weakfootabilitytypecode', 'skillmoves']
    return names, [1] * len(names)


def validate(raw):
    for name, lo, hi in [('weakfootabilitytypecode', 1, 5), ('skillmoves', 0, 5)]:
        v = raw[name]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v != int(v) or not lo <= v <= hi:
            raise ValueError('Invalid native foot/skill code: ' + name)


def role_rating(raw, config):
    # Every candidate rating is a positive weighted sum. Their maximum is
    # nondecreasing in EVERY ability, even if the card's main position changes.
    return max(sum(max(0, raw[k]) * w for k, w in weights.items()) / 100
               for weights in config['role_weights'].values())


def encode(raw, config):
    validate(raw)
    values = []
    for name in ability_fields(config):
        value = raw[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or not -3 <= value <= 255:
            raise ValueError('Invalid native ability: ' + name)
        values.append(float(max(0, value)))
    values += [role_rating(raw, config), float(raw['weakfootabilitytypecode']), float(min(4, raw['skillmoves']))]
    # Native skill codes 0..4 mean increasing actual skill stars. The two
    # inherited code-5 anomalies are preserved and treated as the top actual
    # tier, rather than inventing an additional star. No DB value is changed.
    return 'ALL', values


def ability_floor(raw, config):
    guard = config['low_price_guard']
    sensitivity = config['minimum_price_sensitivity']
    score = role_rating(raw, config)
    smooth_floor = guard['anchor_ep'] * math.exp(guard['log_slope'] * (score - guard['anchor_native_rating']))
    # A hard minimum sensitivity breaks flat tree plateaus. This is a disclosed
    # serving constraint, not a claim that these minimum EP slopes were learned.
    # +3 retains a nonnegative term for the 12 unchanged old negative profiles.
    points = sum(raw[f] + 3 for f in ability_fields(config))
    return (smooth_floor + points * sensitivity['ep_per_ability_point']
            + (raw['weakfootabilitytypecode'] - 1) * sensitivity['ep_per_weakfoot_star']
            + min(4, raw['skillmoves']) * sensitivity['ep_per_skill_star'])


def local_price(log_source_price, raw, config):
    continuous_source = math.exp(min(50, log_source_price)) / config['source_price_divisor']
    return min(5_600_000_000_000_000, max(1, round(continuous_source + ability_floor(raw, config))))
