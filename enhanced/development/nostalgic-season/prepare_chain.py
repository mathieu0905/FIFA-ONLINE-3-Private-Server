"""Frozen season19 chain design for the shared shop owner; no formal mutation."""
from pathlib import Path
import hashlib,json,math
R=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
registry=json.loads((S/'gamedata/custom_rosters.json').read_text('utf-8'))
pool=sorted(next(s['cards'] for s in registry['seasons'] if s['id']==19))
moments=sorted(next(s['cards'] for s in registry['seasons'] if s['id']==84))
assert len(pool)==88 and all(s//1000000==19 for s in pool)
assert moments and all(s//1000000==84 for s in moments)
weights={8:40,9:27,10:20,11:10,12:3};quantities=[5,8,10,12,15]
assert sum(weights.values())==100 and sum(quantities)==50
stages=[dict(stage=i+1,nostalgia_random=q,guaranteed_nostalgia11=int(i==4),guaranteed_moments1=int(i==4)) for i,q in enumerate(quantities)]
spec=dict(schema=1,status='DESIGN_NOT_INSTALLED',name='怀旧神兽连锁',rounds=10,season=19,pool=pool,random_cards_per_round=50,random_grade_weights=weights,stages=stages,
          bonus_cards_per_round=[dict(season=19,grade=11,count=1,pool=pool),dict(season=84,grade=1,count=1,pool=moments)],
          expected_per_round={11:6.0,12:1.5},guaranteed_per_round={11:1,'moments_plus1':1},max_moments_total=10,other_seasons_allowed=[84],
          probability_plus12_zero_per_round=.97**50,plus12_is_guaranteed=False,guarantee_semantics='The final stage grants a separate fixed+11 card; all 50 regular draws independently use the disclosed five-grade distribution.',
          pending=['Shared shop owner assigns globally unique new SKUs and prices, seals current code/probability config and runs transactional issuance tests.','Do not overwrite old sold probability pools or inventory rights.','New chain is separate from installed season data and has not been published.'])
assert len(stages)==5 and sum(s['nostalgia_random'] for s in stages)==50
assert 50*weights[11]/100+1==6 and 50*weights[12]/100==1.5
path=R/'chain-design.json';path.write_text(json.dumps(spec,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(dict(status=spec['status'],rounds=10,random_cards_per_round=50,expected_per_round=spec['expected_per_round'],guaranteed_per_round=spec['guaranteed_per_round'],design_sha256=hashlib.sha256(path.read_bytes()).hexdigest()),ensure_ascii=False))
