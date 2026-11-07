"""Read-only season 12 display audit; output files stay in this directory."""
from pathlib import Path
import contextlib, hashlib, io, json, re, sqlite3, struct, sys, zlib
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')
CLIENT = Path('D:/FO3ID/32795')
sys.path[:0] = ['D:/FO3ID/server/tools/re', 'D:/fifaol3/season-display',
 'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_levels']
import bigdir
from build_moments_display import tags
from avm_patch import ABC, dis

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def swf(p):
    member = next(n for n, *_ in bigdir.entries(p) if n.endswith('.gfx'))
    gfx = bigdir.read(p, member)
    data = b'FWS' + gfx[3:8] + zlib.decompress(gfx[8:])
    start = 8 + (5 + 4 * (data[8] >> 3) + 7) // 8 + 4
    return list(tags(data, start))

module = CLIENT / 'data/ui/libs/Module.big'
label = CLIENT / 'data/ui/components/Label.big'
protected = {str(p): digest(p) for p in [module, label]}
for kind, body, _ in swf(module):
    if kind != 82: continue
    a = ABC(body[body.index(b'\0', 4)+1:])
    if not a.A['cls'] or 'PlayerListUtil' not in str(a.A['cls'][0][0]): continue
    for mid in [12, 13, 14]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output): rendered = dis(a.A, a.A['body'][mid])
        (ROOT / f'PlayerListUtil-method{mid}.txt').write_text(output.getvalue() + '\n'.join(rendered), 'utf-8')
    cinit = a.A['cls'][0][4]
    (ROOT/'PlayerListUtil-cinit.txt').write_text('\n'.join(dis(a.A,a.A['body'][cinit])),'utf-8')
    code = a.A['body'][12]
    assert code[930] == 0x1b
    def s24(at): return int.from_bytes(code[at:at+3], 'little', signed=True)
    default = 930 + s24(931)
    at = 934; count = 0; shift = 0
    while True:
        byte = code[at]; at += 1; count |= (byte & 127) << shift
        if not byte & 128: break
        shift += 7
    branches = [930+s24(at+i*3) for i in range(count+1)]
    (ROOT/'callback-switch.json').write_text(json.dumps(dict(default=default,case_count=count,last_case=branches[-1],targets=branches),indent=2),'utf-8')
    init_lines = dis(a.A,a.A['body'][cinit])
    values = {}
    for ix, line in enumerate(init_lines):
        if 'initproperty ' in line and ix:
            match = re.search(r'push(?:byte|int) (-?\d+)',init_lines[ix-1])
            if match: values[line.split('initproperty ')[1]] = int(match[1])
    checked = re.findall(r'getproperty (\w+)', '\n'.join(dis(a.A, code)))
    constants = {n:values.get(n) for n in checked if n in values}
    assert 12 not in constants.values() and 13 not in constants.values() and 84 not in constants.values()

languages = {}
for cache in ['games/fo3id','cdn']:
    path = CLIENT / f'_cache/{cache}/externalAssets/language_chi.big'
    member = next(n for n,*_ in bigdir.entries(path) if 'LANGUAGESTRING' in n)
    strings = json.loads(bigdir.read(path,member))
    languages[cache] = {k:strings.get(k) for k in ['FC_CUSTOM_SEASON_12','FC_CUSTOM_SEASON_13','FO3_CUSTOM_SEASON_84','COMMON_SEASON_PLUS_NAME_TEXT','COMMON_SEASON_PLUS_NAME_TEXT_OTHER','LEAGUE_MISSION_SEASON_PREFIX_12']}

backup = Path('D:/FO3ID/server/backups/moments-display-20261106-185045-848423/0005.before')
def shapes(p):
    return {struct.unpack_from('<H', b)[0]: (k, b) for k, b, _ in swf(p) if k in (2, 22, 32, 39, 83)}
current, previous = shapes(label), shapes(backup)
comparison = {str(i): dict(unchanged_since_before_moments=current[i] == previous[i],
                         tag_kind=current[i][0], sha256=hashlib.sha256(current[i][1]).hexdigest()) for i in (45, 614, 59, 648)}
with sqlite3.connect((SERVER / 'gamedata/fifadb.sqlite').as_uri()+'?mode=ro', uri=True) as db:
    counts = db.execute('select spid/1000000,count(*) from players where spid/1000000 in (12,13,84) group by 1').fetchall()

pack_findings = []
for name in ['pack_catalogue.json', 'product_packs.json']:
    obj = json.loads((SERVER/'gamedata'/name).read_text('utf-8-sig'))
    def walk(x, path=''):
        if isinstance(x, dict):
            for k, v in x.items(): walk(v, path+'/'+k)
        elif isinstance(x, list):
            for k, v in enumerate(x): walk(v, path+'/'+str(k))
        elif isinstance(x, str) and any(s in x for s in ('12赛季','赛季12','ICON')):
            pack_findings.append(dict(file=name, path=path, value=x))
    walk(obj)
assert protected == {str(p): digest(p) for p in [module, label]}
result = dict(status='READ_ONLY_FINDINGS_NOT_NATIVE_ROOT_CAUSE', inputs=protected,
              season_counts=counts, label_shape_comparison=comparison,
              literal_pack_name_matches=pack_findings,
              language_values=languages, callback12_compared_constants=constants,
              callback12_numeric_fallback=dict(offset=111, default_case=47, seasons_12_13_84_not_intercepted=True,
                  formula='COMMON_SEASON_PLUS_NAME_TEXT(slice("00"+getSeason(spid),-2), playername)'),
              getSeasonString='Explicit season12/13 -> FC_CUSTOM_SEASON_<id>; season84 -> FO3_CUSTOM_SEASON_84',
              remaining_uncertainty='Exact native location of reported 12 season text/badge is unknown; unchanged legacy badge is a candidate, not a confirmed root cause.',
              installed=False, production_written=False, computer_use=False)
(ROOT/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(result,ensure_ascii=True))
