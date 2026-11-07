"""Minimal change against the current official enhancement implementation."""
from pathlib import Path
import ast, hashlib, json, sys
sys.dont_write_bytecode = True
W = Path(__file__).resolve().parent
S = Path('D:/FO3ID/server')
sha = lambda b: hashlib.sha256(b).hexdigest()
source = (S/'enhancement_progression.py').read_text('utf8')
tree = ast.parse(source)
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'material_factor')
lines = source.splitlines(keepends=True)
replacement = '''def material_factor(target_grade, material_grade):
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
'''
out = ''.join(lines[:node.lineno-1]) + replacement + ''.join(lines[node.end_lineno:])
out = out.replace("VERSION = 'progression20-capped-both-v4'", "VERSION = 'progression20-material-gradient-v5'")
old = 'material_factors=dict(below_one_third=.35, below_two_thirds=.50, below_equal=.75, equal_or_higher=1.),'
assert old in out
out = out.replace(old, "material_factors=dict(mode='linear_between_integer_tier_starts', lowest=.35, one_third=.50, two_thirds=.75, equal_or_higher=1., rounding='ceil each threshold; duplicate starts keep higher factor'),")
compile(out, 'enhancement_progression.py', 'exec')
(W/'enhancement_progression.py').write_text(out, encoding='utf8')
result = dict(status='BUILT', baseline={'enhancement_progression.py':sha((S/'enhancement_progression.py').read_bytes())}, outputs={'enhancement_progression.py':sha((W/'enhancement_progression.py').read_bytes())})
(W/'build.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps(result))
