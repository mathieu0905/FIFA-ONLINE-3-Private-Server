from pathlib import Path
fixture=Path(__file__).with_name('fixture.py').read_text('utf8')
exec(compile(fixture.split('\ntry:\n')[0],__file__,'exec'),globals())
try:
 reset();top=request('/transfer/top/50');st=state()
 assert len(top)==50 and sum(r['grade']>=7 for r in top)>=20
 assert set(range(11,21)) <= {r['grade'] for r in top}
 assert len({r['spid'] for r in top})>=35
 assert request('/transfer/top/50')==top
 passed('Top50 exposes diverse players and every +11..20 tier immediately; refresh cannot reroll')
 row=next(r for r in top if 7<=r['grade']<=10)
 sid=row['spid'];g=row['grade'];price=row['price']
 assert row in request(f'/transfer/search/{sid}')
 before_ep=ep(state());assert request(f'/transfer/purchase/{sid}/{g}/{price}/purchase',{})['result']
 assert ep(state())==before_ep-price
 assert not any(r['grade']==g for r in request(f'/transfer/search/{sid}'))
 before=raw();assert not request(f'/transfer/purchase/{sid}/{g}/{price}/purchase',{})['result'] and raw()==before
 passed('Featured regular high-grade stock is shared, debited once, and cannot refill by repeat requests')
 row=next(r for r in top if r['grade']==20);sid=row['spid'];g=20;price=row['price']
 assert row in request(f'/transfer/search/{sid}')
 assert request(f'/transfer/purchase/{sid}/{g}/{price}/purchase',{})['result']
 assert not any(r['grade']==g for r in request(f'/transfer/search/{sid}'))
 passed('Apex discovery, search, and purchase consume the same finite offer')
 pools=engine.quality_pools()
 for grades,_,_,_ in mod.LOW_SUPPLY:
  entries=[r for r in engine.supply_plan() if r['grades']==grades]
  rates=[r['slots']*r['chance']/(r['period']/86400)/len(pools[r['quality']]) for r in entries]
  assert all(abs(rates[i]/rates[0]-f)<1e-12 for i,f in enumerate((1,.9,.8,.7)))
 passed('Every rare grade retains exact per-player quality ratios 1/.9/.8/.7')
 local=copy.deepcopy(state());w=local['market_simulation'];w['supply_version']=2
 old={'spid':sid,'grade':20,'price':12345,'count':1,'expandme':'player','_market_release':clock[0]-1,'_market_expires':clock[0]+3600}
 w['rare_books']={'old':{'rows':[old]}};engine.prepare(local)
 assert old in w['legacy_supply'] and w['supply_version']==3
 before=copy.deepcopy(w);engine.prepare(local);assert w==before
 passed('Upgrade preserves quoted contracts and is idempotent')
 for pos in ('FW','MF','DF','GK'):
  response=request('/transfer/top/50/position/'+pos)
  assert response and len(response)<=50
  with h.closing(h._db()) as db:
   assert all(db.execute('SELECT preferredposition1 FROM players WHERE spid=?',(r['spid'],)).fetchone()[0] in h.LINES[pos] for r in response)
 passed('Position endpoint requests complete')
finally:
 srv.shutdown();(RUN/'result.json').write_text(json.dumps({'checks':checks,'blocked':blocked,'top':top},ensure_ascii=False,indent=2),'utf8')
 print('RESULT',RUN,flush=True)
