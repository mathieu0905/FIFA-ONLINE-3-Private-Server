from pathlib import Path
R=Path('D:/fifaol3/npc-peer-market/remote-training');s=(R/'train_gpu.py').read_text('utf-8-sig')
# Reuse the established split, star constraints and portable export. Only scale
# network capacity and training budget; all comparisons remain validation-only.
s=s[:s.index('start=time.time();print')]
s=s.replace("torch.cuda.set_per_process_memory_fraction(.008,0)","torch.cuda.set_per_process_memory_fraction(.02,0)")
a=s.index('  n=len(columns);self.net=');b=s.index("  if kind=='stars':",a)
s=s[:a]+'''  n=len(columns);layers=[]
  for width in ACTIVE_CONFIG['widths']:
   layers.extend([nn.Linear(n,width),nn.SiLU(),nn.Dropout(ACTIVE_CONFIG['dropout'])]);n=width
  layers.append(nn.Linear(n,1));self.net=nn.Sequential(*layers);self.skip=nn.Linear(len(columns),1);nn.init.zeros_(self.skip.weight);nn.init.zeros_(self.skip.bias)
''' +s[b:]
s=s.replace("dict(params=regular,weight_decay=.01)","dict(params=regular,weight_decay=ACTIVE_CONFIG['weight_decay'])")
s=s.replace("optimizer=torch.optim.AdamW(params,lr=.0008)","optimizer=torch.optim.AdamW(params,lr=ACTIVE_CONFIG['lr'])")
s=s.replace("patience=10,min_lr=1e-5", "patience=25,min_lr=1e-6")
s=s.replace("maximum=fixed_epochs or 300", "maximum=fixed_epochs or ACTIVE_CONFIG['max_epochs']")
s=s.replace("model.train();order=idx[torch.randperm(len(idx),device=device)]", "model.train();order=idx[torch.randperm(len(idx),device=device)];train_loss=0.")
s=s.replace("loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5.);optimizer.step()", "loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5.);optimizer.step();train_loss+=float(loss.detach())*len(batch)")
s=s.replace("hist.append(dict(epoch=epoch,validation_log_mae=score))", "hist.append(dict(epoch=epoch,validation_log_mae=score,training_loss=train_loss/len(indices),learning_rate=optimizer.param_groups[0]['lr']))")
s=s.replace("if epoch%50==0:print('EPOCH',kind,seed,epoch,round(score,5),flush=True)","if epoch%50==0:print('EPOCH',ACTIVE_CONFIG['name'],seed,epoch,'train',round(train_loss/len(indices),5),'val',round(score,5),'best',round(best,5),'best_epoch',best_epoch,flush=True)")
s=s.replace("if epoch-best_epoch>=35:break", "if epoch>=200 and epoch-best_epoch>=150:break")
s=s.replace("lr=.00008+(.0008-.00008)*(.5+.5*math.cos(math.pi*(epoch-1)/maximum))", "lr=ACTIVE_CONFIG['lr']*(.1+.9*(.5+.5*math.cos(math.pi*(epoch-1)/maximum)))")
s=s.replace('self.star_gate=nn.Linear(n,2)','self.star_gate=nn.Linear(len(columns),2)')
s+='''
CONFIGS=[
 dict(name='small_long',widths=[128,96,48],dropout=.08,weight_decay=.01,lr=.0008,max_epochs=1200),
 dict(name='medium_long',widths=[512,512,256,128],dropout=.18,weight_decay=.02,lr=.0005,max_epochs=1000),
 dict(name='large_long',widths=[1024,1024,512,256],dropout=.25,weight_decay=.03,lr=.0003,max_epochs=1000),
]
start=time.time();print('LARGE_START',json.dumps(dict(gpu=torch.cuda.get_device_name(),rows=len(X),features=len(features),cuda=torch.version.cuda,configs=CONFIGS)),flush=True)
runs={};models={};model_info={}
for config in CONFIGS:
 ACTIVE_CONFIG=config;preds=[];nets=[];infos=[]
 for seed in (2026,2027):
  print('RUN_START',config['name'],seed,flush=True)
  net,p,info=fit('stars',seed,train,val);label=config['name']+'_'+str(seed)
  info['validation']=metrics(y[val],p[val]);runs[label]=info;preds.append(p);nets.append(net);infos.append(info)
  torch.save(dict(state_dict=net.state_dict(),config=config,ym=net.ym,ys=net.ys,features=features),O/(label+'.pt'))
  (O/'progress.json').write_text(json.dumps(dict(completed=list(runs),latest=label,validation=info['validation'],best_epoch=info['best_epoch'],parameters=info['parameters'],elapsed=time.time()-start)),encoding='utf8')
  print('RUN_DONE',label,'params',info['parameters'],'best_epoch',info['best_epoch'],json.dumps(info['validation']),flush=True)
 pred=np.mean(preds,axis=0);models[config['name']]=(pred,nets,config);model_info[config['name']]=dict(validation=metrics(y[val],pred[val]),parameters_per_model=infos[0]['parameters'])
choice=min(models,key=lambda k:model_info[k]['validation']['log_mae'])
for label,(pred,_,_) in models.items():model_info[label]['test']=metrics(y[test],pred[test])
chosen_pred,_,ACTIVE_CONFIG=models[choice]
refitted=[];refit_preds=[]
for seed in (2026,2027):
 epochs=runs[choice+'_'+str(seed)]['best_epoch'];print('FINAL_REFIT',choice,seed,epochs,flush=True)
 net,p,info=fit('stars',seed,outer,fixed_epochs=epochs);refitted.append(net);refit_preds.append(p)
 torch.save(dict(state_dict=net.state_dict(),config=ACTIVE_CONFIG,ym=net.ym,ys=net.ys,features=features),O/('selected_'+str(seed)+'.pt'))
final=np.mean(refit_preds,axis=0)
export=dict(schema=2,type='gpu_attribute_ensemble',kind='stars',features=features,input_clip=8,star_indices=stars,nonstar_indices=nonstar,members=[],price_unit='historical normalized EP at +1')
for net in refitted:
 layers=[]
 for layer in net.net:
  if isinstance(layer,nn.Linear):layers.append(dict(type='linear',weight=layer.weight.detach().cpu().tolist(),bias=layer.bias.detach().cpu().tolist()))
  elif isinstance(layer,nn.SiLU):layers.append(dict(type='silu'))
 member=dict(mean=net.mean.cpu().tolist(),std=net.std.cpu().tolist(),y_mean=net.ym,y_std=net.ys,columns=net.columns.cpu().tolist(),layers=layers,skip_weight=net.skip.weight.detach().cpu().tolist()[0],skip_bias=float(net.skip.bias.detach().cpu()[0]),star_raw=net.star_raw.detach().cpu().tolist(),star_gate_weight=net.star_gate.weight.detach().cpu().tolist(),star_gate_bias=net.star_gate.bias.detach().cpu().tolist())
 export['members'].append(member)
(O/'selected-model.json').write_text(json.dumps(export),encoding='utf8')
(O/'inference-probes.json').write_text(json.dumps([dict(attributes=X[i].tolist(),log_prediction=float(final[i])) for i in test[:100]]),encoding='utf8')
report=dict(status='COMPLETED',selected_on_validation=choice,selection_uses_test=False,model_results=model_info,selected_refit_test=metrics(y[test],final[test]),runs=runs,configurations=CONFIGS,split_counts=dict(train=len(train),validation=len(val),test=len(test),refit_train=len(outer)),features=features,star_positive_branch_preserved=True,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(),physical_gpu=os.environ.get('CUDA_VISIBLE_DEVICES'),peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,elapsed_seconds=time.time()-start,production_changed=False)
(O/'training-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('LARGE_COMPLETED',choice,json.dumps(report['selected_refit_test']),'elapsed',round(report['elapsed_seconds'],1),'peak_mib',report['peak_reserved_mib'],flush=True)
'''
(R/'train_larger_gpu.py').write_text(s,'utf8');compile(s,'train_larger_gpu.py','exec')
print('Prepared controlled capacity and training-budget experiment')
