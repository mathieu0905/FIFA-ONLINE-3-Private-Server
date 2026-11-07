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
torch.cuda.set_device(0);torch.cuda.set_per_process_memory_fraction(.008,0)
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
device=torch.device('cuda:0');torch.cuda.reset_peak_memory_stats()
d=np.load(P/'data.npz');X=d['X'].astype(np.float32);y=d['y'];groups=d['groups'];meta=json.loads((P/'data-meta.json').read_text());split=json.loads((P/'split-indices.json').read_text());train=np.array(split['train']);val=np.array(split['validation']);test=np.array(split['test']);outer=np.concatenate([train,val])
assert not (set(groups[train])&set(groups[val]) or set(groups[outer])&set(groups[test]))
features=meta['features'];stars=[features.index('weakfootabilitytypecode'),features.index('skillmoves')];nonstar=[i for i in range(len(features)) if i not in stars]

def metrics(actual,pred):
 e=np.abs(actual-pred);return dict(log_mae=float(e.mean()),median_error_factor=float(np.exp(np.median(e))),within_2x=float((e<=np.log(2)).mean()),within_3x=float((e<=np.log(3)).mean()),p90_error_factor=float(np.exp(np.quantile(e,.9))))

class ValueNet(nn.Module):
 def __init__(self,kind,mean,std,ym,ys):
  super().__init__();self.kind=kind;self.register_buffer('mean',torch.tensor(mean));self.register_buffer('std',torch.tensor(std));self.ym=ym;self.ys=ys
  columns=list(range(len(features))) if kind=='plain' else nonstar;self.register_buffer('columns',torch.tensor(columns,dtype=torch.long))
  n=len(columns);self.net=nn.Sequential(nn.Linear(n,128),nn.SiLU(),nn.Dropout(.08),nn.Linear(128,96),nn.SiLU(),nn.Dropout(.08),nn.Linear(96,48),nn.SiLU(),nn.Linear(48,1));self.skip=nn.Linear(n,1);nn.init.zeros_(self.skip.weight);nn.init.zeros_(self.skip.bias)
  if kind=='stars':
   self.star_raw=nn.Parameter(torch.full((2,5),-4.));self.star_gate=nn.Linear(n,2)
 def forward(self,raw):
  z=torch.clamp((raw-self.mean)/self.std,-8,8);h=z[:,self.columns];value=(self.net(h)+self.skip(h)).squeeze(-1)
  if self.kind=='stars':
   # Monotone, learned positive increments; this is a declared domain prior,
   # not a claim that raw historical prices prove a causal star premium.
   w=F.softplus(self.star_raw);wf=raw[:,stars[0]];sm=raw[:,stars[1]]
   a=torch.stack([sum((wf>=threshold).float()*w[0,j] for j,threshold in enumerate((2,3,4,5,6))),sum((sm>=threshold).float()*w[1,j] for j,threshold in enumerate((1,2,3,4,5)))],dim=1)
   value=value+(a*torch.sigmoid(self.star_gate(h))).sum(1)
  return value

def scaling(indices):
 mean=X[indices].mean(0);std=X[indices].std(0);std[std<1e-6]=1
 return mean,std,float(y[indices].mean()),float(y[indices].std())
T=torch.tensor(X,device=device);Y=torch.tensor(y,dtype=torch.float32,device=device)

def fit(kind,seed,indices,validation=None,fixed_epochs=None):
 torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);np.random.seed(seed);random.seed(seed)
 mean,std,ym,ys=scaling(indices);model=ValueNet(kind,mean,std,ym,ys).to(device)
 regular=[p for n,p in model.named_parameters() if n!='star_raw'];params=[dict(params=regular,weight_decay=.01)]
 if kind=='stars':params.append(dict(params=[model.star_raw],weight_decay=0.))
 optimizer=torch.optim.AdamW(params,lr=.0008);scheduler=torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer,mode='min',factor=.5,patience=10,min_lr=1e-5)
 best=float('inf');best_state=None;best_epoch=0;hist=[];idx=torch.tensor(indices,device=device,dtype=torch.long)
 maximum=fixed_epochs or 300
 for epoch in range(1,maximum+1):
  model.train();order=idx[torch.randperm(len(idx),device=device)]
  if fixed_epochs:
   lr=.00008+(.0008-.00008)*(.5+.5*math.cos(math.pi*(epoch-1)/maximum))
   for g in optimizer.param_groups:g['lr']=lr
  for off in range(0,len(order),512):
   batch=order[off:off+512];optimizer.zero_grad(set_to_none=True);pred=model(T[batch]);loss=F.smooth_l1_loss(pred,(Y[batch]-ym)/ys,beta=.25)
   if kind=='stars':loss=loss+.001*F.softplus(model.star_raw).square().sum()
   loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5.);optimizer.step()
  if validation is not None:
   model.eval()
   with torch.no_grad():p=(model(T[validation])*ys+ym).cpu().numpy()
   score=float(np.abs(p-y[validation]).mean());hist.append(dict(epoch=epoch,validation_log_mae=score));scheduler.step(score)
   if score<best-1e-4:best=score;best_epoch=epoch;best_state=copy.deepcopy({k:v.cpu() for k,v in model.state_dict().items()})
   if epoch%50==0:print('EPOCH',kind,seed,epoch,round(score,5),flush=True)
   if epoch-best_epoch>=35:break
  elif epoch%50==0:print('REFIT_EPOCH',kind,seed,epoch,flush=True)
 if best_state is not None:model.load_state_dict(best_state)
 model.eval()
 with torch.no_grad():p=(model(T)*ys+ym).cpu().numpy()
 return model,p,dict(epochs=epoch,best_epoch=best_epoch or maximum,history=hist,parameters=sum(p.numel() for p in model.parameters()))

