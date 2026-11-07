from pathlib import Path
R=Path('D:/fifaol3/npc-peer-market');O=R/'expanded-training';source=(R/'remote-training/train_larger_gpu.py').read_text('utf8')
s=source[:source.index('CONFIGS=[')]
s=s.replace('torch.cuda.set_per_process_memory_fraction(.02,0)','torch.cuda.set_per_process_memory_fraction(.025,0)')
s=s.replace('train_loss+=float(loss.detach())*len(batch)','train_loss+=loss.detach()*len(batch)')
s=s.replace('training_loss=train_loss/len(indices)','training_loss=float(train_loss)/len(indices)').replace('round(train_loss/len(indices),5)','round(float(train_loss)/len(indices),5)')
s=s.replace("lr=ACTIVE_CONFIG['lr']*(.1+.9*(.5+.5*math.cos(math.pi*(epoch-1)/maximum)))", "lr=REFIT_LRS[epoch-1] if REFIT_LRS else ACTIVE_CONFIG['lr']")
s+='''
encoder=json.loads((P/'encoder.json').read_text())
CONFIGS=[
 dict(name='full_same_arch',widths=[512,512,256,128],dropout=.18,weight_decay=.02,lr=.0005,max_epochs=1000),
 dict(name='full_big',widths=[1024,1024,512,256],dropout=.25,weight_decay=.03,lr=.0003,max_epochs=1000),
 dict(name='full_xl',widths=[2048,2048,1024,512],dropout=.25,weight_decay=.03,lr=.0002,max_epochs=1000),
]
REFIT_LRS=None
start=time.time();print('EXPANDED_START',json.dumps(dict(gpu=torch.cuda.get_device_name(),rows=len(X),raw_features=len(encoder['raw_fields']),encoded_features=len(features),configs=CONFIGS)),flush=True)
runs={};models={};model_info={}
for config in CONFIGS:
 ACTIVE_CONFIG=config;preds=[];nets=[];infos=[]
 for seed in (2026,2027):
  print('RUN_START',config['name'],seed,flush=True)
  net,p,info=fit('stars',seed,train,val);label=config['name']+'_'+str(seed)
  info['validation']=metrics(y[val],p[val]);info['training_at_best']=metrics(y[train],p[train]);runs[label]=info;preds.append(p);nets.append(net);infos.append(info)
  torch.save(dict(state_dict=net.state_dict(),config=config,ym=net.ym,ys=net.ys,features=features),O/(label+'.pt'))
  (O/'progress.json').write_text(json.dumps(dict(completed=list(runs),latest=label,validation=info['validation'],best_epoch=info['best_epoch'],parameters=info['parameters'],elapsed=time.time()-start)),encoding='utf8')
  print('RUN_DONE',label,'params',info['parameters'],'best_epoch',info['best_epoch'],json.dumps(info['validation']),flush=True)
 pred=np.mean(preds,axis=0);models[config['name']]=(pred,nets,config);model_info[config['name']]=dict(validation=metrics(y[val],pred[val]),parameters_per_model=infos[0]['parameters'])
choice=min(models,key=lambda k:model_info[k]['validation']['log_mae'])
for label,(pred,_,_) in models.items():model_info[label]['test']=metrics(y[test],pred[test])
# Joint feature permutations preserve each categorical block and bitmask pattern.
selected_nets=models[choice][1];rng=np.random.default_rng(2026);subset=rng.choice(val,min(2000,len(val)),replace=False)
def ensemble_prediction(t):
 with torch.no_grad():return np.mean([(net(t)*net.ys+net.ym).cpu().numpy() for net in selected_nets],axis=0)
base_pred=ensemble_prediction(T[subset]);original=float(np.abs(base_pred-y[subset]).mean());importance={}
blocks={
 'positions':[i for i,f in enumerate(features) if f.startswith('cat:preferredposition')],
 'preferred_foot':[i for i,f in enumerate(features) if f.startswith('cat:preferredfoot:')],
 'body_type':[i for i,f in enumerate(features) if f.startswith('cat:bodytypecode:')],
 'hidden_traits':[i for i,f in enumerate(features) if f.startswith('bit:')],
 'running_animations':[i for i,f in enumerate(features) if f.startswith(('cat:runningcode1:','cat:runningcode2:'))],
 'shooting_animations':[i for i,f in enumerate(features) if f.startswith(('cat:finishingcode1:','cat:finishingcode2:'))],
 'set_piece_keeper_consistency':[i for i,f in enumerate(features) if f.startswith(('cat:anim','cat:gkkick','cat:gksave','cat:perf'))],
}
for name,cols in blocks.items():
 z=T[subset].clone();perm=torch.tensor(rng.permutation(len(subset)),device=device);z[:,cols]=z[perm][:,cols]
 p=ensemble_prediction(z);importance[name]=float(np.abs(p-y[subset]).mean()-original)
# Keep the exact validation-selected checkpoints, plus a separate refit artifact.
validation_models=selected_nets
refitted=[];refit_preds=[];chosen_pred,_,ACTIVE_CONFIG=models[choice]
for seed in (2026,2027):
 info=runs[choice+'_'+str(seed)];epochs=info['best_epoch'];REFIT_LRS=[h['learning_rate'] for h in info['history'][:epochs]]
 print('FINAL_REFIT',choice,seed,epochs,flush=True)
 net,p,_=fit('stars',seed,outer,fixed_epochs=epochs);refitted.append(net);refit_preds.append(p)
 torch.save(dict(state_dict=net.state_dict(),config=ACTIVE_CONFIG,ym=net.ym,ys=net.ys,features=features,encoder=encoder),O/('selected_'+str(seed)+'.pt'))
final=np.mean(refit_preds,axis=0)
def portable(nets):
 export=dict(schema=3,type='encoded_attribute_ensemble',kind='stars',features=encoder['raw_fields'],encoded_features=features,encoder=encoder,input_clip=8,star_indices=stars,nonstar_indices=nonstar,members=[],price_unit='historical normalized EP at +1')
 for net in nets:
  layers=[]
  for layer in net.net:
   if isinstance(layer,nn.Linear):layers.append(dict(type='linear',weight=layer.weight.detach().cpu().tolist(),bias=layer.bias.detach().cpu().tolist()))
   elif isinstance(layer,nn.SiLU):layers.append(dict(type='silu'))
  export['members'].append(dict(mean=net.mean.cpu().tolist(),std=net.std.cpu().tolist(),y_mean=net.ym,y_std=net.ys,columns=net.columns.cpu().tolist(),layers=layers,skip_weight=net.skip.weight.detach().cpu().tolist()[0],skip_bias=float(net.skip.bias.detach().cpu()[0]),star_raw=net.star_raw.detach().cpu().tolist(),star_gate_weight=net.star_gate.weight.detach().cpu().tolist(),star_gate_bias=net.star_gate.bias.detach().cpu().tolist()))
 return export
# Compress numeric JSON to keep transfer/storage bounded even for millions of weights.
import gzip
for name,nets in (('selected-model.json.gz',refitted),('validation-selected-model.json.gz',validation_models)):
 with gzip.open(O/name,'wt',encoding='utf8') as file:json.dump(portable(nets),file)
probes=json.loads((P/'encoding-probes.json').read_text())
for probe,i in zip(probes,test[:100]):probe['log_prediction']=float(final[i])
(O/'inference-probes.json').write_text(json.dumps(probes),encoding='utf8')
report=dict(status='COMPLETED',selected_on_validation=choice,selection_uses_test=False,model_results=model_info,validation_selected_test=model_info[choice]['test'],selected_refit_test=metrics(y[test],final[test]),runs=runs,configurations=CONFIGS,split_counts=dict(train=len(train),validation=len(val),test=len(test),refit_train=len(outer)),raw_fields=encoder['raw_fields'],encoded_feature_count=len(features),raw_feature_count=len(encoder['raw_fields']),category_vocab_fit='train only',trait_bits=encoder['trait_bits'],validation_group_permutation=importance,refit_lr_policy='replay validation-selected LR schedule; no test tuning',star_positive_branch_preserved=True,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(),physical_gpu=os.environ.get('CUDA_VISIBLE_DEVICES'),peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,elapsed_seconds=time.time()-start,production_changed=False)
(O/'training-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('EXPANDED_COMPLETED',choice,json.dumps(report['selected_refit_test']),'elapsed',round(report['elapsed_seconds'],1),'peak_mib',report['peak_reserved_mib'],flush=True)
'''
(O/'train_expanded_gpu.py').write_text(s,'utf8');compile(s,'train_expanded_gpu.py','exec');print('Prepared expanded feature training')
