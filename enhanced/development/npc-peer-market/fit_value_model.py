"""Fit a research value model to read-only FO3 historical prices, not live money."""
from pathlib import Path
import json,math,statistics,collections,hashlib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error
R=Path(__file__).resolve().parent
rows=json.loads((R/'historical-data.json').read_text('utf8'));schema=json.loads((R/'schema.json').read_text('utf8'))
# Current MUL48 has been rewritten by the custom roster; do not use those altered
# attributes to explain a historical card's price.
rows=[r for r in rows if r['season'] not in (12,13,48,84)]
stats=sorted({k for w in schema['role_weights'].values() for k in w})
raw=['ovr','height','weight','weakfootabilitytypecode','skillmoves','internationalrep','attackingworkrate','defensiveworkrate']
seasons=sorted({r['season'] for r in rows});bodies=sorted({r['bodytypecode'] for r in rows})
features=raw+['stat:'+s for s in stats]+['season:'+str(s) for s in seasons]+['pos:'+str(p) for p in range(28)]+['body:'+str(b) for b in bodies]+[f'trait{w}:{b}' for w in (1,2) for b in range(32)]
def feature(r,f):
 if f.startswith('stat:'):return r[f[5:]]-r['ovr']
 if ':' not in f:return r.get(f,0)
 typ,value=f.split(':');v=int(value)
 if typ=='season':return int(r['season']==v)
 if typ=='pos':return int(r['preferredposition1']==v)
 if typ=='body':return int(r['bodytypecode']==v)
 return (int(r.get(typ,0))&0xffffffff)>>v&1
X=np.array([[feature(r,f) for f in features] for r in rows],dtype=np.float64);y=np.log([r['price'] for r in rows]);groups=np.array([r['playerid'] for r in rows])
train,test=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=2026).split(X,y,groups))
assert not set(groups[train])&set(groups[test])
def metric(pred):
 errors=np.abs(pred-y[test]);return dict(log_mae=float(np.mean(errors)),median_error_factor=float(np.exp(np.median(errors))),within_2x=float(np.mean(errors<=math.log(2))),within_3x=float(np.mean(errors<=math.log(3))),p90_error_factor=float(np.exp(np.quantile(errors,.9))))
by=collections.defaultdict(list)
for i in train:by[rows[i]['ovr']].append(y[i])
base={o:float(np.median(v)) for o,v in by.items()};baseline=np.array([base[min(base,key=lambda o:abs(o-rows[i]['ovr']))] for i in test])
results={'ovr_only':metric(baseline)}
basecols=[i for i,f in enumerate(features) if f=='ovr' or f.startswith(('season:','pos:'))]
params=dict(loss='absolute_error',learning_rate=.08,max_iter=240,max_leaf_nodes=23,min_samples_leaf=20,l2_regularization=5,random_state=2026)
a=HistGradientBoostingRegressor(**params).fit(X[train][:,basecols],y[train]);results['ovr_season_position']=metric(a.predict(X[test][:,basecols]));print('BASELINES',results,flush=True)
m=HistGradientBoostingRegressor(**params).fit(X[train],y[train]);pred=m.predict(X[test]);results['full_attributes']=metric(pred);print('FULL',results['full_attributes'],flush=True)
# Group permutation is descriptive predictive association, not causal hand-feel evidence.
rng=np.random.default_rng(2026);subset=rng.choice(test,min(1800,len(test)),replace=False);original=mean_absolute_error(y[subset],m.predict(X[subset]));importance={}
sets={'ability':[features.index('ovr')],'season':[i for i,f in enumerate(features) if f.startswith('season:')],'position':[i for i,f in enumerate(features) if f.startswith('pos:')],'attribute_combinations':[i for i,f in enumerate(features) if f.startswith('stat:')],'physical_model':[i for i,f in enumerate(features) if f.startswith('body:') or f in ('height','weight')],'weakfoot_skillmoves':[features.index(f) for f in ('weakfootabilitytypecode','skillmoves')],'traits_opaque_bits':[i for i,f in enumerate(features) if f.startswith(('trait1:','trait2:'))],'reputation_workrate':[features.index(f) for f in ('internationalrep','attackingworkrate','defensiveworkrate')]}
for key,cols in sets.items():
 z=X[subset].copy();z[:,cols]=X[rng.permutation(subset)][:,cols];importance[key]=float(mean_absolute_error(y[subset],m.predict(z))-original)
# Refit to all reference cards for prototype use. Export numeric trees so production
# can later evaluate them without installing sklearn into the running server.
m.fit(X,y);trees=[]
for group in m._predictors:
 n=group[0].nodes
 assert not any(n['is_categorical'])
 trees.append([[int(r['feature_idx']),float(r['num_threshold']),int(r['left']),int(r['right']),float(r['value']),int(r['is_leaf'])] for r in n])
export=dict(schema=1,scope='research_prototype_only',price_unit='historical Indonesia-normalized EP at +1',features=features,role_weights=schema['role_weights'],position_roles=schema['position_roles'],baseline=float(m._baseline_prediction[0,0]),trees=trees,seasons=seasons,source_prices_sha256=hashlib.sha256(Path('D:/FO3ID/server/gamedata/fa_prices.json').read_bytes()).hexdigest())
(R/'value-model.json').write_text(json.dumps(export,ensure_ascii=False),'utf8')
# Evidence/examples: observed prices, with unambiguous season and source SPID.
seasonlabels=schema['season_labels']
def summary(r):return dict(spid=r['spid'],name=r['name'],season=seasonlabels.get(str(r['season']),str(r['season'])),ovr=r['ovr'],historical_price=r['price'])
top=[summary(r) for r in sorted(rows,key=lambda r:-r['price'])[:20]]
examples=[summary(r) for r in rows if r['season']==88 and r['playerid'] in (192505,202126,183277,188545,192985,158023,20801)]
pairs=[];grouped=collections.defaultdict(list)
for r in rows:grouped[(r['season'],r['ovr'],r['preferredposition1'])].append(r)
for key,g in grouped.items():
 if len(g)<10 or key[1]<76:continue
 lo,hi=min(g,key=lambda r:r['price']),max(g,key=lambda r:r['price'])
 pairs.append(dict(season=seasonlabels.get(str(key[0]),str(key[0])),ovr=key[1],position=key[2],ratio=hi['price']/lo['price'],expensive=summary(hi),cheap=summary(lo),n=len(g)))
report=dict(raw_entries=38077,positive_price_rows=16041,training_rows=len(rows),excluded_current_custom_seasons=[12,13,48,84],training_players=len(set(groups[train])),test_players=len(set(groups[test])),test_rows=len(test),split='Group holdout by playerid; no same player in train and test',validation=results,group_permutation_log_mae_increase=importance,top_cards=top,ordinary_2017_examples=examples,same_season_rating_position_examples=sorted(pairs,key=lambda p:-p['ratio'])[:10],limitations=['Source is historical regional prices, not current Chinese-server transactions.','Historical price includes scarcity, popularity and supply, not causal proof of physical-model or traits effects.','Current attributes and historical price are matched by SPID; same-date feature snapshots are unavailable.','Body/trait codes are learned categories/bits, not verified human-readable trait meanings.','Exact-reference cards should retain historical relative premiums; model is fallback for missing cards.','New custom seasons and new rating ranges are out of distribution and need explicit calibration.','Only +1 is fitted; no historical +20 prices are invented.','No live server files, wallet, cards, packs, state or pricing changed.'])
(R/'value-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print('IMPORTANCE',importance,flush=True);print('REPORT',R/'value-analysis.json',flush=True)
