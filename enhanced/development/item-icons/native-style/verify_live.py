from pathlib import Path
import http.client,ssl,json,hashlib,concurrent.futures
R=Path(__file__).resolve().parent;m=json.loads((R/'all_item_icon_manifest.json').read_text('utf8'));ctx=ssl._create_unverified_context()
def conn():return http.client.HTTPSConnection('127.0.0.1',443,context=ctx,timeout=25)
c=conn();request=json.dumps(dict(itemids=list(map(int,m['items'])))).encode();c.request('POST','/static/cache/item',request,{'Content-Type':'application/json'});response=c.getresponse();assert response.status==200;data=json.loads(response.read());c.close()
checked=0
def walk(v):
 global checked
 if isinstance(v,list):
  for x in v:walk(x)
 elif isinstance(v,dict):
  if 'itemicon' in v:
   i=str(v.get('itemid',v.get('productid',0)))
   if i in m['items']:assert v['itemicon']==m['items'][i]['icon'],(i,v['itemicon']);checked+=1
  for x in v.values():walk(x)
walk(data)
c=conn();c.request('GET','/shop/list');r=c.getresponse();assert r.status==200;shop=json.loads(r.read());c.close();walk(shop)
rows=list(m['items'].values());groups=[rows[i::8] for i in range(8)]
def fetch(group):
 c=conn();n=0
 try:
  for row in group:
   c.request('GET','/cdn/externalAssets/shop/'+row['filename']);r=c.getresponse();raw=r.read();assert r.status==200,(row['filename'],r.status);assert r.getheader('Content-Type').startswith('image/png');assert hashlib.sha256(raw).hexdigest()==row['sha256'];n+=1
 finally:c.close()
 return n
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:downloaded=sum(pool.map(fetch,groups))
result=dict(status='PASS',static_api_definitions=len(data),nested_icon_checks=checked,shop_rows=len(shop),cdn_images_downloaded_and_sha256_verified=downloaded,expected_images=len(rows),native_verified=False,state_shop_written=False)
(R/'live-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
