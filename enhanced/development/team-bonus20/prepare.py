"""Prepare a minimal current-source delta. Never writes official files or starts services."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parent
SERVER = Path(r'D:\FO3ID\server')
REVISION = 'team-bonus20-moments-v1'

def replace_once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError('Current source needs review: '+old[:120])
    return source.replace(old, new)

def transform(source):
    if 'TC_MOMENTS_EXTRA' in source:
        raise RuntimeError('Team bonus extension already present; do not append twice')
    source = replace_once(source, '\n\ndef tc_seasons():', '''

# Single-grade extensions preserve the existing +2..+10 groups. Highest wins.
TC_GRADE += tuple((10100 + g, g, f"强化+{g}套装", _tc_groups((11, 11, g - 3)))
                  for g in range(11, 21))
TC_MOMENTS_EXTRA = 60084
TC_MOMENTS_GROUPS = _tc_groups((3, 5, 2), (6, 8, 3), (9, 10, 4), (11, 11, 5))


def tc_seasons():''')
    source = replace_once(source,
        '        for _, codes in tc_seasons():\n            sets[TC_SEASON + codes[0]] = [(s, p) for s, p in rows if s // 1000000 in codes]',
        '        sets[TC_MOMENTS_EXTRA] = [(s, p) for s, p in rows if s // 1000000 == 84]\n        for _, codes in tc_seasons():\n            sets[TC_SEASON + codes[0]] = [(s, p) for s, p in rows if s // 1000000 in codes]')
    source = replace_once(source, '    return [club, nation] + grades + clubs + nations + specials', '''    # Native feature colors are selected independently of base and grade colors.
    moments = {"teamcolorid": TC_MOMENTS_EXTRA, "type": "feature", "teamid": str(TC_MOMENTS_EXTRA),
               "name": "传奇时刻额外加成", "description": "首发传奇时刻球员3–5人+2、6–8人+3、9–10人+4、11人+5；与原有套装及强化套叠加",
               "boostgroups": TC_MOMENTS_GROUPS}
    return [club, nation] + grades + clubs + nations + specials + [moments]''')
    source = replace_once(source,
        'for c in tc_colors() if c["type"] == "special"}',
        'for c in tc_colors() if c["type"] in ("special", "feature")}')
    source = replace_once(source,
        'n = counts.get(("special", c["teamcolorid"]) if c["type"] == "special"',
        'n = counts.get(("special", c["teamcolorid"]) if c["type"] in ("special", "feature")')
    source = replace_once(source,
        '"special": lambda: spid in sets[c["teamcolorid"]][0]}[c["type"]]()',
        '"special": lambda: spid in sets[c["teamcolorid"]][0],\n                    "feature": lambda: spid in sets[c["teamcolorid"]][0]}[c["type"]]()')
    source = replace_once(source,
        'kind = "grade" if c["type"] == "grade" else "base"',
        'kind = c["type"] if c["type"] in ("grade", "feature") else "base"')
    source = replace_once(source,
        'best = {}  # "base" / "grade": (point, boosts)',
        'best = {}  # Independent best base / grade / feature colors: (point, boosts)')
    compile(source, 'http_config.py', 'exec')
    return source

def sha(data): return hashlib.sha256(data).hexdigest()

def build():
    before = (SERVER/'http_config.py').read_bytes()
    after = transform(before.decode('utf8')).encode('utf8')
    # Changed function bodies are limited to the shared native team-color pipeline.
    old = ast.parse(before); new = ast.parse(after)
    functions = lambda tree: {n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    a, b = functions(old), functions(new)
    changed = sorted(k for k in a if a[k] != b[k])
    assert changed == ['active_teamcolors', 'ep_teamcolor', 'tc_colors', 'tc_special_sets', 'xi_ratings'], changed
    (ROOT/'http_config.prepared.py').write_bytes(after)
    report = dict(status='PREPARED_NOT_INSTALLED', revision=REVISION,
                  source=str(SERVER/'http_config.py'), before_sha256=sha(before), after_sha256=sha(after),
                  changed_functions=changed, grade_tiers={g:g-3 for g in range(11,21)},
                  moments_tiers=[[3,5,2],[6,8,3],[9,10,4],[11,11,5]],
                  client_resource_changes=False, state_shop_written=False, services_restarted=False,
                  native_verified=False, install_policy='Fresh source, fresh parent, locks, backup/CAS after user finishes game; never copy a stale full prepared HTTP file')
    (ROOT/'prepared.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n','utf8')
    print(json.dumps(report, ensure_ascii=True))
    return report

if __name__ == '__main__': build()
