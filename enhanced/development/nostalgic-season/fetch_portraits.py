"""Download missing historical mini faces into this task's work directory only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request
R=Path(__file__).resolve().parent;spec=json.loads((R/'roster-audit.json').read_text('utf-8'))
O=R/'downloaded-portraits';O.mkdir(exist_ok=True)
def get(card):
 pid=card['base_playerid'];target=O/f'p{pid}.png';url=f'https://fifaaddict.com/fo3img/players/p{pid}.png'
 try:
  if not target.exists():
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
   data=urllib.request.urlopen(req,timeout=25).read();assert data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)<1024*1024
   target.write_bytes(data)
  return dict(pid=pid,url=url,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='OK')
 except Exception as e:return dict(pid=pid,url=url,status='FAILED',error=str(e))
cache=Path('D:/FO3ID/32795/_cache/games/fo3id/externalAssets/players')
todo=[r for r in spec['cards'] if not any((cache/f'p{p}.png').exists() for p in (r['template_spid'],r['base_playerid']))]
with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(get,todo))
(O/'sources.json').write_text(json.dumps(results,indent=2),'utf-8')
print(json.dumps(dict(total=len(results),ok=sum(r['status']=='OK' for r in results),failed=[r for r in results if r['status']!='OK']),ensure_ascii=True))
