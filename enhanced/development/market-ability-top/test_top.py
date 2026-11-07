from pathlib import Path
import copy,json,sqlite3,sys,tempfile,threading,types
from contextlib import closing
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server');sys.path[:0]=[str(P),str(S)]
import market_simulation as mod
from market_simulation import Market
checks=[]
def check(v,s):assert v,s;checks.append(s)
tmpbase=P/'tmp';tmpbase.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=tmpbase,prefix='ability-top-') as temp:
 root=Path(temp).resolve();assert root.is_relative_to(tmpbase.resolve());db=root/'players.sqlite';ratings={i:60+(i%45) for i in range(1,101)};ratings.update({900:72,901:104,902:85})
 positions={i:(0 if i%3==0 else 25) for i in ratings}
 with closing(sqlite3.connect(db)) as c:c.execute('create table players(spid,preferredposition1)');c.executemany('insert into players values(?,?)',positions.items());c.commit()
 boost=(0,5,6,7,8,10,12,14,17,20,24)+tuple(24+2*(g-10) for g in range(11,21))
 st={'market_simulation':{'books':{'x':{'epoch':2,'rows':[dict(spid=i,grade=1+i%20,count=1,price=1000+i) for i in range(1,101)]},'old':{'epoch':1,'rows':[dict(spid=902,grade=20,count=1,price=1)]}}}}
 rare=[dict(spid=900,grade=20,count=1,price=500),dict(spid=900,grade=20,count=2,price=400),dict(spid=901,grade=1,count=1,price=100),dict(spid=902,grade=10,count=1,price=600,levelinfo={'level':30})]
 rare+=[dict(spid=1,grade=20,count=0,price=1),dict(spid=2,grade=20,count=1,price=1,_market_release=1900),dict(spid=3,grade=20,count=1,price=1,_market_expires=1800)]
 m=Market.__new__(Market);m.h=types.SimpleNamespace(LINES={'GK':(0,)},STATE_LOCK=threading.RLock(),MAX_GRADE=20,PLAYER_MAX_LEVEL=30,GRADE_BOOST=boost,player_level_boost=lambda lv:lv-1 if lv<=23 else 22+(lv-22)//2,_state=lambda:st,_json=lambda x:x,closing=closing,_db=lambda:sqlite3.connect(db),card_ovrs=lambda ids:{i:ratings[i] for i in ids},_save=lambda s:None)
 m.has_active=lambda s:True;m.prepare=lambda s:None;m.settle=lambda s,t:None;m.rare_stock=lambda s,t:rare;m.exchange=types.SimpleNamespace(listings=lambda *args:[]);m.candidates=lambda:tuple(ratings)
 def no_refill(*args,**kwargs):raise AssertionError('Recommendation cannot regenerate occupied books')
 m.featured_rows=no_refill;mod.now=lambda:1800;before=copy.deepcopy((st,rare));rows=m.top(None,{},b'');abilities=[m.listing_ability(r,ratings) for r in rows]
 check(len(rows)==50 and abilities==sorted(abilities,reverse=True),'global top fifty is sorted by actual listed ability')
 check(next(i for i,r in enumerate(rows) if r['spid']==900)<next(i for i,r in enumerate(rows) if r['spid']==901),'higher-enhanced lower-base card outranks lower-enhanced high-base card')
 same=[r for r in rows if (r['spid'],r['grade'])==(900,20)];check(len(same)==1 and same[0]['price']==400 and same[0]['count']==2,'identical variants choose cheapest real offer without inventing counts')
 check(m.listing_ability(next(r for r in rows if r['spid']==902),ratings)==85+24+26,'listed level thirty uses the current non-linear level bonus')
 check(not any(r['spid']==902 and r['grade']==20 for r in rows),'expired regular book is not recommended')
 check(not any((r['spid'],r['grade']) in ((1,20),(2,20),(3,20)) for r in rows),'sold-out, unreleased and expired offers excluded')
 check((st,rare)==before,'ranking does not consume, refill or mutate inventory')
 check(m.top(None,{},b'')==rows,'unchanged listings produce stable ranking, not forced seasonal rotation')
 gk=m.top('GK',{},b'');check(all(positions[r['spid']]==0 for r in gk),'position filters still apply')
 # Changing actual stock removes that entry; no persistent recommendation cache.
 for r in rare:
  if r['spid']==900:r['count']=0
 check(not any(r['spid']==900 for r in m.top(None,{},b'')),'stock depletion is reflected immediately')
 # Time advancement does not refill cached books through the ranking path.
 mod.now=lambda:2700;check(all(r['price']<1000 for r in m.top(None,{},b'')),'new epoch removes stale book listings without rerolling inventory')
report=dict(status='PASS',checks=len(checks),details=checks,real_state_written=False)
(P/'regression.json').write_text(json.dumps(report,indent=2),'utf8');print(json.dumps({'status':'PASS','checks':len(checks)}))
