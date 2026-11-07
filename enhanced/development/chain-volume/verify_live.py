from pathlib import Path
import urllib.request,ssl,json
R=Path(__file__).resolve().parent
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def get(url):
 with op.open(url,timeout=15) as response:return json.load(response)
status=get('http://127.0.0.1:8088/api/hot_update_status');assert status['revision']=='chain_volume110_20261107_01' and status['error'] is None and status['watcher_running']
plan=json.loads((R/'plan.json').read_text('utf8'));rows=get('https://127.0.0.1/shop/list');chains=[r for r in rows if isinstance(r.get('chained'),list)];assert len(chains)==5
quotes=[]
for row in chains:
 root=row['shopid'];parts=[row]+row['chained']
 for k,part in enumerate(parts):
  if part.get('currentstep')=='complete':continue
  d=part['product']['staticdata'];p=plan[str(root)]['packages'][str(part['product']['itemid'])]
  assert sum(i['count'] for i in d['items'])==[5,10,20,30,45][k]
  assert d['bunches'][0]['price']==p['price'] and str(p['count'])+'包' in d['name']
 q=get('https://127.0.0.1/shop/chain/round/quote?root='+str(root))
 if not q.get('result'):continue
 q=q['quote'];expected=sum([5,10,20,30,45][q['stage']:]);assert sum(n for i,n in q['rewards'])==expected
 assert q['total']==sum(plan[str(root)]['prices'][str(i)] for i in q['steps'])==row['round_buy_total']
 quotes.append(dict(root=root,round=q['round'],start_stage=q['stage']+1,remaining_pack_count=expected,total=q['total']))
report=dict(status='LIVE_ACTIVE_PASS',hot_status=status,active_chains=5,full_round_packs=110,counts=[5,10,20,30,45],quotes=quotes,no_real_purchase=True,native_verified=False)
(R/'live-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report))
