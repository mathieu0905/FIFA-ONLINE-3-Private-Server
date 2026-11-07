"""Verify exact +3 base ratings, unchanged historical cards and protected live assets."""
import json,sqlite3,ssl,urllib.request
import restore_main_season as x
S,C,R=x.S,x.C,x.R;i=x.read(R/'installed.json');out=x.Path(i['build']);build=x.read(out/'build.json')
def get(path,admin=True):
 with urllib.request.urlopen(('http://127.0.0.1:8088' if admin else 'https://127.0.0.1')+path,context=ssl._create_unverified_context(),timeout=30) as response:assert response.status==200;return json.load(response)
for name,path in [('fifadb.sqlite',S/'gamedata/fifadb.sqlite'),('data_0.big',C/'data/data_0.big'),('custom_rosters.json',S/'gamedata/custom_rosters.json'),('static_roster.json',S/'responses/static_roster.json')]:assert x.sha(path)==build['outputs'][name]
for r in build['ratings']:
 detail=get('/api/database_detail?spid='+str(r['spid']));assert detail['ovr']==r['after_base']==r['before_base']+3 and detail['row']['overallrating']==r['overallrating']
assert next(r for r in build['ratings'] if r['spid']==48194957)['after_base']==85
roster=get('/static/roster',False);assert roster==x.read(out/'static_roster.json')
proof=x.common.load(S/'tools/player_import/check.py','restored_formal_semantics').validate(S,C);assert proof['status']=='PLAYER_IMPORT_CERTIFICATE_PASS'
before=x.read(R/'fresh-stop-snapshot'/i['revision']/'state.json');after=x.read(S/'gamedata/state.json');assert {k:v for k,v in before.items() if k!='market_simulation'}=={k:v for k,v in after.items() if k!='market_simulation'},'Concurrent progress; do not restore old state'
for path,digest in i['protected'].items():
 if not path.endswith('state.json'):assert x.sha(path)==digest,path
transaction=x.read(x.Path(i['backup'])/'transaction.json');old_db=x.Path(i['backup'])/str(next(n for n,row in enumerate(transaction['files']) if row['relative']=='gamedata/fifadb.sqlite'))
with sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;db.execute('attach database ? as old',(str(old_db),));assert not db.execute('select * from old.players where spid/1000000<>48 except select * from players where spid/1000000<>48').fetchone();assert not db.execute('select * from players where spid/1000000<>48 except select * from old.players where spid/1000000<>48').fetchone()
 assert db.execute('select count(*) from players where spid/1000000 in (49,55)').fetchone()[0]==12
 assert tuple(db.execute('select count(*),min(overallrating),max(overallrating) from players where spid/1000000=48').fetchone())==(67,85,89)
_,_,top,parent=x.tx.top();preflight=parent.preflight(S,C)
result=dict(status='PASS',main_season=48,changed_cards=67,each_primary_base_ovr_exact_plus3=True,base_rating_range=[85,89],phil_jones_base_before=82,phil_jones_base_after=85,previous_attribute_change_exactly_reversed=True,historical_49_55_cards_unchanged=12,all_other_players_unchanged=True,player_import_status=proof['status'],real_manager_cards_experience_grades_balances_inventory_team_progress_unchanged=True,pack_configs_unchanged=True,state_shop_written=False,preflight=preflight,actual_top=top,services_ready=x.common.listening()==[443,8088,28002],native_ui_verified=False,match_verified=False)
x.write(R/'verification.json',result);i.update(status='INSTALLED_MAIN67_RESTORED_API_RESOURCE_VERIFIED_NATIVE_PENDING',verification=str(R/'verification.json'),verification_status='PASS',services_restored=result['services_ready']);x.write(R/'installed.json',i)
dpath=x.BASE.parent/'root-current-top.json';d=x.read(dpath)
if d.get('top_preflight')==str(S/x.SELF):
 d.update(status=i['status'],verification=str(R/'verification.json'),verification_status='PASS',services_restored=result['services_ready']);x.common.atomic(x.common.body(d),dpath)
registry=x.read(S/'gamedata/custom_rosters.json');names={c['fo3_spid']:c['name_zh'] for c in registry['cards']};lines=['曼联传奇主赛季：67人，已加回上一版下调的3点。','当前主位置基础能力85～89；菲尔·琼斯基础85。','此表不额外计算强化/等级/队套加成；49/55历史卡保持原值。','']+[str(r['after_base'])+'  '+names[r['spid']]+'  SPID '+str(r['spid']) for r in sorted(build['ratings'],key=lambda r:(-r['after_base'],r['spid']))]
for p in (R/'曼联传奇名单.txt',x.BASE/'service-expansion/曼联传奇名单.txt'):p.write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=True))
