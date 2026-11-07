"""Cache official FC abilities and portraits for existing-identity FO3 expansion."""
from pathlib import Path
import ast, concurrent.futures, datetime, hashlib, json, re, sqlite3, threading, time
import urllib.error, urllib.parse, urllib.request
import shutil

ROOT = Path(__file__).resolve().parent
WORK = Path('C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online')
OUT = ROOT / 'bulk-sources'
OUT.mkdir(exist_ok=True)
SOURCE = OUT / 'official'
SOURCE.mkdir(exist_ok=True)
tree = ast.parse((WORK / 'work/roster_extension/fc_source/fetch_official_cards.py').read_text('utf-8'))
LABELS = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'labels' for t in n.targets))
metadata = json.loads((WORK / 'work/season_expansion/spid.json').read_text('utf-8-sig'))
icons = json.loads((WORK / 'work/season_expansion/model_compatible_icons.json').read_text('utf-8'))
modern24 = json.loads((WORK / 'work/modern_roster_completion/official24.json').read_text('utf-8'))
modern_lookup = {r['playerid']: r for r in modern24}
db = sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro', uri=True)
db.row_factory = sqlite3.Row
existing = {r[0] for r in db.execute('select distinct playerid from players where spid>=1000000')}
issued = {r[0] for r in db.execute('select playerid from players where spid/1000000=13')}
rows = []
backlog = []
for meta in metadata:
    if meta['id'] // 1000000 != 519:
        continue
    pid = meta['id'] % 1000000
    if pid in issued:
        backlog.append(dict(fc_spid=meta['id'], playerid=pid, reason='existing issued season13 card preserved; new same-slot replacement forbidden'))
        continue
    if pid not in existing and pid not in modern_lookup:
        backlog.append(dict(fc_spid=meta['id'], playerid=pid, name_ko=meta['name'], reason='new identity lacks a reviewed FO3 model/template'))
        continue
    name = db.execute('select full,full_eng from nameschi where playerid=?', (pid,)).fetchone()
    rows.append(dict(group='modern', playerid=pid, fc_spid=meta['id'], name_ko=meta['name'],
                     name_zh=modern_lookup[pid]['name_zh'] if pid in modern_lookup else name['full'],
                     name_en=modern_lookup[pid]['name_en'] if pid in modern_lookup else name['full_eng']))
for row in icons:
    name = db.execute('select full from nameschi where playerid=?', (row['playerid'],)).fetchone()
    rows.append(dict(group='icon', playerid=row['playerid'], fc_spid=row['fc_spid'], name_zh=name['full'],
                     name_en=row['names']['full_eng'], template_spid=row['template']['spid']))
