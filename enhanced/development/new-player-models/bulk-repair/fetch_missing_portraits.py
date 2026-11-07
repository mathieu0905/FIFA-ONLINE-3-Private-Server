import concurrent.futures,json,pathlib,urllib.request,urllib.error
R=pathlib.Path(__file__).resolve().parent/'portraits';R.mkdir(exist_ok=True)
urls=[(pid,f'https://fco.dn.nexoncdn.co.kr/live/externalAssets/common/{folder}/p{prefix}{pid}.png') for pid in [245,249] for folder,prefix in [('players',''),('playersAction','101000'),('playersAction','')]]
def fetch(item):
    pid,url=item
    try:
        with urllib.request.urlopen(url,timeout=15) as response:body=response.read(2*1024*1024)
        if not body.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Not PNG')
        target=R/(str(pid)+'-'+url.split('/')[-2]+'-'+url.split('/')[-1]);target.write_bytes(body)
        return dict(playerid=pid,url=url,path=str(target),bytes=len(body))
    except Exception as e:return dict(playerid=pid,url=url,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,urls))
(R/'sources.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(json.dumps(rows))
