from pathlib import Path
import urllib.request,json,hashlib
R=Path(__file__).resolve().parent/'downloaded-portraits';results=[]
for url in ('https://fifaaddict.com/fo3img/players/p27177844.png','https://fifaaddict.com/fo3img/players/p7569.png','https://fo4.dn.nexoncdn.co.kr/live/externalAssets/common/players/p177844.png'):
 try:
  d=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=15).read();assert d.startswith(b'\x89PNG')
  target=R/('materazzi-'+str(len(results))+'.png');target.write_bytes(d)
  results.append(dict(url=url,path=str(target),sha256=hashlib.sha256(d).hexdigest(),status='OK'))
 except Exception as e:results.append(dict(url=url,error=str(e)))
(R/'materazzi-sources.json').write_text(json.dumps(results,indent=2),'utf-8');print(json.dumps(results))
