"""Monotone role experts with a strictly increasing, identity-free EP link."""
import math

EXTRA = {'agility', 'balance', 'curve', 'freekickaccuracy', 'penalties'}
GK_FIELDS = ['gkdiving', 'gkhandling', 'gkkicking', 'gkpositioning', 'gkreflexes']
GK_SUPPORT = ['reactions', 'agility', 'jumping', 'strength']
FAMILIES = ['OUT', 'GK']


def ability_fields(config):
    return sorted(set().union(*(set(w) for w in config['role_weights'].values())) | EXTRA)


def schema(config, family):
    if family == 'OUT':
        fields = [k for k in ability_fields(config) if k not in GK_FIELDS]
        fields += ['role:' + role for role in sorted(config['role_weights']) if role != 'GK']
        fields += ['best_outfield', 'allround_min']
    elif family == 'GK':
        fields = GK_FIELDS + GK_SUPPORT + ['role:GK', 'keeper_mean', 'keeper_min']
    else:
        raise ValueError('Unknown monotone expert')
    fields += ['weakfootabilitytypecode', 'skillmoves']
    return fields, [1] * len(fields)


def validate(raw, config):
    for field in ability_fields(config):
        value = raw[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or not -3 <= value <= 255:
            raise ValueError('Invalid native ability: ' + field)
    for field, lo, hi in [('weakfootabilitytypecode', 1, 5), ('skillmoves', 0, 5)]:
        value = raw[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or not lo <= value <= hi:
            raise ValueError('Invalid native star code: ' + field)


def role_scores(raw, config):
    return {role: sum(max(0, raw[k]) * w for k, w in weights.items()) / 100
            for role, weights in config['role_weights'].items()}


def role_rating(raw, config):
    return max(role_scores(raw, config).values())


def encode(raw, config, family):
    validate(raw, config)
    scores = role_scores(raw, config)
    best_outfield = max(value for role, value in scores.items() if role != 'GK')
    allround = min(max(scores[r] for r in group) for group in
                   [('ST', 'CF', 'W'), ('AM', 'CM', 'WM', 'DM'), ('CB', 'SW', 'FB', 'WB')])
    mean = sum(max(0, raw[k]) for k in GK_FIELDS) / 5
    values = []
    for key in schema(config, family)[0]:
        if key.startswith('role:'):
            value = scores[key[5:]]
        elif key == 'best_outfield':
            value = best_outfield
        elif key == 'allround_min':
            value = allround
        elif key == 'keeper_mean':
            value = mean
        elif key == 'keeper_min':
            value = min(max(0, raw[k]) for k in GK_FIELDS)
        elif key == 'skillmoves':
            value = min(4, raw[key])
        else:
            value = max(0, raw[key])
        values.append(float(value))
    return values


def keeper_gate(raw, config):
    mean = sum(max(0, raw[k]) for k in GK_FIELDS) / 5
    gate = config['gk_gate']
    return min(1., (mean / gate['full_support_mean']) ** gate['power'])


def source_price(log_out, log_gk, raw, config):
    out = math.exp(min(50, log_out))
    keeper = math.exp(min(50, log_gk)) * keeper_gate(raw, config)
    return max(out, keeper)


def ability_floor(raw, config):
    guard = config['low_price_guard']
    sensitivity = config['minimum_price_sensitivity']
    smooth = guard['anchor_ep'] * math.exp(guard['log_slope'] * (role_rating(raw, config) - guard['anchor_native_rating']))
    return (smooth + sum(raw[k] + 3 for k in ability_fields(config)) * sensitivity['ep_per_ability_point']
            + (raw['weakfootabilitytypecode'] - 1) * sensitivity['ep_per_weakfoot_star']
            + min(4, raw['skillmoves']) * sensitivity['ep_per_skill_star'])


def local_price(log_out, log_gk, raw, config, identity_factor=1.):
    if not math.isfinite(identity_factor) or identity_factor <= 0:
        raise ValueError('Invalid same-player history factor')
    return min(5_600_000_000_000_000, max(1, round(source_price(log_out, log_gk, raw, config) * identity_factor / config['source_price_divisor'] + ability_floor(raw, config))))