start=time.time();print('GPU_START',json.dumps(dict(host=platform.node(),gpu=torch.cuda.get_device_name(0),device=str(device),torch=torch.__version__,rows=len(X),features=len(features),memory_fraction=.008)),flush=True)
models={};scores={};runs={}
for kind,seeds in (('plain',(2026,)),('no_stars',(2026,)),('stars',(2026,2027,2028))):
 preds=[];nets=[]
 for seed in seeds:
  net,p,info=fit(kind,seed,train,val);label=kind+'_'+str(seed);runs[label]=info;scores[label]=dict(validation=metrics(y[val],p[val]));preds.append(p);nets.append(net)
  print('RUN_DONE',label,json.dumps(scores[label]),flush=True)
 pred=np.mean(preds,axis=0);models[kind]=(pred,nets);scores[kind]=dict(validation=metrics(y[val],pred[val]))
chosen=min(models,key=lambda k:scores[k]['validation']['log_mae'])
# Plain and no-stars use the same seed and capacity, providing a controlled ablation.
for kind,(pred,_) in models.items():scores[kind]['test']=metrics(y[test],pred[test])
# Refit only the preselected architecture on train+validation with fixed epochs
# selected before reading test results. Test remains excluded from all fitting.
refitted=[];refit_preds=[];selected_seeds=(2026,2027,2028) if chosen=='stars' else (2026,)
for seed in selected_seeds:
 epochs=runs[chosen+'_'+str(seed)]['best_epoch'];net,p,info=fit(chosen,seed,outer,fixed_epochs=epochs);refitted.append(net);refit_preds.append(p)
 torch.save(dict(state_dict=net.state_dict(),kind=chosen,features=features,ym=net.ym,ys=net.ys),O/f'{chosen}_{seed}_gpu.pt')
final=np.mean(refit_preds,axis=0)
# Counterfactual star controls and permutation on the held-out rows.
net=models['stars'][1][0];sample=T[test[:400]].clone()
with torch.no_grad():base=(net(sample)*net.ys+net.ym).cpu().numpy()
permutation={}
for j in stars:
 altered=sample.clone();altered[:,j]=altered[torch.randperm(len(altered),device=device),j]
 with torch.no_grad():pred=(net(altered)*net.ys+net.ym).cpu().numpy()
 permutation[features[j]]=float(np.abs(pred-y[test[:400]]).mean()-np.abs(base-y[test[:400]]).mean())
physical=T[test[0]:test[0]+1].clone();grid=[]
for wf in (2,3,4,5):
 for sm in (1,2,3,4):
  row=physical.clone();row[:,stars[0]]=wf;row[:,stars[1]]=sm
  with torch.no_grad():lp=float((net(row)*net.ys+net.ym).item())
  grid.append(dict(weakfoot_code=wf,skillmoves_code=sm,estimated_value=round(math.exp(lp))))
for sm in (1,2,3,4):assert all(a['estimated_value']<=b['estimated_value'] for a,b in zip([r for r in grid if r['skillmoves_code']==sm],[r for r in grid if r['skillmoves_code']==sm][1:]))
# Export all operations for a portable standard-library evaluator.
export=dict(schema=2,type='gpu_attribute_ensemble',kind=chosen,features=features,input_clip=8,star_indices=stars,nonstar_indices=nonstar,members=[],price_unit='historical normalized EP at +1')
for net in refitted:
 layers=[]
 for layer in net.net:
  if isinstance(layer,nn.Linear):layers.append(dict(type='linear',weight=layer.weight.detach().cpu().tolist(),bias=layer.bias.detach().cpu().tolist()))
  elif isinstance(layer,nn.SiLU):layers.append(dict(type='silu'))
 member=dict(mean=net.mean.cpu().tolist(),std=net.std.cpu().tolist(),y_mean=net.ym,y_std=net.ys,columns=net.columns.cpu().tolist(),layers=layers,skip_weight=net.skip.weight.detach().cpu().tolist()[0],skip_bias=float(net.skip.bias.detach().cpu()[0]))
 if chosen=='stars':member.update(star_raw=net.star_raw.detach().cpu().tolist(),star_gate_weight=net.star_gate.weight.detach().cpu().tolist(),star_gate_bias=net.star_gate.bias.detach().cpu().tolist())
 export['members'].append(member)
(O/'selected-model.json').write_text(json.dumps(export),encoding='utf8')
(O/'inference-probes.json').write_text(json.dumps([dict(attributes=X[i].tolist(),log_prediction=float(final[i])) for i in test[:100]]),encoding='utf8')
report=dict(status='COMPLETED',selected_on_validation=chosen,scores=scores,final_refit_test=metrics(y[test],final[test]),split_counts=dict(train=len(train),validation=len(val),test=len(test),refit_train=len(outer)),run_details=runs,weakfoot_skillmoves_permutation=permutation,controlled_star_grid=grid,stars_already_in_plain_features=True,monotone_branch_is_declared_domain_prior=True,excluded_identity_and_season=True,training_features=features,device=torch.cuda.get_device_name(0),physical_gpu=os.environ.get('CUDA_VISIBLE_DEVICES'),cuda=torch.version.cuda,torch=torch.__version__,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,elapsed_seconds=time.time()-start,production_deployed=False)
(O/'training-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GPU_COMPLETED',chosen,json.dumps(report['final_refit_test']),'peak_mib',report['peak_reserved_mib'],'elapsed',round(report['elapsed_seconds'],1),flush=True)
