from pathlib import Path
import sys,json,subprocess,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent));import install
S=install.S;W=install.W
read=lambda:json.loads((S/'gamedata/state.json').read_text(encoding='utf-8-sig'))
business=lambda d:{k:v for k,v in d.items() if k!='market_simulation'}
def fingerprint(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
with install.locks():
 install.gameclosed();proof=install.load(S/install.SELF,'cutover_top').preflight(S,install.C)
 before=read();protected={n:install.tx.digest(S/'gamedata'/n) for n in ('shop.json','enhancement_rates.json','pack_cadence.json','pack_catalogue.json','product_packs.json')}
 ps=r'''
$ErrorActionPreference='Stop'
if(Get-Process fifazf -ErrorAction SilentlyContinue){throw 'Game started; defer reload'}
& 'D:\FO3ID\server\stop-server.ps1'
$env:FO3_GAME='D:\FO3ID\32795'
$env:FO3_LANGUAGE='chi'
$env:FO3_MAX_GRADE='20'
$env:FO3_ADMIN_PORT='8088'
Start-Process -FilePath 'D:\FO3ID\server\.venv\Scripts\python.exe' -ArgumentList '-B','-u','D:\FO3ID\server\start_all.py' -WorkingDirectory 'D:\FO3ID\server' -WindowStyle Hidden -RedirectStandardOutput 'D:\fifaol3\enhancement-protection40\formal.stdout.log' -RedirectStandardError 'D:\fifaol3\enhancement-protection40\formal.stderr.log'
'''
 subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],check=True)
 subprocess.run([str(S/'.venv/Scripts/python.exe'),'-B',str(S/'wait_services.py'),'--timeout','35'],check=True)
 after=read();assert business(before)==business(after),'Unexpected live business change; never restore snapshot'
 assert all(install.tx.digest(S/'gamedata'/n)==v for n,v in protected.items())
 result=dict(status='FORMAL_RELOADED',business_unchanged=True,business_before=fingerprint(business(before)),business_after=fingerprint(business(after)),protected=protected,preflight=proof,gui_or_game_actions=False)
 (W/'cutover-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
