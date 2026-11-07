"""Read-only formal roster, valuation-generation, hot-route and asset checks."""
from pathlib import Path
import collections,importlib.util,json,sqlite3,ssl,urllib.request
P=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('nostalgia87_transaction',P/'install.py');x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x)
S,C=x.S,x.C;read=x.read;t=x.t
def api(path):
 with urllib.request.urlopen('http://127.0.0.1:8088/api/'+path,timeout=30) as response:assert response.status==200;return json.load(response)
def assets(state):return {k:v for k,v in state.items() if k!='market_simulation'}
i=read(P/'installed-handback.json');out=Path(i['build']);report=read(out/'report.json');changes=read(out/'changes.json')
for name,path in [('fifadb.sqlite',S/'gamedata/fifadb.sqlite'),('data_0.big',C/'data/data_0.big'),('custom_rosters.json',S/'gamedata/custom_rosters.json'),('static_roster.json',S/'responses/static_roster.json')]:assert x.sha(path)==report['outputs'][name],path
weights=x.b.resource.weights();actual=[]
with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;rows=[dict(r) for r in db.execute('select * from players where spid/1000000=19')];assert len(rows)==88
 for r in rows:
  rating=x.b.resource.primary(r,weights);assert r['overallrating']==rating;actual.append(rating)
 assert sum(actual)==88*87 and max(actual)==93 and 92 in actual and min(actual)==85
 for change in changes:
  live=api('database_detail?spid='+str(change['spid']));assert live['ovr']==change['after_base'] and live['row']['overallrating']==change['after_base']
 roster=read(S/'responses/static_roster.json');scores=[]
 for e in roster['seasons']:
  values=[x.b.resource.primary(dict(r),weights) for r in db.execute('select * from players where spid/1000000 in ('+','.join('?' for _ in e['value'])+')',e['value'])];scores.append(sum(values)/len(values))
 assert scores==sorted(scores,reverse=True)
before=read(P/'fresh-stop-snapshot'/i['revision']/'state.json');now=read(S/'gamedata/state.json');assert assets(before)==assets(now)
for path,h in i['protected'].items():assert x.sha(path)==h,path
certificate=x.load(S/'tools/player_import/check.py','nostalgia87_after_import').validate(S,C);assert certificate['status']=='PLAYER_IMPORT_CERTIFICATE_PASS'
preflight=x.load(S/x.SELF,'nostalgia87_after_preflight').preflight(S,C)
with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 metadata=dict(db.execute('select key,value from metadata'));assert metadata['fair_revision']==x.b.TAG and metadata['fair_source_database']==str(S/'gamedata/fifadb.sqlite')
for sid in [19001040,19005740,19188428,19204550]:
 for grade in [1,10,20]:
  price=api(f'market_price_store?spid={sid}&grade={grade}');assert price['active_valuation_revision']==x.b.TAG and price['value']>0
hot=api('hot_update_status');assert hot['revision']==i['expected_hot_revision'] and hot['watcher_running'] and hot['error'] is None
market=api('market_status');assert market['background']['running'] and market['background']['errors']==0 and market['background']['last_error'] is None
result=dict(status='PASS',cards=88,primary_base_mean=87.0,primary_base_range=[85,93],distribution=dict(sorted(collections.Counter(actual).items())),all_88_live_rating_probes=True,unrelated_database_rows_and_identity_fields_preserved=True,real_manager_assets_experience_grades_balances_inventory_and_team_preserved=True,state_market_generation_migration_only=True,player_import=certificate['status'],profile_binding=preflight,market_background=market['background'],hot_status=hot,services_ready=t.listening()==[443,8088,28002],native_home_close_far_dribbling_and_match_verified=False,game_gui_used=False)
x.save(P/'verification.json',result);i.update(status='INSTALLED_AND_LIVE_PASS_NATIVE_PENDING',verification=str(P/'verification.json'),verification_status='PASS',services_restored=result['services_ready'],hot_status=hot);x.save(P/'installed-handback.json',i)
dpath=x.b.W/'root-current-top.json';d=read(dpath)
if d.get('top_preflight')==str(S/x.SELF):d.update(status=i['status'],revision=i['revision'],backup=i['backup'],composition_api=i['composition_api'],verification=str(P/'verification.json'),preflight=preflight,services_restored=result['services_ready'],hot_status=hot,state_market_migration_only=True,shop_written=False,real_assets_preserved=True);t.atomic(t.body(d),dpath)
registry=read(S/'gamedata/custom_rosters.json');names={c['fo3_spid']:c['name_zh'] for c in registry['cards']};lines=['怀旧神兽：88人，主位置基础能力平均87.00，范围85～93。','不额外计算强化、等级和队套加成。','']+[str(c['after_base'])+'  '+names[c['spid']]+'  SPID '+str(c['spid']) for c in sorted(changes,key=lambda c:(-c['after_base'],c['spid']))];(P/'怀旧神兽能力名单.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('profile_binding','market_background')},ensure_ascii=True))
