from pathlib import Path
P=Path(__file__).resolve().parent;s=(P/'train_clean_gpu.py').read_text('utf8');s=s[:s.index('encoder=json.loads')]
s+='''
import gzip
encoder=json.loads((P/'encoder.json').read_text())
control=json.loads((P/'results/training-report.json').read_text())
extra=np.load(P/'extra.npz');audit=json.loads((P/'extra-audit.json').read_text())
original_count=len(X);original_outer=len(outer)
X=np.concatenate([X,extra['X']]);y=np.concatenate([y,extra['y']]);groups=np.concatenate([groups,extra['groups']])
add=np.flatnonzero(extra['refit_eligible'])+original_count;outer=np.concatenate([outer,add])
assert not set(groups[outer])&set(groups[test])
T=torch.tensor(X,device=device);Y=torch.tensor(y,dtype=torch.float32,device=device)
O=P/'results/final';O.mkdir(exist_ok=True)
ACTIVE_CONFIG=next(c for c in control['configurations'] if c['name']==control['selected_on_validation'])
start=time.time();nets=[];preds=[];epochs_by_seed={}
for seed in (2026,2027):
 info=control['runs'][ACTIVE_CONFIG['name']+'_'+str(seed)];epochs=info['best_epoch'];epochs_by_seed[str(seed)]=epochs;REFIT_LRS=[h['learning_rate'] for h in info['history'][:epochs]]
 print('AUGMENTED_REFIT',seed,'rows',len(outer),'epochs',epochs,flush=True)
 net,p,_=fit('stars',seed,outer,fixed_epochs=epochs);nets.append(net);preds.append(p)
 torch.save(dict(state_dict=net.state_dict(),config=ACTIVE_CONFIG,ym=net.ym,ys=net.ys,features=features,encoder=encoder),O/('selected_'+str(seed)+'.pt'))
final=np.mean(preds,axis=0)
'''
original=(P/'train_clean_gpu.py').read_text('utf8');a=original.index('def portable(nets):');b=original.index('# Compress numeric JSON',a);s+=original[a:b]
s+='''
export=portable(nets);export['training_region']='id';export['additional_training_policy']=audit['policy']
with gzip.open(O/'selected-model.json.gz','wb',compresslevel=1) as file:file.write(json.dumps(export,separators=(',',':')).encode('utf8'))
probes=json.loads((P/'encoding-probes.json').read_text())
for probe,i in zip(probes,test[:100]):probe['log_prediction']=float(final[i])
(O/'inference-probes.json').write_text(json.dumps(probes),encoding='utf8')
old=np.load(P/'results/test-predictions.npz');assert np.array_equal(old['spids'],d['spids'][test])
np.savez_compressed(O/'test-predictions.npz',spids=d['spids'][test],y=y[test],new=final[test],old=old['old'])
extra_test=np.flatnonzero(~extra['refit_eligible'])+original_count
np.savez_compressed(O/'extra-test-predictions.npz',spids=extra['spids'][~extra['refit_eligible']],y=y[extra_test],new=final[extra_test])
report=dict(control,selected_refit_test=metrics(y[test],final[test]),control_refit_test=control['selected_refit_test'],extra_audit=audit,final_refit_rows=len(outer),original_refit_rows=original_outer,extra_refit_rows=len(add),selection_uses_test=False,final_refit_hyperparameter_policy='Reuse original clean validation-selected config, epochs and LR schedules; augmentation committed before examining test results',original_test_cards=len(test),extra_test_cards=len(extra_test),extra_test=metrics(y[extra_test],final[extra_test]) if len(extra_test) else None,epochs_by_seed=epochs_by_seed,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,elapsed_seconds=time.time()-start,control_training_elapsed_seconds=control['elapsed_seconds'],production_changed=False)
(O/'training-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('AUGMENTED_COMPLETED',json.dumps(report['selected_refit_test']),json.dumps(dict(elapsed=report['elapsed_seconds'],peak_mib=report['peak_reserved_mib'])),flush=True)
'''
(P/'refit_extra_gpu.py').write_text(s,'utf8');compile(s,'refit_extra_gpu.py','exec');print('Prepared extra-data final refit; held-out player groups remain protected')
