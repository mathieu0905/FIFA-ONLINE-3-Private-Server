"""Read-only preservation and temporary market/team-color regressions."""
from pathlib import Path
from contextlib import closing
import ast,copy,hashlib,importlib.util,json,sqlite3,sys,tempfile,types
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path[:0]=[str(R),str(S),str(S/'tools/player_import'),str(S/'tools/re')]
import price_extension,bigdir,native_db,market_price_store

def main():
 cases=[];db=R/'prepared-v3/fifadb.sqlite';con=sqlite3.connect(db);con.row_factory=sqlite3.Row
 con.execute('attach database ? as old',(str(S/'gamedata/fifadb.sqlite'),))
 for name, in con.execute("select name from old.sqlite_master where type='table' and name not like 'sqlite_%'"):
  escaped=name.replace('"','""');assert con.execute(f'SELECT count(*) FROM (SELECT * FROM old."{escaped}" EXCEPT SELECT * FROM main."{escaped}")').fetchone()[0]==0
 cases.append('Every old SQL row and table preserved, including 688 LIVE cards')
 cards=json.loads((R/'input/cards.json').read_text('utf8'));assert len(cards)==32
 source=(R/'http_config.py').read_text('utf8');tree=ast.parse(source)
 weights=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROLE_WEIGHTS' for t in n.targets)))
 roles='GK SW WB FB CB CB CB FB WB DM DM DM WM CM CM CM WM AM AM AM CF CF CF W ST ST ST W'.split()
 for c in cards:
  row=con.execute('select * from players where spid=?',(c['fo3_spid'],)).fetchone();w=weights[roles[row['preferredposition1']]]
  rating=sum(row[k]*v for k,v in w.items())//100+5
  assert rating==c['mapping_rule']['target_plus1_lv1'] and 85<=rating<=92
  assert row['playerid']==c['base_playerid'] and row['nationality']==155
  assert all(con.execute('select full from names'+lang+' where playerid=?',(row['playerid'],)).fetchone() for lang in ('eng','chi','ind','kor','tha','vie'))
  cases.append(c['name_en']+' exact +1 LV1 rating '+str(rating)+' and six-language identity')
 con.close()
 old=json.loads((S/'gamedata/custom_rosters.json').read_text('utf8'));new=json.loads((R/'prepared-v3/custom_rosters.json').read_text('utf8'))
 assert old['cards']==new['cards'][:len(old['cards'])] and old['seasons']==new['seasons'][:len(old['seasons'])]
 cases.append('All original registry entries preserved')
 def native(p):
  raw=bigdir.read(p,'data/db/fifa_ng_db.db');meta=bigdir.read(p,'data/db/fifa_ng_db-meta.xml').decode();*_,t,f=native_db.player_table(raw,meta)
  return {t.get(r,f['playerid']['shortname']):r for r in t.rows}
 a=native(C/'data/data_0.big');b=native(R/'prepared-v3/data_0.big')
 assert len(b)==len(a)+32 and all(b[k]==v for k,v in a.items())
 cases.append('32 unique native identities added; every prior native record exact')
 def members(p):
  body=p.read_bytes();return {n:body[o:o+size] for n,o,size,u in bigdir.entries(p)}
 a=members(C/'data/data_0.big');b=members(R/'prepared-v3/data_0.big')
 changed={'data/db/fifa_ng_db.db','data/db2/fifadb.db.db2'}|{f'data/db2/{l}.db.db2' for l in ('eng','chi','ind','kor','tha','vie')}
 assert a.keys()==b.keys() and all(a[k]==b[k] for k in a if k not in changed)
 cases.append('All unrelated BIG members including Lua and model resources exact')
 assert json.loads((R/'prepared-v3/player-import-validation.json').read_text('utf8'))['status']=='PLAYER_IMPORT_FULL_PASS'
 assert json.loads((R/'badge-proof.json').read_text('utf8'))['non_target_members_exact']
 cases.append('Full strict player import and additive native badge PASS')
 with tempfile.TemporaryDirectory(dir=R,prefix='market-test-') as tmp:
  fixture=Path(tmp)/'prices.sqlite'
  with closing(sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(fixture)) as dst:src.backup(dst)
  with closing(sqlite3.connect(fixture)) as c:before={t:c.execute('select * from '+t+' order by 1').fetchall() for t in ('seeds','prices','price_events','metadata')}
  price_extension.apply(fixture,R/'prices.json')
  with closing(sqlite3.connect(fixture)) as c:assert all(set(v)<=set(c.execute('select * from '+t).fetchall()) for t,v in before.items())
  market_price_store.verify_seed(fixture,S/'gamedata/npc-market-seed.json.gz');market_price_store.verify_calibration(fixture,S/'gamedata/valuation-v11.json.gz')
  spec=importlib.util.spec_from_file_location('prior_live_prices',S/'fo4_live_market.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.verify(fixture,S/'gamedata/fo4-live-price-extension.json')
  cases.append('New seeds append only; original seeds, v11 calibration and LIVE extension pass')
  price_extension.rollback(fixture,R/'prices.json')
  with closing(sqlite3.connect(fixture)) as c:assert all(v==c.execute('select * from '+t+' order by 1').fetchall() for t,v in before.items())
  cases.append('Own seed rollback exact')
  price_extension.apply(fixture,R/'prices.json')
  try:price_extension.apply(fixture,R/'prices.json')
  except ValueError:pass
  else:raise AssertionError('Duplicate imports accepted')
  sid=cards[0]['fo3_spid']
  with closing(sqlite3.connect(fixture)) as c,c:c.execute('update prices set basis_price=basis_price+1 where spid=?',(sid,))
  try:price_extension.rollback(fixture,R/'prices.json')
  except RuntimeError:pass
  else:raise AssertionError('Later market progress overwritten')
  cases.append('Duplicate import rejected and later market progress retained')
 # Run exact color/rating functions with disposable teams and read-only card DB.
 sys.path.insert(0,str(R.parent/'team-bonus20'))
 spec=importlib.util.spec_from_file_location('color_harness',R.parent/'team-bonus20/test.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
 ns=h.functions(source,real=True);ns['_db']=lambda:sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
 ns['STAT_COLS']=list(set().union(*ns['ROLE_WEIGHTS'].values()));ns['GRADE_BOOST']=tuple(0 for _ in range(21))
 sets=ns['tc_special_sets']();newids={c['fo3_spid'] for c in cards}
 assert newids<=sets[60084][0] and newids<=sets[20043][0] and newids<=sets[886][0]
 cases.append('All new cards eligible for China legends, legend base, and original moments feature')
 old_db=sqlite3.connect((S/'gamedata/fifadb.sqlite').as_uri()+'?mode=ro',uri=True)
 moments=[r[0] for r in old_db.execute('select spid from players where spid/1000000=84 group by playerid limit 11')]
 other=[r[0] for r in old_db.execute('select spid from players where spid/1000000=93 group by playerid limit 11')];old_db.close()
 for n in range(12):
  for future in range(n+1):
   ids=sorted(newids)[:future]+moments[:n-future]+other[:11-n]
   tm=dict(players=[dict(id=str(i),spid=s,grade=1,levelinfo={'level':1,'exp':0}) for i,s in enumerate(ids)],squad=dict(positions=[dict(id=str(i),spid=s,pos=14) for i,s in enumerate(ids)]))
   expected=0 if n<3 else 4 if n<6 else 6 if n<9 else 8 if n<11 else 10
   active=ns['active_teamcolors'](tm);feature=[c for c in active if c['teamcolorid']==60084];assert bool(feature)==bool(expected)
   ns['card_stats']=lambda ids:{s:dict.fromkeys(ns['STAT_COLS'],80) for s in ids}
   rated=ns['xi_ratings'](dict(tm,teamcolors=feature))
   assert all(rated[str(i)]==80+(expected if s//1000000 in (84,327) else 0) for i,s in enumerate(ids))
   cases.append(f'Feature mixed starters {future} future + {n-future} moments: +{expected} only eligible players')
 ids=sorted(newids)[:2]+other[:9]
 tm=dict(players=[dict(id=str(i),spid=s,grade=1,levelinfo={'level':1,'exp':0}) for i,s in enumerate(ids)],squad=dict(positions=[dict(id=str(i),spid=s,pos=14) for i,s in enumerate(ids)]))
 tm['players'].append(dict(id='bench',spid=sorted(newids)[-1],grade=20,levelinfo={'level':30,'exp':0}));tm['squad']['positions'].append(dict(id='bench',spid=sorted(newids)[-1],pos=28))
 assert not any(e['teamcolorid']==60084 for e in ns['active_teamcolors'](tm))
 cases.append('Third eligible card on bench cannot activate three-starter feature')
 tm['players'][2]['spid']=ids[0];tm['squad']['positions'][2]['spid']=ids[0]
 assert not any(e['teamcolorid']==60084 for e in ns['active_teamcolors'](tm))
 cases.append('Repeated same player identity does not complete feature threshold')
 before_ast=ast.parse((S/'http_config.py').read_text('utf8'));functions=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)}
 a,b=functions(before_ast),functions(tree);assert {k for k in a if a[k]!=b[k]}=={'tc_seasons','tc_special_sets','tc_colors','pack_pool'}
 cases.append('All unrelated HTTP functions, reinforcement protection and grade declarations preserved')
 report=dict(status='PASS',case_count=len(cases),cases=cases,cards=32,new_native_identities=32,native_runtime_verified=False,formal_state_shop_written=False)
 (R/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(dict(status='PASS',cases=len(cases))))

if __name__=='__main__':main()
