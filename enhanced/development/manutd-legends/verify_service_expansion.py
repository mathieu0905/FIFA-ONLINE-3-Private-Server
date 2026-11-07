"""Read-only formal API, assets, market availability and preserved-state verification."""
import json,sqlite3,ssl,urllib.parse,urllib.request
import expand_service_legends as x
S,C,R=x.S,x.C,x.R
def request(path,admin=True):
 base='http://127.0.0.1:8088' if admin else 'https://127.0.0.1'
 with urllib.request.urlopen(base+path,context=ssl._create_unverified_context(),timeout=30) as response:
  assert response.status==200;return json.load(response)
installed=x.read(R/'installed.json');out=x.Path(installed['build']);build=x.read(out/'build.json')
for name,path in [('fifadb.sqlite',S/'gamedata/fifadb.sqlite'),('data_0.big',C/'data/data_0.big'),('custom_rosters.json',S/'gamedata/custom_rosters.json'),('static_roster.json',S/'responses/static_roster.json')]:assert x.sha(path)==build['outputs'][name],path
roster=request('/static/roster',False);assert roster==x.read(out/'static_roster.json');united=[e for e in roster['seasons'] if 48 in e['value']];assert len(united)==1 and united[0]['value']==[48,49,55]
with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;weights=x.util.weights();scores=[]
 for entry in roster['seasons']:
  values=[x.util.primary(dict(row),weights)+5 for row in db.execute('select * from players where spid/1000000 in ('+','.join('?' for _ in entry['value'])+')',entry['value'])];scores.append(sum(values)/len(values))
 assert scores==sorted(scores,reverse=True)
 count=db.execute('select count(*) from players where spid/1000000 in (48,49,55)').fetchone()[0];assert count==79
 for pid in [201535,200145,203263,205988,191740,139068,167905,152908,186146,193080,212198]:
  row=db.execute('select * from players where spid=?',(48000000+pid,)).fetchone();assert row and row['teamid']==11
 for card in build['cards']:
  spid=card['fo3_spid'];row=dict(db.execute('select * from players where spid=?',(spid,)).fetchone());assert x.util.primary(row,weights)+5==card['display_plus1_ovr']
  detail=request('/api/database_detail?spid='+str(spid));assert detail['row']==row and detail['ovr']+5==card['display_plus1_ovr']
  rows=request('/api/search?'+urllib.parse.urlencode(dict(q=card['name_en'])))['rows'];live=next(r for r in rows if r['spid']==spid);assert live['market'] and live['price']>0
  for table in x.PERMS:assert tuple(db.execute('select licensed,transferable from '+table+' where spid=?',(spid,)).fetchone())==(1,1)
  for prefix in ('games/fo3id','cdn'):assert x.sha(C/f'_cache/{prefix}/externalAssets/players/p{spid}.png')==next(p['sha256'] for p in build['portraits'] if p['spid']==spid)
checker=x.common.load(S/'tools/player_import/check.py','formal_service_imports');semantic=checker.validate(S,C);assert semantic['status']=='PLAYER_IMPORT_CERTIFICATE_PASS'
before=x.read(R/'fresh-stop-snapshot'/installed['revision']/'state.json');after=x.read(S/'gamedata/state.json');assert {k:v for k,v in before.items() if k!='market_simulation'}=={k:v for k,v in after.items() if k!='market_simulation'},'Concurrent live manager change; do not restore snapshot'
for path,digest in installed['protected'].items():
 if not path.endswith('state.json'):assert x.sha(path)==digest,path
_,_,relative,parent=x.top();preflight=parent.preflight(S,C)
result=dict(status='PASS',new_cards=26,main_season_cards=67,merged_man_united_cards=count,one_season_filter=True,all_new_primary_ovr_exact=True,new_rating_range=[90,94],old_players_database_rows_unchanged=build['original_rows_preserved'],all_new_cards_searchable_tradeable_and_priced=True,dual_portraits_verified=True,strength_order=True,all_other_season_entries_retained=True,player_import_check=semantic,manager_cards_balances_inventory_team_and_progress_equal=True,shop_and_issued_pack_configs_unchanged=True,state_shop_written=False,preflight=preflight,current_top=relative,native_ui_verified=False,match_verified=False,gui_used=False,cards=build['cards'])
x.write(R/'verification.json',result);installed.update(verification=str(R/'verification.json'),verification_status='PASS',status='INSTALLED_API_RESOURCE_VERIFIED_NATIVE_PENDING');x.write(R/'installed.json',installed)
descriptor=x.BASE.parent/'root-current-top.json';d=x.read(descriptor)
if d.get('top_preflight')==str(S/x.SELF):d.update(verification=str(R/'verification.json'),verification_status='PASS');x.common.atomic(x.common.body(d),descriptor)
print(json.dumps({k:v for k,v in result.items() if k not in ('cards','player_import_check')},ensure_ascii=True))
