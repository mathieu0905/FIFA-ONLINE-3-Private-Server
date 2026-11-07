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
def portable(nets):
 export=dict(schema=3,type='encoded_attribute_ensemble',kind='stars',features=encoder['raw_fields'],encoded_features=features,encoder=encoder,input_clip=8,star_indices=stars,nonstar_indices=nonstar,members=[],price_unit='historical Indonesia EP at source default +1')
 for net in nets:
  layers=[]
  for layer in net.net:
   if isinstance(layer,nn.Linear):layers.append(dict(type='linear',weight=layer.weight.detach().cpu().tolist(),bias=layer.bias.detach().cpu().tolist()))
   elif isinstance(layer,nn.SiLU):layers.append(dict(type='silu'))
  export['members'].append(dict(mean=net.mean.cpu().tolist(),std=net.std.cpu().tolist(),y_mean=net.ym,y_std=net.ys,columns=net.columns.cpu().tolist(),layers=layers,skip_weight=net.skip.weight.detach().cpu().tolist()[0],skip_bias=float(net.skip.bias.detach().cpu()[0]),star_raw=net.star_raw.detach().cpu().tolist(),star_gate_weight=net.star_gate.weight.detach().cpu().tolist(),star_gate_bias=net.star_gate.bias.detach().cpu().tolist()))
 return export

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
