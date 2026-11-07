"""Fit a few bounded, explainable curve parameters, not an unconstrained NN."""
from pathlib import Path
import collections,copy,gzip,json,math,statistics
from fair_value_model import effective_score,segments,economic_curve,strict_floor,canonical

P=Path(__file__).resolve().parent;B=Path('D:/fifaol3/npc-peer-market/anchor-retraining-v10')
def save(name,value):(P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
def prepare_data():
 with gzip.open(B/'training-data.json.gz','rt',encoding='utf8') as f:return [r for r in json.load(f) if r['kind']=='real']
def priors(data,config,regularization=6):
 residuals=collections.defaultdict(list)
 for r in data:
  target=max(1.,r['price']/1000)
  residuals[r['playerid']].append(math.log(target)-math.log(economic_curve(effective_score(r['attributes']|{'playerid':r['playerid']},config),config)))
 result={}
 for pid,values in residuals.items():
  shift=statistics.median(values)*len(values)/(len(values)+regularization);shift=max(math.log(.85),min(math.log(1.15),shift))
  result[str(pid)]=dict(factor=math.exp(shift),real_quotes=len(values))
 return result
def fit(data,config):
 c=copy.deepcopy(config);c['currency_scale']=1.;features=[];targets=[];baseweights=[];pids=[]
 for r in data:
  raw=r['attributes']|{'playerid':r['playerid']};features.append([1.]+segments(effective_score(raw,c),c))
  targets.append(math.log(max(1.,r['price']/1000)));baseweights.append(12. if r['calibration_anchor'] else 1.);pids.append(str(r['playerid']))
 params=[math.log(100.)]+[.18]*(len(features[0])-1);predictions=[sum(a*b for a,b in zip(x,params)) for x in features]
 names={};adjusted=targets[:]
 for outer in range(3):
  for robust in range(3):
   weights=[w*min(1.,1.25/max(1e-8,abs(y-p))) for w,y,p in zip(baseweights,adjusted,predictions)]
   for iteration in range(25):
    largest=0.
    for j in range(len(params)):
     numerator=sum(w*x[j]*(y-p+params[j]*x[j]) for x,y,p,w in zip(features,adjusted,predictions,weights));denominator=sum(w*x[j]*x[j] for x,w in zip(features,weights))
     if not denominator:continue
     value=numerator/denominator
     value=max(math.log(10),min(math.log(2000),value)) if j==0 else max(.06,min(.28,value))
     delta=value-params[j];largest=max(largest,abs(delta));params[j]=value
     if delta:predictions=[p+delta*x[j] for p,x in zip(predictions,features)]
    if largest<1e-6:break
  c['curve']['intercept']=params[0];c['curve']['slopes']=params[1:];names=priors(data,c)
  adjusted=[y-math.log(names[pid]['factor']) for y,pid in zip(targets,pids)]
 # Currency calibration is a separate global scale. Use trusted UL/WL kings,
 # never the current game's erroneous prices. Selection fits this on train only.
 anchor_ratios=collections.defaultdict(list)
 for r in data:
  if r['calibration_anchor'] and r['spid']//1000000 in (30,93) and r['price']/1000>=3000000:
   raw=r['attributes']|{'playerid':r['playerid']}
   anchor_ratios[r['playerid']].append((r['price']/1000)/economic_curve(effective_score(raw,c),c))
 if not anchor_ratios:raise ValueError('No trusted king currency anchors')
 c['currency_scale']=math.exp(statistics.median(math.log(statistics.median(v)) for v in anchor_ratios.values()))
 c['currency_anchor_identities']=len(anchor_ratios);c['identity_factors']=names
 return c
def metric(data,config):
 errors=[]
 for r in data:
  raw=r['attributes']|{'playerid':r['playerid']};score=effective_score(raw,config);value=economic_curve(score,config)*config.get('identity_factors',{}).get(str(r['playerid']),{}).get('factor',1.)+strict_floor(raw,config)
  errors.append(abs(math.log(max(1,r['price']/1000))-math.log(value)))
 return dict(rows=len(errors),log_mae=statistics.mean(errors),median_error_factor=math.exp(statistics.median(errors)),within_2x=sum(e<=math.log(2) for e in errors)/len(errors))
def main():
 all_data=prepare_data();data=[r for r in all_data if r['price']/1000>=2000];base=json.loads((B/'config.json').read_text('utf8'))
 config=dict(schema=1,revision='fair-value-v12',role_weights=base['role_weights'],grade1_boost=5,market_factor_bounds=[.85,1.15],identity_factor_bounds=[.85,1.15],
             curve=dict(knots=[40,50,60,70,80,90,100],intercept=math.log(100),slopes=[.18]*6,slope_bounds=[.06,.28],high_tail='linear_in_price'),
             minimum_price_sensitivity=dict(ability_point_ep=1,star_ep=25),identity_factors={})
 train=[r for r in data if r['partition']=='train'];val=[r for r in data if r['partition']=='validation'];test=[r for r in data if r['partition']=='test']
 candidates=[]
 for wf,sm in [(1.,.5),(1.,1.),(1.5,.5),(1.5,1.)]:
  c=copy.deepcopy(config);c.update(weakfoot_score_per_star=wf,skill_score_per_star=sm);c=fit(train,c);m=metric(val,c)
  candidates.append((m['log_mae'],c,m));print('CANDIDATE',wf,sm,m,flush=True)
 _,chosen,validation=min(candidates,key=lambda x:x[0]);independent=metric(test,chosen)
 # Freeze held-out results before final historical refit. A fitted historic
 # quote is never presented as a new independent test.
 final=fit(data,chosen)
 save('model.json',final);save('training-report.json',dict(status='PASS',real_rows=len(all_data),curve_fit_rows=len(data),identities=len(final['identity_factors']),historical_floor_filter='Historical quotes below2000EP excluded from curve fitting and independent subset metrics; low-price labels below the strict ability floor cannot define this new economy. Threshold fixed before validation.',selection='whole-player validation only',validation=validation,unseen_identity_test=independent,all_history_floor_inclusive_diagnostic=metric(all_data,final),final_fit='all eligible real history; final refit is not an independent test',candidates=[dict(weakfoot=c['weakfoot_score_per_star'],skill=c['skill_score_per_star'],validation=m) for _,c,m in candidates],constraints=dict(maximum_log_price_slope=.28,minimum_log_price_slope=.06,above100='linear in price',name_factor=[.85,1.15],market_factor=[.85,1.15]),formal_activated=False))
 print('FINAL',json.dumps(dict(selected_stars=[final['weakfoot_score_per_star'],final['skill_score_per_star']],curve=final['curve'],test=independent)),flush=True)

if __name__=='__main__':main()
