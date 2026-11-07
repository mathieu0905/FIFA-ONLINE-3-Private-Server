from pathlib import Path
import sys,json,urllib.request,ssl,time,sqlite3,copy
R=Path('D:/fifaol3/npc-peer-market');S=Path('D:/FO3ID/server')
with urllib.request.urlopen('http://127.0.0.1:8088/api/market_status',timeout=20) as r:s=json.load(r)
w=s['npc_exchange'];assert w['peer_trades']>0,w
assert s['background']['running'] and s['background']['errors']==0
state=json.loads((S/'gamedata/state.json').read_text('utf8'));world=state['market_simulation']['npc_exchange']
assert sum(a['wallet'] for a in world['agents'])+world['supplier_wallet']+world['fees']==32*10**15+sum(e['price'] for e in world['history'] if e['kind']=='npc_to_player')
assert world['source_buys']-world['human_buys']==len(world['assets'])
peer=[e for e in w['recent_trades'] if e['kind']=='npc_peer'];assert all(e['buyer']!=e['seller'] for e in peer)
listings=[a['listing'] for a in world['assets'].values() if 'listing' in a]
listing=listings[0]
with urllib.request.urlopen('https://127.0.0.1/transfer/search/'+str(listing['spid']),context=ssl._create_unverified_context(),timeout=20) as r:rows=json.load(r)
assert any(all(row.get(k)==listing[k] for k in ('spid','grade','price','count')) for row in rows)
assert all(not any(k.startswith('_market_') for k in row) for row in rows)
sys.path.insert(0,str(S));from npc_attribute_value import AttributeValueModel
model=AttributeValueModel(S/'gamedata/npc_attribute_value.json')
with sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;card=dict(db.execute('select * from players where spid=?',(listing['spid'],)).fetchone())
with urllib.request.urlopen('https://127.0.0.1/transfer/price/'+str(listing['spid'])+'/1',context=ssl._create_unverified_context(),timeout=20) as r:quote=json.load(r)
assert quote['default']==max(1,model.predict(card)//1000),(quote,model.predict(card))
report=dict(at=time.time(),background=s['background'],npc=w,conservation_verified=True,card_quantity_verified=True,native_search_exposes_listing=True,attribute_base_quote_verified=True,first_peer=peer[0],native_gui_verified=False)
(R/'live-peer-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('npc',)},ensure_ascii=False));print('COUNTS',w['source_buys'],w['peer_trades'],w['listed_cards'])
