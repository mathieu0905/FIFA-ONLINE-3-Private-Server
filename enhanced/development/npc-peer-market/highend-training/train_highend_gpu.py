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
d=np.load(P/'data.npz');X=d['X'].astype(np.float32);y=d['y'];groups=d['groups'];meta=json.loads((P/'data-meta.json').read_text());split=json.loads((P/'split-indices.json').read_text());train=np.array(split['train']);val=np.array(split['validation']);test=np.array(split['test']);outer=np.array(split['outer'])
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
   batch=order[off:off+512];optimizer.zero_grad(set_to_none=True);pred=model(T[batch]);point_loss=F.smooth_l1_loss(pred,(Y[batch]-ym)/ys,beta=.25,reduction='none');weights=W[batch] if ACTIVE_CONFIG['weighted'] else torch.ones_like(point_loss);loss=(point_loss*weights).sum()/weights.sum()
   if kind=='stars':loss=loss+.001*F.softplus(model.star_raw).square().sum()
   loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5.);optimizer.step();train_loss+=loss.detach()*len(batch)
  if validation is not None:
   model.eval()
   with torch.no_grad():p=(model(T[validation])*ys+ym).cpu().numpy()
   parts=validation_score(validation,p);score=parts['score'];hist.append(dict(epoch=epoch,validation_score=score,validation_log_mae=parts['overall'],validation_high_log_mae=parts['high'],validation_top_gk_log_mae=parts['top_gk'],training_loss=float(train_loss)/len(indices),learning_rate=optimizer.param_groups[0]['lr']));scheduler.step(score)
   if score<best-1e-4:best=score;best_epoch=epoch;best_state=copy.deepcopy({k:v.cpu() for k,v in model.state_dict().items()})
   if epoch%50==0:print('EPOCH',ACTIVE_CONFIG['name'],seed,epoch,'train',round(float(train_loss)/len(indices),5),'val',round(score,5),'best',round(best,5),'best_epoch',best_epoch,flush=True)
   if epoch>=150 and epoch-best_epoch>=100:break
  elif epoch%50==0:print('REFIT_EPOCH',kind,seed,epoch,flush=True)
 if best_state is not None:model.load_state_dict(best_state)
 model.eval()
 with torch.no_grad():p=(model(T)*ys+ym).cpu().numpy()
 return model,p,dict(epochs=epoch,best_epoch=best_epoch or maximum,history=hist,parameters=sum(p.numel() for p in model.parameters()))




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
  
  if config['name']=='real_only_control':
   old=Path('/home/zhihao/fo3_value_training/run-20261107-highend-kr-v7/results')
   checkpoint=torch.load(old/('real_only_control_'+str(seed)+'.pt'),map_location=device,weights_only=False)
   assert checkpoint['features']==features,'Changed encoder invalidates control reuse'
   state=checkpoint['state_dict'];net=ValueNet('stars',state['mean'].cpu().numpy(),state['std'].cpu().numpy(),checkpoint['ym'],checkpoint['ys']).to(device);net.load_state_dict(state);net.eval()
   with torch.no_grad():p=(net(T)*net.ys+net.ym).cpu().numpy()
   info=json.loads((old/'training-report.json').read_text())['runs']['real_only_control_'+str(seed)]
  else:net,p,info=fit('stars',seed,indices,val)
  info['validation']=cohort_metrics(val,p[val]);runs[config['name']+'_'+str(seed)]=info;preds.append(p);nets.append(net)
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
def portable(nets):
 export=dict(schema=3,type='encoded_attribute_ensemble',kind='stars',features=encoder['raw_fields'],encoded_features=features,encoder=encoder,input_clip=8,star_indices=stars,nonstar_indices=nonstar,members=[],price_unit='historical Korea EP at source default +1')
 for net in nets:
  layers=[]
  for layer in net.net:
   if isinstance(layer,nn.Linear):layers.append(dict(type='linear',weight=layer.weight.detach().cpu().tolist(),bias=layer.bias.detach().cpu().tolist()))
   elif isinstance(layer,nn.SiLU):layers.append(dict(type='silu'))
  export['members'].append(dict(mean=net.mean.cpu().tolist(),std=net.std.cpu().tolist(),y_mean=net.ym,y_std=net.ys,columns=net.columns.cpu().tolist(),layers=layers,skip_weight=net.skip.weight.detach().cpu().tolist()[0],skip_bias=float(net.skip.bias.detach().cpu()[0]),star_raw=net.star_raw.detach().cpu().tolist(),star_gate_weight=net.star_gate.weight.detach().cpu().tolist(),star_gate_bias=net.star_gate.bias.detach().cpu().tolist()))
 return export

export=portable(refitted);export['training_region']='kr';export['synthetic_data_warning']='Game-design priors clearly separated from observed prices; no synthetic validation/test labels'
with gzip.open(O/'selected-model.json.gz','wb',compresslevel=1) as file:file.write(json.dumps(export,separators=(',',':')).encode('utf8'))
probes=json.loads((P/'encoding-probes.json').read_text())
for probe,i in zip(probes,test[:100]):probe['log_prediction']=float(final[i])
(O/'inference-probes.json').write_text(json.dumps(probes),encoding='utf8')
np.savez_compressed(O/'test-predictions.npz',indices=test,spids=d['spids'][test],y=y[test],new=final[test],control=model_predictions['real_only_control'][test],validation_selected=model_predictions['highend_augmented'][test],season=d['season'][test],ovr=d['ovr'][test],gk=d['gk'][test])
report=dict(status='COMPLETED',price_region='kr',selection_uses_test=False,model_policy='Corrected Nostalgia anchor priority: UL then WL, not ordinary native template; real-control checkpoints reused unchanged; early stopping on real grouped validation only',validation_selection_score='overall real logMAE + 0.5 high-end logMAE + 0.25 top-GK logMAE',model_results=results,selected_refit_test=cohort_metrics(test,final[test]),runs=runs,configurations=CONFIGS,final_training_rows=len(outer),final_real_training_rows=len(split['real_outer']),final_synthetic_training_rows=len(outer)-len(split['real_outer']),split_counts={k:len(v) for k,v in split.items()},raw_fields=encoder['raw_fields'],encoded_dimensions=len(features),data_audit=json.loads((P/'data-audit.json').read_text()),elapsed_seconds=time.time()-start,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,production_changed=False)
(O/'training-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('HIGHEND_COMPLETED',json.dumps(report['selected_refit_test']),'elapsed',report['elapsed_seconds'],'peak_mib',report['peak_reserved_mib'],flush=True)
