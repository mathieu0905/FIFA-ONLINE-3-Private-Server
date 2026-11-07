"""Read-only verification of installed removal and runtime lookup boundaries."""
from pathlib import Path
import json,sqlite3,ssl,urllib.request,urllib.parse,sys
import build as b
import install as i
def get(url):
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
 with op.open(url,timeout=20) as r:return json.load(r)
def main():
 hand=i.read(b.W/'installed-handback.json');assert hand['status']=='INSTALLED_RUNTIME_ACTIVE_NATIVE_PENDING'
 backup=Path(hand['backup']);before=json.loads((backup/'fresh-state.json').read_bytes());current=i.read(b.S/'gamedata/state.json')
 expected,counts=i.migrate(before)
 assert before['coaches']==expected['coaches'] and before['teams']==expected['teams'],'Unexpected owned target present in fresh snapshot'
 business=lambda s:{k:v for k,v in s.items() if k!='market_simulation'}
 assert business(current)==business(expected),'Business progress changed; inspect instead of restoring old state'
 assert (b.S/'gamedata/shop.json').read_bytes()==(backup/'fresh-shop.json').read_bytes()
 with sqlite3.connect((b.S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('select count(*) from players where playerid=231747 or spid%1000000=231747').fetchone()[0]==0
 api={}
 for sid in sorted(b.IDS):
  rows=get('https://127.0.0.1/transfer/search/'+str(sid));assert rows==[],(sid,rows);api[str(sid)]=rows
 admin={}
 for q in ('Mbapp','姆巴佩'):
  data=get('http://127.0.0.1:8088/api/search?'+urllib.parse.urlencode({'q':q}));assert isinstance(data,dict) and 'rows' in data,data
  assert all(not b.blocked(r['spid']) for r in data['rows']);admin[q]=data
 hot=get('http://127.0.0.1:8088/api/hot_update_status');assert hot['revision']==hand['hot_update_status']['revision'] and hot['watcher_running'] and hot['error'] is None
 market=current.get('market_simulation',{});assert not any(b.blocked(k.split(':')[0]) for key in ('books','quotes','rare_books') for k in market.get(key,{}))
 assert not any(b.blocked(r.get('spid')) for r in market.get('npc_exchange',{}).get('assets',{}).values())
 result=dict(status='PASS',market_lookup=api,admin_lookup=admin,hot_update=hot,owned_cards_and_teams_preserved=True,balances_experience_inventory_receipts_preserved=True,shop_exact=True,nonmarket_state_exact=True,removed_active=counts,services_ready=i.ports()==[443,8088,28002],GUI_used=False,native_runtime_verified=False,match_verified=False)
 b.write(b.W/'live-verification.json',result);print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
