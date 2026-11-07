"""Refresh exact-ID Nexon career evidence for the ordinary-legend audit cohort."""
from pathlib import Path
import concurrent.futures
import datetime
import gzip
import hashlib
import importlib.util
import json
import requests
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('career_parser', ROOT.parent / 'club-history/collect.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


def main():
    out = ROOT / 'sources/refreshed'
    out.mkdir(exist_ok=True)
    audit = json.loads((ROOT / ('audit-expanded.json' if '--expanded' in sys.argv else 'audit.json')).read_text('utf8'))
    meta = json.loads((ROOT / 'sources/spid-current.json').read_text('utf-8-sig'))
    choices = {}
    for item in meta:
        choices.setdefault(item['id'] % 1000000, []).append(item)

    def one(player):
        pid = player['playerid']
        destination = out / f'{pid}.json'
        if destination.exists():
            return json.loads(destination.read_text('utf8'))
        options = sorted(choices.get(pid, []), key=lambda x: x['id'], reverse=True)
        errors = []
        for item in options[:2]:
            url = 'https://fconline.nexon.com/DataCenter/PlayerInfo?spid=' + str(item['id'])
            try:
                response = requests.get(url, timeout=(8, 18))
                response.raise_for_status()
                career = parser.parse(response.content.decode('utf-8-sig'))
                raw_path = out / f'{pid}.html.gz'
                raw_path.write_bytes(gzip.compress(response.content, mtime=0))
                result = dict(status='OK', playerid=pid, source_spid=item['id'], name_ko=item['name'],
                    url=url, fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    raw_sha256=hashlib.sha256(response.content).hexdigest(), raw_file=str(raw_path), career=career)
                destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
                time.sleep(.1)
                return result
            except (ValueError, requests.RequestException) as exc:
                errors.append(str(exc))
        result = dict(status='NO_EXACT_ID_SOURCE' if not options else 'UNAVAILABLE', playerid=pid, errors=errors)
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, audit['players']))
    from collections import Counter
    report = dict(status='REFRESH_COMPLETE', metadata_items=len(meta), players=len(results),
        outcomes=dict(Counter(r['status'] for r in results)), formal_files_written=False)
    (ROOT / 'sources/refresh-result.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
