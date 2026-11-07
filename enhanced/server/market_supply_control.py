"""Read/set live market supply settings through the loopback admin API, without restart."""
import argparse,json,urllib.request
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--set',dest='source',help='Complete settings JSON file');p.add_argument('--expected-revision',help='Revision returned by the live read command');a=p.parse_args()
 if a.source and not a.expected_revision:p.error('--set requires --expected-revision')
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 if a.source:
  data=json.loads(Path(a.source).read_text('utf-8-sig'));request=urllib.request.Request('http://127.0.0.1:8088/api/market_supply_config_set',data=json.dumps(dict(revision=a.expected_revision,settings=data),allow_nan=False).encode(),headers={'Content-Type':'application/json','X-FO3-Admin':'1'})
 else:request='http://127.0.0.1:8088/api/market_supply_config'
 with opener.open(request,timeout=10) as response:r=json.load(response)
 print(json.dumps(r,ensure_ascii=False,indent=2))
 if r.get('error'):raise SystemExit(1)
 if a.source and r['active_revision']!=r['revision']:raise SystemExit('Configuration not active')
if __name__=='__main__':main()
