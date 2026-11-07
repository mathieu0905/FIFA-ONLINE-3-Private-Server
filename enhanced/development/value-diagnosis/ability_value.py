"""Explainable monotone ability prices; no model loading, asset writes or threads.

All comparisons hold position and body fixed. Native role weights are the same
ones used by the client. Higher relevant abilities never lower the fair price.
Historical seeds remain evidence; only a bounded historical market movement is
applied to the new fair price. Prices are local EP, without the old /1000 floor.
"""
from pathlib import Path
import bisect
import json
import math
from fractions import Fraction

MAX_PRICE = 5_600_000_000_000_000
ATHLETIC = ('acceleration', 'sprintspeed', 'agility', 'balance', 'stamina', 'strength', 'jumping')
CONTROL = ('ballcontrol', 'shortpassing', 'reactions')
GK_SUPPORT = ('agility', 'reactions', 'strength', 'jumping')


class AbilityValuePolicy:
    def __init__(self, path=None):
        path = Path(path or Path(__file__).parent / 'gamedata/ability_value_policy.json')
        self.config = json.loads(path.read_text('utf8'))
        c = self.config
        if c['schema'] != 1 or len(c['position_roles']) != 28:
            raise ValueError('Unsupported ability price policy')
        self.weights = c['role_weights']
        for role, weights in self.weights.items():
            if not weights or sum(weights.values()) != 100 or any(type(w) is not int or w <= 0 for w in weights.values()):
                raise ValueError('Nonpositive or incomplete role weights: ' + role)
        if any(role not in self.weights for role in c['position_roles']):
            raise ValueError('Unknown position role')
        self.curve = c['curve']
        if len(self.curve) < 2 or any(not math.isfinite(float(v)) for point in self.curve for v in point):
            raise ValueError('Invalid ability price curve')
        if any(a[0] >= b[0] or not 0 < a[1] < b[1] <= MAX_PRICE for a, b in zip(self.curve, self.curve[1:])):
            raise ValueError('Ability price curve must strictly increase')
        self.scores = [point[0] for point in self.curve]
        self.fields = sorted(set(ATHLETIC + CONTROL + GK_SUPPORT).union(*(set(w) for w in self.weights.values())))
        self.fields += ['preferredposition1', 'height', 'weakfootabilitytypecode', 'skillmoves']
        if not 0 < c['market_factor_min'] <= 1 <= c['market_factor_max'] <= 1.1:
            raise ValueError('Invalid bounded market movement')

    @staticmethod
    def _number(raw, field, lo, hi):
        value = raw[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('Invalid ability field: ' + field)
        return value

    def explain(self, raw):
        pos = self._number(raw, 'preferredposition1', 0, 27)
        if pos != int(pos):
            raise ValueError('Position must be an integer')
        role = self.config['position_roles'][int(pos)]
        abilities = {}
        for field in self.fields:
            if field not in ('preferredposition1', 'height', 'weakfootabilitytypecode', 'skillmoves'):
                # Twelve existing season-40 profiles contain -1..-3 values.
                # Retain their source DB exactly; explicitly value nonpositive
                # abilities as zero and expose them in the explanation.
                abilities[field] = max(0, self._number(raw, field, -3, 255))
        rating = sum(abilities[field] * weight for field, weight in self.weights[role].items()) / 100
        height = self._number(raw, 'height', 100, 250)
        wf = self._number(raw, 'weakfootabilitytypecode', 1, 5)
        # FO3 skillmoves is a level CODE (normally 0..4), not source 1..5 stars.
        # Two existing special templates use code 5: retain them and saturate
        # the bonus, rather than changing their DB values or inventing a tier.
        sm = self._number(raw, 'skillmoves', 0, 5)
        if wf != int(wf) or sm != int(sm):
            raise ValueError('Foot and skill codes must be integers')
        if role == 'GK':
            supporting = sum(abilities[f] for f in GK_SUPPORT) / len(GK_SUPPORT)
            ability = .9 * rating + .1 * supporting
            modifier = min(20, max(0, height - 180)) * .025
        else:
            athletic = sum(abilities[f] for f in ATHLETIC) / len(ATHLETIC)
            control = sum(abilities[f] for f in CONTROL) / len(CONTROL)
            supporting = .75 * athletic + .25 * control
            ability = .8 * rating + .2 * supporting
            modifier = (wf - 3) * .3 + (min(4, sm) - 1) * .3
        score = ability + modifier
        index = min(len(self.curve) - 2, max(0, bisect.bisect_right(self.scores, score) - 1))
        (lo, price_lo), (hi, price_hi) = self.curve[index:index + 2]
        log_price = math.log(price_lo) + (score - lo) / (hi - lo) * math.log(price_hi / price_lo)
        fair_price = max(1, round(math.exp(min(math.log(MAX_PRICE), log_price))))
        return dict(policy=self.config['revision'], role=role, native_role_rating=rating,
                    supporting_rating=supporting, modifier=modifier, ability_score=score,
                    fair_price=fair_price, unit='EP',
                    nonpositive_source_abilities={f: raw[f] for f in abilities if raw[f] < 0})

    def fair_price(self, raw):
        return self.explain(raw)['fair_price']

    def market_factor(self, basis, initial):
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0 for v in (basis, initial)):
            raise ValueError('Invalid historical market basis')
        return min(self.config['market_factor_max'], max(self.config['market_factor_min'], basis / initial))


class AbilityPriceBook:
    def __init__(self, host, policy=None):
        self.host = host
        self.policy = policy or AbilityValuePolicy()
        self._cache = {}
        self.grade_factors = [Fraction(str(host.GRADE_PRICE[g])) for g in range(11)]
        for grade in range(11, host.MAX_GRADE + 1):
            step = host.PROGRESSION20['price_steps'][str(grade)]
            if not math.isfinite(step) or step < 1:
                raise ValueError('Invalid existing enhancement investment curve')
            self.grade_factors.append(self.grade_factors[-1] * Fraction(str(step)))

    def explain(self, spid):
        spid = int(spid)
        if spid not in self._cache:
            with self.host.closing(self.host._db()) as db:
                row = db.execute('SELECT ' + ','.join(self.policy.fields) + ' FROM players WHERE spid=?', (spid,)).fetchone()
            if row is None:
                raise ValueError('Missing ability profile: ' + str(spid))
            self._cache[spid] = self.policy.explain(dict(zip(self.policy.fields, row)))
        return dict(self._cache[spid])

    def current(self, spid, basis, initial):
        fair = self.explain(spid)['fair_price']
        return min(MAX_PRICE, max(1, round(fair * self.policy.market_factor(basis, initial))))

    def graded(self, base, grade):
        grade = min(self.host.MAX_GRADE, max(0, int(grade)))
        amount = base * self.grade_factors[grade]
        return min(MAX_PRICE, max(1, amount.numerator // amount.denominator)) if amount > 0 else 0
