from pathlib import Path
import json,ssl,urllib.request,hashlib
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(uri):
 with op.open('https://127.0.0.1'+uri,timeout=30) as r:return json.load(r)
rows=get('/shop/list');chains=[x for x in rows if isinstance(x.get('chained'),list) and x['chained']];verified=[]
for row in chains:
 parts=[row]+row['chained'];assert row['round_buy_supported']
 for index,p in enumerate(parts):
  if index:assert p.get('chained') is True,(row['shopid'],index)
 if row['round_buy_enabled']:
  q=get('/shop/chain/round/quote?root='+str(row['shopid']));assert q['result'] and q['quote']['total']==row['round_buy_total'];assert len(q['quote']['steps'])==row['round_buy_stages']
 verified.append(dict(root=row['shopid'],current_step=row['step'],one_click_supported=row['round_buy_supported'],one_click_enabled=row['round_buy_enabled'],all_child_native_chain_flags=True))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();build=json.loads((R/'build.json').read_text('utf8'))
assert sha(C/'data/ui/components/TileList.big')==sha(S/'patches/TileList.big')==build['client_after'];assert sha(S/'product_packs.py')==build['server_before']
report=dict(status='PASS',chains=verified,client_and_launch_install_source_match=True,state_shop_written=False,real_purchase_executed=False,native_verified=False)
(R/'live-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report))
