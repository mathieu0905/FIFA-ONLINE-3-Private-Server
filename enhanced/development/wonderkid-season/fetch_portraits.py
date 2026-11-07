from pathlib import Path
import concurrent.futures,hashlib,json,struct,urllib.request
R=Path(__file__).resolve().parent;B=R/'install-build-v3';cards=json.loads((B/'cards.json').read_text('utf-8'));previous={r['spid']:r for r in json.loads((R/'portraits-supplement.json').read_text('utf-8'))['rows']} if (R/'portraits-supplement.json').exists() else {}
def fetch(c):
    p=B/'portraits'/f'p{c["fo3_spid"]}.png'
    if p.exists():return previous.get(c['fo3_spid'],dict(spid=c['fo3_spid'],source='existing_native_cache',sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    pid=c['base_playerid'];url=f'https://fco.dn.nexoncdn.co.kr/live/externalAssets/common/players/p{pid}.png'
    try:
        with urllib.request.urlopen(url,timeout=20) as r:data=r.read(2*1024*1024)
        assert data[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',data[16:24]);assert 16<=w<=2048 and 16<=h<=2048
        p.write_bytes(data);return dict(spid=c['fo3_spid'],playerid=pid,url=url,sha256=hashlib.sha256(data).hexdigest(),width=w,height=h)
    except Exception as e:return dict(spid=c['fo3_spid'],url=url,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(fetch,cards))
(R/'portraits-supplement.json').write_text(json.dumps(dict(rows=rows,status='PASS' if all('error' not in r for r in rows) else 'FAIL'),ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(ok=sum('error' not in r for r in rows),errors=[r for r in rows if 'error' in r])))
