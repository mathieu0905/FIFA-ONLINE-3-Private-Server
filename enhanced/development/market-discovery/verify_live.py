import urllib.request,ssl,json,time,sqlite3,collections
from pathlib import Path
root=Path('D:/fifaol3/market-discovery')
with urllib.request.urlopen('http://127.0.0.1:8088/api/market_status',timeout=20) as r:s=json.load(r)
with urllib.request.urlopen('https://127.0.0.1/transfer/top/50',context=ssl._create_unverified_context(),timeout=20) as r:rows=json.load(r)
assert s['discovery_refresh_seconds']==300 and s['background']['running'] and s['background']['errors']==0
assert len(rows)==50 and sum(x['grade']>=11 for x in rows)<=16
assert sum(7<=x['grade']<=10 for x in rows)>=34
(root/'live-first.json').write_text(json.dumps(dict(at=time.time(),rows=rows,status=s),indent=2),'utf8')
before=json.loads((root/'state-before.json').read_text('utf8'));after=json.loads(Path('D:/FO3ID/server/gamedata/state.json').read_text('utf8'))
assert before['coaches']==after['coaches'] and before['teams']==after['teams']
print(json.dumps(dict(rows=len(rows),rare_rows=sum(x['grade']>=11 for x in rows),regular_high=sum(7<=x['grade']<=10 for x in rows),background=s['background'],seconds_to_next_rotation=300-int(time.time())%300,assets_unchanged=True),ensure_ascii=False))
