"""Versioned enhancement curve for newly authored packs; legacy packs keep their rules."""
import math

FORMULA = 'six-anchor-v1'
ANCHORS = (30, 28, 25, 10, 6, 1)

def probabilities(low, high):
    if type(low) is not int or type(high) is not int or not 1 <= low <= high <= 20:
        raise ValueError('强化范围必须为1～20，且最低不能高于最高')
    if low == high:
        return [100.0]
    values = []
    for grade in range(low, high + 1):
        x = 5 * (grade - low) / (high - low)
        left = min(4, int(x))
        values.append(ANCHORS[left] + (ANCHORS[left + 1] - ANCHORS[left]) * (x - left))
    total = sum(values)
    result = [round(x * 100 / total, 6) for x in values]
    result[-1] = round(100 - sum(result[:-1]), 6)
    return result

def clean(definition, max_grade=20):
    low, high = definition.get('min_grade', 1), definition.get('grade', 1)
    if type(low) is not int or type(high) is not int or not 1 <= low <= high <= max_grade:
        raise ValueError(f'强化范围必须为1～{max_grade}，且最低不能高于最高')
    mode = definition.get('probability_mode', 'formula')
    if mode == 'formula':
        weights = probabilities(low, high)
    elif mode == 'manual':
        weights = definition.get('grade_probabilities')
        if not isinstance(weights, list) or len(weights) != high - low + 1:
            raise ValueError('请为范围内每个强化等级填写概率')
        if any(type(x) not in (float, int) or not math.isfinite(x) or x < 0 or x > 100 for x in weights):
            raise ValueError('概率必须是0～100的有限数字')
        if abs(sum(weights) - 100) > 0.00001:
            raise ValueError('各档概率合计必须为100%')
        weights = list(weights)
    elif mode == 'legacy':
        if low != 1:
            raise ValueError('旧版概率必须从+1开始')
        total = high * (high + 1) / 2
        weights = [(high - grade + 1) * 100 / total for grade in range(1, high + 1)]
    else:
        raise ValueError('未知概率模式')
    return dict(min_grade=low, grade=high, probability_mode=mode,
                probability_formula=FORMULA, grade_probabilities=weights)

def grades(definition):
    result = clean(definition)
    return list(zip(range(result['min_grade'], result['grade'] + 1), result['grade_probabilities']))
