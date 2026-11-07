from pathlib import Path
import hashlib,json,os,re,shutil,sqlite3,struct,sys,tempfile,types
sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parent;B=R/'install-build-v3';S=Path('D:/FO3ID/server')
T=Path(tempfile.mkdtemp(prefix='regression-',dir=R));(T/'gamedata').mkdir()
for p in S.glob('*.json'):shutil.copyfile(p,T/p.name)
for p in (S/'gamedata').glob('*.json'):shutil.copyfile(p,T/'gamedata'/p.name)
for n in ('custom_rosters.json',):shutil.copyfile(B/n,T/'gamedata'/n)
shutil.copyfile(B/'server_display_zh.json',T/'server_display_zh.json')
shutil.copyfile(R/'frozen-pools.json',T/'gamedata/wonderkid_legacy_pools.json')
shutil.copytree(S/'responses',T/'responses');shutil.copyfile(B/'static_roster.json',T/'responses/static_roster.json');shutil.copyfile(B/'fifadb.sqlite',T/'gamedata/fifadb.sqlite')
with sqlite3.connect((S/'gamedata/npc-market-prices.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(T/'gamedata/npc-market-prices.sqlite') as dest:src.backup(dest)
seeds=json.loads((R/'price-seeds.json').read_text('utf-8'))
with sqlite3.connect(T/'gamedata/npc-market-prices.sqlite') as db:
    for spid,price in seeds['rows']:
        db.execute('insert into seeds values(?,?,?,?)',(spid,price,seeds['model_sha256'],0))
        db.execute('insert into prices values(?,?,?,?,null)',(spid,float(price),price,0))
def audit(event,args):
    if event=='open':
        path,mode,flags=args
        if isinstance(path,(str,bytes,os.PathLike)) and ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))):
            if not Path(os.fsdecode(path)).resolve().is_relative_to(R):raise PermissionError('Non-temporary write rejected')
sys.addaudithook(audit)
sys.path[:0]=[str(B),str(S),str(R)];sys.argv=['http_config.py'];os.environ.update(FO3_GAME='D:/FO3ID/32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',FO3_ADMIN_PORT='0')
h=types.ModuleType('http_config');h.__file__=str(T/'http_config.py');sys.modules['http_config']=h
source=(B/'http_config.py').read_text('utf-8').replace('import gen_teams','import gen_teams\ngen_teams.DB='+repr(str(T/'gamedata/fifadb.sqlite')),1)
exec(compile(source,h.__file__,'exec'),h.__dict__)
checks=[]
def check(name,ok):assert ok,name;checks.append(name);print(name,flush=True)
cards=json.loads((B/'cards.json').read_text('utf-8'));spids={c['fo3_spid'] for c in cards};frozen=json.loads((R/'frozen-pools.json').read_text('utf-8'))
check('40 new cards are market eligible',len(spids)==40 and spids<=set(h.market_spids()) and all(h.market_engine.valid_card(s) for s in spids))
check('Native level1 grade1 ratings90..94',all(h.card_ovr(c['fo3_spid'])+h.GRADE_BOOST[1]==c['native_plus1_ovr'] for c in cards))
check('All263 legacy packs retain exact weighted pool and grades',all(h.pack_pool(int(i))==[tuple(r) for r in rows] and h.pack_grades(int(i))==[tuple(r) for r in frozen['grades'][i]] for i,rows in frozen['pools'].items()))
check('Old packs exclude the new season',all(not any(s//1000000==18 for s,w in h.pack_pool(int(i))) for i in frozen['pools']))
check('Season selector contains one new18 entry',sum(18 in row.get('value',[]) for row in json.loads(h.from_file('/static/roster')[1])['seasons'])==1)
check('Every new card has one-time seeded positive market price',all(h.market_engine.exchange.base_value(s)>0 for s in spids))
check('Runtime loads no valuation model',not any(n in sys.modules for n in ('npc_attribute_value','expanded_value_model')))
before={n:hashlib.sha256((T/'gamedata'/n).read_bytes()).hexdigest() for n in ('state.json','shop.json')}
st=h._state();team=st['teams'][str(h._default_slot(st))];size=len(team['players'])
for s in spids:
    book=h.market_engine.book(st,s,h.time.time());assert all(any(r['grade']==g and r['count']>0 and r['price']>0 for r in book['rows']) for g in (1,2,3))
check('All40 have purchasable positive-price +1..3 NPC stock in temporary state',True)
for s in spids:h.add_player(team,s,1)
check('All40 card instances can be created in temporary state',len(team['players'])==size+40)
check('Read-only checks never wrote real or temporary saved assets',all(hashlib.sha256((T/'gamedata'/n).read_bytes()).hexdigest()==v for n,v in before.items()))
# Replay actual bytecode with the established bounded interpreter.
base=Path('D:/fifaol3/season12-display/replay_callback.py').read_text('utf-8');start=base.index('init=dis(');end=base.index('\nrows=[]')
import build_install as b
env={'dis':b.dis,'R':__import__('avm_patch').R,'re':re,'OLD':b.ABC((B/'module-before.abc').read_bytes())}
interpreter=base[start:end].replace('        elif op==0x29:stack.pop()', '        elif op==0x76:stack.append(bool(stack.pop()))\n        elif op==0x2a:stack.append(stack[-1])\n        elif op==0x96:stack.append(not stack.pop())\n        elif op==0x29:stack.pop()')
interpreter=interpreter.replace("else season};", "else season,2:''};").replace('        elif op==0x27:stack.append(False)', '        elif op==0x26:stack.append(True)\n        elif op==0xab:\n            y=stack.pop();x=stack.pop();stack.append(x==y)\n        elif op==0x27:stack.append(False)')
exec(interpreter,env);env['CONSTANTS']['CURRENT_SEASON']=15;env['LABELS']['FO3_CUSTOM_SEASON_18']='神童';old=env['OLD'];new=b.ABC((B/'module-after.abc').read_bytes());run=env['run']
for season in range(128):
    a,_=run(old,12,season);v,depth=run(new,12,season)
    assert v==('神童 测试球员' if season==18 else a),(season,a,v)
    assert depth<=old.A['body_records'][12]['fields'][0]
    a,_=run(old,14,season);v,depth=run(new,14,season)
    assert v==('神童' if season==18 else a)
    assert depth<=old.A['body_records'][14]['fields'][0]
check('256 actual AVM2 name/season paths preserve every old season',True)
big,*_=b.codec.load_codecs(S)
for lang in b.LANGS:
    raw=bytes(b.codec.load_codecs(S)[1].decrypt(big.read(B/'data_0.big',f'data/db2/{lang}.db.db2')))
    with sqlite3.connect(':memory:') as db:
        db.deserialize(b'SQLite format 3\0'+raw[16:]);assert db.execute('select teamname from team where teamid=999918').fetchone()[0]==('神童' if lang=='chi' else 'Wonderkids')
    for prefix in ('games/fo3id','cdn'):
        p=B/'languages'/prefix/f'language_{lang}.big'
        if p.exists():
            member=next(n for n,*_ in big.entries(p) if 'LANGUAGESTRING' in n);assert json.loads(big.read(p,member))['FO3_CUSTOM_SEASON_18']==('神童' if lang=='chi' else 'Wonderkids')
check('Six native locale affiliations and all cached season names match',True)
for filename in ('http_config.py','wonderkid_runtime.py'):compile((B/filename).read_text('utf-8'),filename,'exec')
report=dict(status='PASS',checks=checks,private_service_started=False,production_written=False,native_verified=False,temporary_data=str(T))
(R/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(dict(status='PASS',checks=len(checks))))
