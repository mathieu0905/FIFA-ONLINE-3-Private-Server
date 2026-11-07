from pathlib import Path
exec(compile(Path('D:/fifaol3/market-background/test_background.py').read_text('utf-8-sig').split('e=m.Market(h);checks=[]')[0],__file__,'exec'),globals())
h.card_ovr=lambda s:(70,84,89,94)[s%4]
h.card_ovrs=lambda cards:{s:h.card_ovr(s) for s in cards}
h.LINES={'GK':range(0,1),'DF':range(1,10),'MF':range(10,21),'FW':range(21,28)}
h._json=lambda rows:(200,json.dumps(rows).encode())
def db():
 c=sqlite3.connect(':memory:');c.execute('create table players(spid integer,preferredposition1 integer)');c.executemany('insert into players values(?,?)',[(x,x%28) for x in range(1,101)]);return c
h._db=db;e=m.Market(h);e.tick();checks=[]
def top(pos=None):return json.loads(e.top(pos,'',b'')[1])
a=top();assert len(a)==50 and len([r for r in a if r['grade']>=11])<=16
assert {r['grade'] for r in a if r['grade']>=11}==set(range(11,21))
regular=[r for r in a if r['grade']<=10]
assert all(7<=r['grade']<=10 for r in regular)
print('BANDS',{q:sum(e.quality(r['spid'])==q for r in regular) for q in ('low','mid','high','elite')});assert all(sum(e.quality(r['spid'])==q for r in regular)>=4 for q in ('low','mid','high','elite'))
assert top()==a
checks.append('50 recommendations; every rare grade represented; all four ability bands; stable within five minutes')
row=regular[0];before=copy.deepcopy(state);clock[0]+=301;b=top()
assert sum(r not in a for r in b)>=15,(len(a),len(b))
assert len({r['spid'] for r in b if r['grade']<=10}^{r['spid'] for r in regular})>=10
checks.append('Five-minute boundary substantially changes player selection within the same 15-minute inventory epoch')
# A displayed item and its direct SPID book are the same finite source.
st=copy.deepcopy(state);target=next(r for r in e.book(st,row['spid'],clock[0])['rows'] if r['grade']==row['grade']);target['count']=0;save(st);e.tick()
assert next(r for r in state['market_simulation']['books'][str(row['spid'])]['rows'] if r['grade']==row['grade'])['count']==0
checks.append('Recommendation rotation and background ticks do not replenish consumed stock')
for pos in h.LINES:
 rows=top(pos);assert rows and all(r['spid']%28 in h.LINES[pos] for r in rows)
checks.append('All four native position filters constrain every returned row')
Path('D:/fifaol3/market-discovery/test-result.json').write_text(json.dumps(dict(passed=True,checks=checks,before=a,after=b),indent=2),'utf8')
print('\n'.join('PASS '+s for s in checks))

