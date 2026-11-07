from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent
s=(R/'clean-training/train_clean_gpu.py').read_text('utf8');s=s[:s.index('encoder=json.loads')]
s=s.replace("outer=np.concatenate([train,val])","outer=np.array(split['outer'])")
s=s.replace("loss=F.smooth_l1_loss(pred,(Y[batch]-ym)/ys,beta=.25)","point_loss=F.smooth_l1_loss(pred,(Y[batch]-ym)/ys,beta=.25,reduction='none');weights=W[batch] if ACTIVE_CONFIG['weighted'] else torch.ones_like(point_loss);loss=(point_loss*weights).sum()/weights.sum()")
s=s.replace("score=float(np.abs(p-y[validation]).mean());hist.append(dict(epoch=epoch,validation_log_mae=score,training_loss=float(train_loss)/len(indices),learning_rate=optimizer.param_groups[0]['lr']));scheduler.step(score)","parts=validation_score(validation,p);score=parts['score'];hist.append(dict(epoch=epoch,validation_score=score,validation_log_mae=parts['overall'],validation_high_log_mae=parts['high'],validation_top_gk_log_mae=parts['top_gk'],training_loss=float(train_loss)/len(indices),learning_rate=optimizer.param_groups[0]['lr']));scheduler.step(score)")
s=s.replace("if epoch>=200 and epoch-best_epoch>=150:break","if epoch>=150 and epoch-best_epoch>=100:break")
s+='''
import gzip
encoder=json.loads((P/'encoder.json').read_text());W=torch.tensor(d['weights'],device=device)
REFIT_LRS=None
def cohort_metrics(indices,p):
 masks=dict(overall=np.ones(len(indices),dtype=bool),high=(np.isin(d['season'][indices],[30,93])|(d['ovr'][indices]>=82)),top_gk=(d['gk'][indices]&(np.isin(d['season'][indices],[30,93])|(d['ovr'][indices]>=80))),WL=d['season'][indices]==93,UL=d['season'][indices]==30)
 return {k:dict(rows=int(mask.sum()),**metrics(y[indices][mask],p[mask])) for k,mask in masks.items() if mask.any()}
def validation_score(indices,p):
 e=np.abs(y[indices]-p);hi=np.isin(d['season'][indices],[30,93])|(d['ovr'][indices]>=82);gk=d['gk'][indices]&(np.isin(d['season'][indices],[30,93])|(d['ovr'][indices]>=80))
 a=float(e.mean());b=float(e[hi].mean()) if hi.any() else a;c=float(e[gk].mean()) if gk.any() else a
 return dict(score=a+.5*b+.25*c,overall=a,high=b,top_gk=c)
CONFIGS=[dict(name='real_only_control',widths=[2048,2048,1024,512],dropout=.22,weight_decay=.02,lr=.0003,max_epochs=650,weighted=False),dict(name='highend_augmented',widths=[2048,2048,1024,512],dropout=.22,weight_decay=.02,lr=.0003,max_epochs=650,weighted=True)]
start=time.time();runs={};model_predictions={};chosen_nets=[]
print('HIGHEND_START',json.dumps(dict(rows=len(X),features=len(features),raw_fields=len(encoder['raw_fields']),gpu=torch.cuda.get_device_name(),physical_gpu=os.environ.get('CUDA_VISIBLE_DEVICES'))),flush=True)
for config in CONFIGS:
 ACTIVE_CONFIG=config;indices=np.array(split['real_train']) if config['name']=='real_only_control' else train;preds=[];nets=[]
 for seed in (2026,2027):
  print('RUN_START',config['name'],seed,'training_rows',len(indices),flush=True)
  net,p,info=fit('stars',seed,indices,val);info['validation']=cohort_metrics(val,p[val]);runs[config['name']+'_'+str(seed)]=info;preds.append(p);nets.append(net)
  torch.save(dict(state_dict=net.state_dict(),config=config,ym=net.ym,ys=net.ys,features=features),O/(config['name']+'_'+str(seed)+'.pt'))
  (O/'progress.json').write_text(json.dumps(dict(completed=list(runs),latest=config['name']+'_'+str(seed),best_epoch=info['best_epoch'],validation=info['validation'],elapsed_seconds=time.time()-start)),encoding='utf8')
  print('RUN_DONE',config['name'],seed,'best_epoch',info['best_epoch'],json.dumps(info['validation']),flush=True)
 model_predictions[config['name']]=np.mean(preds,axis=0)
 if config['name']=='highend_augmented':chosen_nets=nets
results={name:dict(validation=cohort_metrics(val,p[val]),test=cohort_metrics(test,p[test])) for name,p in model_predictions.items()}
# Augmentation is the requested fixed modelling policy. The real-only network
# is a diagnostic ablation, not selected using the final test results.
ACTIVE_CONFIG=CONFIGS[1];refitted=[];preds=[]
for seed in (2026,2027):
 info=runs['highend_augmented_'+str(seed)];epochs=info['best_epoch'];REFIT_LRS=[h['learning_rate'] for h in info['history'][:epochs]]
 print('FINAL_REFIT',seed,'rows',len(outer),'epochs',epochs,flush=True)
 net,p,_=fit('stars',seed,outer,fixed_epochs=epochs);refitted.append(net);preds.append(p)
 torch.save(dict(state_dict=net.state_dict(),config=ACTIVE_CONFIG,ym=net.ym,ys=net.ys,features=features,encoder=encoder),O/('selected_'+str(seed)+'.pt'))
final=np.mean(preds,axis=0)
'''
portable=(R/'clean-training/train_clean_gpu.py').read_text('utf8');a=portable.index('def portable(nets):');b=portable.index('# Compress numeric JSON',a);s+=portable[a:b].replace("price_unit='historical Indonesia EP at source default +1'","price_unit='historical Korea EP at source default +1'")
s+='''
export=portable(refitted);export['training_region']='kr';export['synthetic_data_warning']='Game-design priors clearly separated from observed prices; no synthetic validation/test labels'
with gzip.open(O/'selected-model.json.gz','wb',compresslevel=1) as file:file.write(json.dumps(export,separators=(',',':')).encode('utf8'))
probes=json.loads((P/'encoding-probes.json').read_text())
for probe,i in zip(probes,test[:100]):probe['log_prediction']=float(final[i])
(O/'inference-probes.json').write_text(json.dumps(probes),encoding='utf8')
np.savez_compressed(O/'test-predictions.npz',indices=test,spids=d['spids'][test],y=y[test],new=final[test],control=model_predictions['real_only_control'][test],validation_selected=model_predictions['highend_augmented'][test],season=d['season'][test],ovr=d['ovr'][test],gk=d['gk'][test])
report=dict(status='COMPLETED',price_region='kr',selection_uses_test=False,model_policy='Fixed requested high-end augmentation; early stopping on real grouped validation only',validation_selection_score='overall real logMAE + 0.5 high-end logMAE + 0.25 top-GK logMAE',model_results=results,selected_refit_test=cohort_metrics(test,final[test]),runs=runs,configurations=CONFIGS,final_training_rows=len(outer),final_real_training_rows=len(split['real_outer']),final_synthetic_training_rows=len(outer)-len(split['real_outer']),split_counts={k:len(v) for k,v in split.items()},raw_fields=encoder['raw_fields'],encoded_dimensions=len(features),data_audit=json.loads((P/'data-audit.json').read_text()),elapsed_seconds=time.time()-start,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,production_changed=False)
(O/'training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HIGHEND_COMPLETED',json.dumps(report['selected_refit_test']),'elapsed',report['elapsed_seconds'],'peak_mib',report['peak_reserved_mib'],flush=True)
'''
(P/'train_highend_gpu.py').write_text(s,'utf8');compile(s,'train_highend_gpu.py','exec');print('Prepared real-control and high-end-augmented ensemble trainer')