assert len(rows) == 378 and len({r['fc_spid'] for r in rows}) == 378
jobs = sorted(rows, key=lambda r: (r['group'], r['fc_spid']))
write_lock = threading.Lock()
rate_lock = threading.Lock()
last_request = 0.0


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def get(url, params=None):
    global last_request
    with rate_lock:
        delay = .45 - (time.monotonic() - last_request)
        if delay > 0:
            time.sleep(delay)
        last_request = time.monotonic()
    headers = {'User-Agent': 'Mozilla/5.0 (FO3 offline roster research)',
               'Referer': 'https://fconline.nexon.com/DataCenter/', 'X-Requested-With': 'XMLHttpRequest'}
    request = urllib.request.Request(url, data=None if params is None else urllib.parse.urlencode(params).encode(), headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                assert response.status == 200
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def cache_ability(spid):
    path = SOURCE / f'{spid}-ability.html'
    if path.exists():
        return path, path.read_bytes(), 'bulk-cache'
    for old in [WORK / f'work/season_expansion/official/{spid}-ability.html',
                WORK / f'work/modern_roster_completion/official_abilities/{spid}.html',
                WORK / f'work/modern_players/official/{spid}-ability.html']:
        if old.exists():
            raw = old.read_bytes()
            path.write_bytes(raw)
            return path, raw, str(old)
    params = dict(spid=spid, n1Strong=1, n1Grow=0, n4TeamColorId=0, n4TeamColorLv=0,
                  n4TeamColorId_Enhance=0, n4TeamColorLv_Enhance=0, n4TeamColorId_Feature=0, n1Change=0, strPlayerImg='')
    raw = get('https://fconline.nexon.com/datacenter/PlayerAbility', params)
    path.write_bytes(raw)
    return path, raw, 'official-network'


def fetch(row):
    spid = row['fc_spid']
    try:
        path, raw, origin = cache_ability(spid)
        html = raw.decode('utf-8', 'strict')
        pairs = re.findall(r'<li class="ab"[^>]*>\s*<div class="txt">(.*?)</div>\s*<div class="value[^\"]*">\s*(\d+)', html, re.S)
        stats = {LABELS[k]: int(v) for k, v in pairs if k in LABELS}
        assert len(stats) == 34, ('expected34stats', len(stats))
        ovr = int(re.search(r'<div class="ovr value">(\d+)</div>', html)[1])
        position = re.search(r'<div class="position">\s*(.*?)\s*</div>', html, re.S)[1].strip()
        def field(cls):
            match = re.search(r'<span class="etc ' + cls + r'">(.*?)</span>', html, re.S)
            return re.sub('<[^>]+>', '', match[1]).strip() if match else None
        def imageid(pattern):
            match = re.search(pattern, html)
            return int(match[1]) if match else None
        portrait = SOURCE / f'{spid}-portrait.png'
        portrait_url = None
        if not portrait.exists():
            old = WORK / f'work/season_expansion/official/{spid}-portrait.png'
            if old.exists():
                portrait.write_bytes(old.read_bytes())
                portrait_url = 'existing official snapshot'
            else:
                urls = re.findall(r'(?:src|value)="(https://[^\"]+/playersAction/[^\"]+\.png)"', html)
                portrait_url = urls[0] if urls else f'https://fco.dn.nexoncdn.co.kr/live/externalAssets/common/playersHigh/p{row["playerid"]}.png'
                try:
                    portrait.write_bytes(get(portrait_url))
                except (urllib.error.URLError, OSError) as error:
                    # A season action image may be unavailable; reuse only a same-PID original.
                    fallback = None
                    for cache in [Path('D:/FO3ID/32795/_cache/games/fo3id/externalAssets/players'), Path('D:/FO3ID/32795/_cache/cdn/externalAssets/players')]:
                        for candidate in cache.glob(f'p*{row["playerid"]}.png'):
                            suffix = candidate.stem[1:]
                            if suffix.isdigit() and int(suffix) % 1000000 == row['playerid'] and candidate.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                                fallback = candidate
                                break
                        if fallback is not None:
                            break
                    if fallback is None:
                        raise
                    portrait.write_bytes(fallback.read_bytes())
                    portrait_url = str(fallback) + ' (same-PID fallback; official action image unavailable)'
        assert portrait.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        return row | dict(status='READY_OFFICIAL_SNAPSHOT', stats=stats, ovr=ovr, primary_position=position,
                          physical={k: field(v) for k, v in dict(height='height', weight='weight', birthdate='birth', body_type='physical').items()},
                          nationality=imageid(r'/countries/smallflags/(\d+)\.png'),
                          teamid=imageid(r'/crests/light/small/l(-?\d+)\.png'), leagueid=imageid(r'/league/light/ca/l(-?\d+)\.png'),
                          raw_file=str(path), raw_sha256=digest(raw), raw_origin=origin,
                          portrait_file=str(portrait), portrait_sha256=digest(portrait.read_bytes()), portrait_url=portrait_url,
                          endpoint='https://fconline.nexon.com/datacenter/PlayerAbility',
                          checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except (OSError, ValueError, AssertionError, TypeError, IndexError, UnicodeError) as error:
        return row | dict(status='SOURCE_FAILED', error=f'{type(error).__name__}: {error}')


if __name__ == '__main__':
    (OUT / 'backlog.json').write_text(json.dumps(backlog, ensure_ascii=False, indent=2), 'utf-8')
    previous = json.loads((OUT / 'sources.json').read_text('utf-8')) if (OUT / 'sources.json').exists() else []
    if len(previous) == len(jobs):
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        shutil.copyfile(OUT / 'sources.json', OUT / f'sources-before-retry-{stamp}.json')
    completed = {r['fc_spid']: r for r in previous if r['status'] == 'READY_OFFICIAL_SNAPSHOT'}
    for row in completed.values():
        if row.get('teamid') is None:
            html = Path(row['raw_file']).read_text('utf-8')
            match = re.search(r'/crests/light/small/l(-?\d+)\.png', html)
            if match:
                row['teamid'] = int(match[1])
                if row['teamid'] == -1 and row.get('leagueid') is None:
                    row['leagueid'] = -1
                    row['club_policy'] = 'official free-agent sentinel -1; no club inferred'
    results = list(completed.values())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch, row): row for row in jobs if row['fc_spid'] not in completed}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            (OUT / 'sources.json').write_text(json.dumps(sorted(results, key=lambda r:r['fc_spid']), ensure_ascii=False, indent=2), 'utf-8')
            if len(results) % 20 == 0 or result['status'] != 'READY_OFFICIAL_SNAPSHOT':
                print(json.dumps(dict(done=len(results), total=len(jobs), failed=sum(r['status'] != 'READY_OFFICIAL_SNAPSHOT' for r in results), last=result['fc_spid'], status=result['status'])), flush=True)
    (OUT / 'sources.json').write_text(json.dumps(sorted(results, key=lambda r:r['fc_spid']), ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(dict(done=len(results), ready=sum(r['status'] == 'READY_OFFICIAL_SNAPSHOT' for r in results), failed=sum(r['status'] != 'READY_OFFICIAL_SNAPSHOT' for r in results))), flush=True)
