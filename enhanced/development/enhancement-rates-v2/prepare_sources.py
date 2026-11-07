from pathlib import Path
import json,urllib.request,hashlib
W=Path(r'D:\fifaol3\enhancement-rates-v2');S=Path(r'D:\FO3ID\server')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8088/api/enhancement',timeout=8) as r:before=json.load(r)
path=S/'gamedata/enhancement_rates.json';raw=path.read_bytes() if path.exists() else None
if raw is not None:(W/'rates-before.json').write_bytes(raw)
rates=dict(before['rates']);rates.update({str(g):v for g,v in zip(range(11,20),(20,15,12,10,8,6,5,4,3))})
body=json.dumps(dict(rates=rates,revision=before['revision'])).encode()
req=urllib.request.Request('http://127.0.0.1:8088/api/enhancement_set',data=body,headers={'Content-Type':'application/json','X-FO3-Admin':'1'},method='POST')
with op.open(req,timeout=8) as r:after=json.load(r)
assert 'error' not in after,after
assert after['rates']==rates
(W/'hot-save.json').write_text(json.dumps(dict(before=before,after=after,previous_file_existed=raw is not None),indent=2),encoding='utf-8')
print('Saved via existing live admin API:',json.dumps({g:rates[g] for g in map(str,range(11,20))}))
s=(S/'enhancement_progression.py').read_text(encoding='utf-8-sig')
s=s.replace("VERSION = 'progression20-v1'","VERSION = 'progression20-v2'").replace('.55, .50, .45, .35, .28, .20, .14, .09, .06, .04, 0.', '.55, .20, .15, .12, .10, .08, .06, .05, .04, .03, 0.').replace('From current +13:','From current +12:').replace('h.grade_of(pa) < 13','h.grade_of(pa) < 12')
compile(s,'enhancement_progression.py','exec');(W/'enhancement_progression.py').write_bytes(s.replace('\n','\r\n').encode('utf-8'))
for relative,name in [('enhancement_protection40.py','enhancement_protection40.py'),('admin/index.html','index.html')]:
 s=(S/relative).read_text(encoding='utf-8-sig').replace('当前+13起','当前+12起（冲+13）').replace('当前 +13 起','当前 +12 起（冲 +13）')
 (W/name).write_bytes(s.replace('\n','\r\n').encode('utf-8'))
print('Prepared module, protection wording and admin note; price and fee code untouched')
