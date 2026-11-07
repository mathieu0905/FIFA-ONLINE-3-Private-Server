from pathlib import Path
import ast,json,hashlib,sqlite3,copy,time
R=Path('D:/fifaol3/npc-peer-market');O=Path('D:/fifaol3/value-diagnosis')
source=(R/'model-serving/build_initial_prices.py').read_text('utf8')
prefix=source[:source.index('start=time.monotonic()')]
# Reuse the exact read-only seed inference implementation without its seed writes.
ns={'__file__':str(R/'model-serving/build_initial_prices.py')};exec(compile(prefix,'seed_inference_readonly','exec'),ns)
model=ns['model'];predict=ns['predict'];rows={r['spid']:r for r in ns['rows']}
price_db=sqlite3.connect('file:D:/FO3ID/server/gamedata/npc-market-prices.sqlite?mode=ro',uri=True)
prices={s:(p,i) for s,p,i in price_db.execute('select p.spid,p.current_price,s.initial_price from prices p join seeds s using(spid)')}
report={'model_sha256':hashlib.sha256(ns['MODEL'].read_bytes()).hexdigest(),'pairs':[],'counterfactuals':[]}
for strong,weak in [(9138726,47138726),(9119152,47119152),(9045595,47045595),(48167905,84167905)]:
 if strong not in rows or weak not in rows:continue
 a,b=rows[strong],rows[weak];logs=predict([a,b]);report['pairs'].append({'strong_spid':strong,'weak_spid':weak,'current_and_seed':[prices[strong],prices[weak]],'recomputed_prices':[max(1,round(__import__('math').exp(float(v)))//1000) for v in logs],'all_model_input_differences':{f:[b[f],a[f]] for f in model.model['features'] if b[f]!=a[f]}})
base=rows[47138726];variants=[base];labels=['original']
for f in ['positioning','agility','reactions','marking']:
 v=copy.copy(base);v[f]=rows[9138726][f];variants.append(v);labels.append(f)
for label,v,log in zip(labels,variants,predict(variants)):
 report['counterfactuals'].append({'change':label,'input':None if label=='original' else [base[label],v[label]],'price':max(1,round(__import__('math').exp(float(log)))//1000)})
# Strict comparisons hold every other model input fixed, unlike cross-card comparisons.
checks=[]
for spid in [9138726,47138726,9119152,47119152,9045595,47045595,48167905,84037576]:
 if spid not in rows:continue
 base=rows[spid];batch=[base];fields=[]
 for f in model.model['encoder']['numeric']:
  if f in ['height','weight','attackingworkrate','defensiveworkrate','weakfootabilitytypecode','skillmoves']:continue
  v=copy.copy(base);v[f]+=1;batch.append(v);fields.append(f)
 logs=predict(batch)
 for f,log in zip(fields,logs[1:]):
  ratio=float(__import__('math').exp(log-logs[0]))
  if ratio<.99:checks.append({'spid':spid,'only_change':f+' +1','price_ratio':ratio})
report['single_stat_decreases']=sorted(checks,key=lambda x:x['price_ratio'])
training=json.loads((R/'highend-training/results/training-report.json').read_text('utf8'))
report['test_metrics']=training['selected_refit_test'];report['training_rows']={k:training[k] for k in ['final_real_training_rows','final_synthetic_training_rows']}
(O/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
