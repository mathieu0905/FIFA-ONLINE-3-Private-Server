"""GPU small value model, with explicit weak-foot/skill-move branch and ablation."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4');os.environ.setdefault('MKL_NUM_THREADS','4');os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
from pathlib import Path
import json,math,time,copy,random,platform
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F
P=Path(__file__).resolve().parent;O=P/'results';O.mkdir(exist_ok=True)
torch.set_num_threads(4);torch.set_num_interop_threads(1)
assert torch.cuda.is_available(),'CUDA environment required'
torch.cuda.set_device(0);torch.cuda.set_per_process_memory_fraction(.025,0)
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
device=torch.device('cuda:0');torch.cuda.reset_peak_memory_stats()
d=np.load(P/'data.npz');X=d['X'].astype(np.float32);y=d['y'];groups=d['groups'];meta=json.loads((P/'data-meta.json').read_text());split=json.loads((P/'split-indices.json').read_text());train=np.array(split['train']);val=np.array(split['validation']);test=np.array(split['test']);outer=np.concatenate([train,val])
assert not (set(groups[train])&set(groups[val]) or set(groups[outer])&set(groups[test]))
features=meta['features'];NUMERIC_COUNT=len(meta['base_features']);stars=[features.index('weakfootabilitytypecode'),features.index('skillmoves')];nonstar=[i for i in range(len(features)) if i not in stars]

def metrics(actual,pred):
 e=np.abs(actual-pred);return dict(log_mae=float(e.mean()),median_error_factor=float(np.exp(np.median(e))),within_2x=float((e<=np.log(2)).mean()),within_3x=float((e<=np.log(3)).mean()),p90_error_factor=float(np.exp(np.quantile(e,.9))))

class ValueNet(nn.Module):
 def __init__(self,kind,mean,std,ym,ys):
  super().__init__();self.kind=kind;self.register_buffer('mean',torch.tensor(mean));self.register_buffer('std',torch.tensor(std));self.ym=ym;self.ys=ys
  columns=list(range(len(features))) if kind=='plain' else nonstar;self.register_buffer('columns',torch.tensor(columns,dtype=torch.long))
  n=len(columns);layers=[]
  for width in ACTIVE_CONFIG['widths']:
   layers.extend([nn.Linear(n,width),nn.SiLU(),nn.Dropout(ACTIVE_CONFIG['dropout'])]);n=width
  layers.append(nn.Linear(n,1));self.net=nn.Sequential(*layers);self.skip=nn.Linear(len(columns),1);nn.init.zeros_(self.skip.weight);nn.init.zeros_(self.skip.bias)
  if kind=='stars':
   self.star_raw=nn.Parameter(torch.full((2,5),-4.));self.star_gate=nn.Linear(len(columns),2)
 def forward(self,raw):
  z=torch.clamp((raw-self.mean)/self.std,-8,8)
  if self.training:
   z=torch.cat([z[:,:NUMERIC_COUNT],z[:,NUMERIC_COUNT:]*(torch.rand_like(z[:,NUMERIC_COUNT:])>=.05)],dim=1)
  h=z[:,self.columns];value=(self.net(h)+self.skip(h)).squeeze(-1)
  if self.kind=='stars':
   # Monotone, learned positive increments; this is a declared domain prior,
   # not a claim that raw historical prices prove a causal star premium.
   w=F.softplus(self.star_raw);wf=raw[:,stars[0]];sm=raw[:,stars[1]]
   a=torch.stack([sum((wf>=threshold).float()*w[0,j] for j,threshold in enumerate((2,3,4,5,6))),sum((sm>=threshold).float()*w[1,j] for j,threshold in enumerate((1,2,3,4,5)))],dim=1)
   value=value+(a*torch.sigmoid(self.star_gate(h))).sum(1)
  return value

def scaling(indices):
 mean=X[indices].mean(0);std=X[indices].std(0);std[std<1e-6]=1
 mean[NUMERIC_COUNT:]=0;std[NUMERIC_COUNT:]=1
 return mean,std,float(y[indices].mean()),float(y[indices].std())
T=torch.tensor(X,device=device);Y=torch.tensor(y,dtype=torch.float32,device=device)

def fit(kind,seed,indices,validation=None,fixed_epochs=None):
 torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);np.random.seed(seed);random.seed(seed)
 mean,std,ym,ys=scaling(indices);model=ValueNet(kind,mean,std,ym,ys).to(device)
 regular=[p for n,p in model.named_parameters() if n!='star_raw'];params=[dict(params=regular,weight_decay=ACTIVE_CONFIG['weight_decay'])]
 if kind=='stars':params.append(dict(params=[model.star_raw],weight_decay=0.))
 optimizer=torch.optim.AdamW(params,lr=ACTIVE_CONFIG['lr']);scheduler=torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer,mode='min',factor=.5,patience=25,min_lr=1e-6)
 best=float('inf');best_state=None;best_epoch=0;hist=[];idx=torch.tensor(indices,device=device,dtype=torch.long)
 maximum=fixed_epochs or ACTIVE_CONFIG['max_epochs']
 for epoch in range(1,maximum+1):
  model.train();order=idx[torch.randperm(len(idx),device=device)];train_loss=0.
  if fixed_epochs:
   lr=REFIT_LRS[epoch-1] if REFIT_LRS else ACTIVE_CONFIG['lr']
   for g in optimizer.param_groups:g['lr']=lr
  for off in range(0,len(order),512):
   batch=order[off:off+512];optimizer.zero_grad(set_to_none=True);pred=model(T[batch]);loss=F.smooth_l1_loss(pred,(Y[batch]-ym)/ys,beta=.25)
   if kind=='stars':loss=loss+.001*F.softplus(model.star_raw).square().sum()
   loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5.);optimizer.step();train_loss+=loss.detach()*len(batch)
  if validation is not None:
   model.eval()
   with torch.no_grad():p=(model(T[validation])*ys+ym).cpu().numpy()
   score=float(np.abs(p-y[validation]).mean());hist.append(dict(epoch=epoch,validation_log_mae=score,training_loss=float(train_loss)/len(indices),learning_rate=optimizer.param_groups[0]['lr']));scheduler.step(score)
   if score<best-1e-4:best=score;best_epoch=epoch;best_state=copy.deepcopy({k:v.cpu() for k,v in model.state_dict().items()})
   if epoch%50==0:print('EPOCH',ACTIVE_CONFIG['name'],seed,epoch,'train',round(float(train_loss)/len(indices),5),'val',round(score,5),'best',round(best,5),'best_epoch',best_epoch,flush=True)
   if epoch>=200 and epoch-best_epoch>=150:break
  elif epoch%50==0:print('REFIT_EPOCH',kind,seed,epoch,flush=True)
 if best_state is not None:model.load_state_dict(best_state)
 model.eval()
 with torch.no_grad():p=(model(T)*ys+ym).cpu().numpy()
 return model,p,dict(epochs=epoch,best_epoch=best_epoch or maximum,history=hist,parameters=sum(p.numel() for p in model.parameters()))



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
report=dict(status='COMPLETED',selected_on_validation=choice,selection_uses_test=False,model_results=model_info,validation_selected_test=model_info[choice]['test'],selected_refit_test=metrics(y[test],final[test]),runs=runs,configurations=CONFIGS,split_counts=dict(train=len(train),validation=len(val),test=len(test),refit_train=len(outer)),raw_fields=encoder['raw_fields'],encoded_feature_count=len(features),raw_feature_count=len(encoder['raw_fields']),category_vocab_fit='train only',trait_bits=encoder['trait_bits'],validation_group_permutation=importance,refit_lr_policy='replay validation-selected LR schedule; no test tuning',star_positive_branch_preserved=True,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(),physical_gpu=os.environ.get('CUDA_VISIBLE_DEVICES'),peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,elapsed_seconds=time.time()-start,production_changed=False,scaling_policy='numeric standardized; one-hot/bit inputs remain 0/1; 5% sparse feature dropout during training')
(O/'training-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('EXPANDED_COMPLETED',choice,json.dumps(report['selected_refit_test']),'elapsed',round(report['elapsed_seconds'],1),'peak_mib',report['peak_reserved_mib'],flush=True)
