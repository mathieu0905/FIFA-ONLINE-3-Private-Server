"""Collect dated club careers from the current public Nexon datacenter.

This never writes any installed game/server file. Raw replies are retained compressed.
Only exact EA player IDs and the datacenter's exact team-name/EA-team-ID map are used.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
import datetime, gzip, hashlib, json, re, sqlite3, threading, time
import requests

HERE = Path(__file__).resolve().parent
DB = Path('D:/FO3ID/server/gamedata/fifadb.sqlite')
LOCAL = threading.local()

def write(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    tmp.replace(path)

def clean(s):
    return unescape(re.sub('<[^>]+>', '', s)).strip()

def parse(text):
    start = text.find('data_detail_club')
    if start < 0:
        raise ValueError('No club career section')
    end = text.find('</ul>', start)
    if end < 0:
        raise ValueError('Unterminated club career list')
    rows = []
    for li in re.findall(r'<li\b[^>]*>(.*?)</li>', text[start:end], re.S):
        values = {}
        for key in ('year', 'club', 'rent'):
            m = re.search(r'class="td ' + key + r'"[^>]*>(.*?)</div>', li, re.S)
            if not m:
                raise ValueError('Malformed career row: ' + key)
            values[key] = clean(m.group(1))
        years = re.fullmatch(r'(\d{4})\s*~\s*(\d{4})?', values['year'])
        if not years or values['rent'] not in ('', '임대'):
            raise ValueError('Unexpected career date/rent format: ' + repr(values))
        joined, ended = int(years[1]), int(years[2]) if years[2] else -1
        if not 1850 <= joined <= 2026 or (ended != -1 and not joined <= ended <= 2026):
            raise ValueError('Invalid career years')
        rows.append(dict(club_ko=values['club'], joinedyear=joined, endyear=ended,
                         loan=int(values['rent'] == '임대')))
    if not rows:
        raise ValueError('Empty career section')
    return rows

def main():
    (HERE/'records').mkdir(exist_ok=True)
    (HERE/'raw').mkdir(exist_ok=True)
    meta = json.loads((HERE/'spid.json').read_text('utf8'))
    choices = {}
    for p in meta:
        choices.setdefault(p['id'] % 1000000, []).append(p)
    with sqlite3.connect('file:' + DB.as_posix() + '?mode=ro', uri=True) as c:
        ids = {r[0] for r in c.execute('select distinct playerid from players')}
        licensed = {r[0] for r in c.execute('select distinct p.playerid from players p join permid m using(spid) where m.licensed=1')}
    state = json.loads((DB.parent/'state.json').read_text('utf8'))
    owned = set()
    def walk(v):
        if isinstance(v, dict):
            if 'spid' in v:
                try: owned.add(int(v['spid']) % 1000000)
                except (ValueError, TypeError): pass
            for x in v.values(): walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
    walk(state)
    selected = sorted(ids & choices.keys(), key=lambda p: (p not in owned, p not in licensed, p))
    write(HERE/'collection-plan.json', dict(source='https://fconline.nexon.com/DataCenter/PlayerInfo',
          metadata_url='https://open.api.nexon.com/static/fconline/meta/spid.json',
          requested_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
          installed_player_ids=len(ids), source_match_ids=len(selected),
          licensed_match_ids=len(licensed & choices.keys()),
          owned_match_ids=len(owned & choices.keys()), not_in_source=sorted(ids - choices.keys()),
          player_ids=selected))

    def fetch(pid):
        target = HERE/'records'/f'{pid}.json'
        if target.exists():
            record = json.loads(target.read_text('utf8'))
            if record.get('status') == 'OK': return record
        if not hasattr(LOCAL, 'session'):
            LOCAL.session = requests.Session()
            LOCAL.session.headers.update({'User-Agent':'FO3-club-career-sync/1.0 (public datacenter, read-only)',
                                          'Accept-Language':'ko-KR'})
        candidates = sorted(choices[pid], key=lambda x: x['id'], reverse=True)
        errors = []
        for item in candidates[:2]:
            url = 'https://fconline.nexon.com/DataCenter/PlayerInfo?spid=' + str(item['id'])
            try:
                for attempt in range(2):
                    response = LOCAL.session.get(url, timeout=(6, 15))
                    if response.status_code not in (429, 503): break
                    time.sleep(3 * (attempt + 1))
                response.raise_for_status()
                body = response.content
                rows = parse(body.decode('utf-8-sig'))
                raw = HERE/'raw'/f'{pid}.html.gz'
                raw.write_bytes(gzip.compress(body, mtime=0))
                record = dict(status='OK', playerid=pid, source_spid=item['id'], name_ko=item['name'],
                              url=url, fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                              raw_sha256=hashlib.sha256(body).hexdigest(), raw_file=str(raw), career=rows)
                write(target, record)
                time.sleep(.08)
                return record
            except (requests.RequestException, ValueError) as exc:
                errors.append(type(exc).__name__ + ': ' + str(exc))
        record = dict(status='UNAVAILABLE', playerid=pid, errors=errors)
        write(target, record)
        return record

    started = time.monotonic()
    done = good = 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(fetch, pid) for pid in selected]
        for f in as_completed(futures):
            r = f.result();done += 1;good += r['status'] == 'OK'
            if done % 100 == 0 or done == len(selected):
                report = dict(total=len(selected), completed=done, good=good,
                              unavailable=done-good, elapsed_s=round(time.monotonic()-started,1))
                write(HERE/'collection-progress.json', report)
                print(json.dumps(report), flush=True)
    print('COLLECTION_COMPLETE', flush=True)

if __name__ == '__main__': main()
