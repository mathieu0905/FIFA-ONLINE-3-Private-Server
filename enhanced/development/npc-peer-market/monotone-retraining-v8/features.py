"""Identity-free FO3 features and an explicit low-denomination guard."""
import math

EXTRA = {'agility', 'balance', 'curve', 'freekickaccuracy', 'penalties'}
GK_ABILITIES = ['gkdiving', 'gkhandling', 'gkkicking', 'gkpositioning', 'gkreflexes', 'reactions', 'agility', 'jumping', 'strength']


def schema(config, family):
    all_stats = sorted(set().union(*(set(x) for x in config['role_weights'].values())) | EXTRA)
    abilities = GK_ABILITIES if family == 'GK' else [f for f in all_stats if not f.startswith('gk')]
    names = list(abilities) + ['native_role_rating']
    if family != 'GK':
        names += ['weakfootabilitytypecode', 'skillmoves']
    constraints = [1] * len(names)
    names += ['height', 'weight']
    constraints += [1 if family == 'GK' else 0, 0]
    if family != 'GK':
        roles = sorted(set(config['position_roles']) - {'GK'})
        names += ['role:' + role for role in roles]
        constraints += [0] * len(roles)
    return names, constraints


def validate(raw):
    for field in ('preferredposition1', 'height', 'weight', 'weakfootabilitytypecode', 'skillmoves'):
        value = raw[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Invalid feature: ' + field)
    if raw['preferredposition1'] != int(raw['preferredposition1']) or not 0 <= raw['preferredposition1'] < 28:
        raise ValueError('Invalid native position')
    if not 100 <= raw['height'] <= 250 or not 30 <= raw['weight'] <= 200:
        raise ValueError('Invalid body profile')
    if not 1 <= raw['weakfootabilitytypecode'] <= 5 or not 0 <= raw['skillmoves'] <= 5:
        raise ValueError('Invalid native foot/skill code')


def role_rating(raw, config):
    role = config['position_roles'][int(raw['preferredposition1'])]
    return sum(max(0, raw[k]) * w for k, w in config['role_weights'][role].items()) / 100


def encode(raw, config):
    validate(raw)
    role = config['position_roles'][int(raw['preferredposition1'])]
    family = 'GK' if role == 'GK' else 'OUTFIELD'
    names, _ = schema(config, family)
    result = []
    for name in names:
        if name == 'native_role_rating':
            value = role_rating(raw, config)
        elif name.startswith('role:'):
            value = int(role == name[5:])
        elif name == 'skillmoves':
            value = min(4, raw[name])  # retain two historical code-5 templates
        else:
            value = raw[name]
            if name not in ('height', 'weight', 'weakfootabilitytypecode'):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not -3 <= value <= 255:
                    raise ValueError('Invalid native ability: ' + name)
                value = max(0, value)  # explicit treatment of 12 old season-40 rows
        result.append(float(value))
    return family, result


def ability_floor(raw, config):
    guard = config['low_price_guard']
    score = role_rating(raw, config)
    return guard['anchor_ep'] * math.exp(guard['log_slope'] * (score - guard['anchor_native_rating']))


def local_price(log_source_price, raw, config):
    # Currency conversion remains continuous; do not floor /1000 before adding
    # the ability floor. Only the final displayed EP amount is rounded.
    source = math.exp(min(50, log_source_price))
    return min(5_600_000_000_000_000, max(1, round(source / config['source_price_divisor'] + ability_floor(raw, config))))
