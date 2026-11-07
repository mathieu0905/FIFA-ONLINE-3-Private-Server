"""Bounded CPU experiment: player-group train/val/test, numeric-attribute models only."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4');os.environ.setdefault('MKL_NUM_THREADS','4');os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
import argparse,copy,json,time,random,math,hashlib,platform
from pathlib import Path
import numpy as np
import torch
from torch import nn
import sklearn
from sklearn.model_selection import GroupShuffleSplit
from sklearn.ensemble import HistGradientBoostingRegressor

P=Path(__file__).resolve().parent;P.joinpath('results').mkdir(exist_ok=True)
torch.set_num_threads(4);torch.set_num_interop_threads(1)
d=np.load(P/'data.npz');X=d['X'].astype(np.float32);y=d['y'];groups=d['groups'];meta=json.loads((P/'data-meta.json').read_text())
outer,test=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=2026).split(X,y,groups))
train_rel,val_rel=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2027).split(X[outer],y[outer],groups[outer]));train,val=outer[train_rel],outer[val_rel]
assert not(set(groups[train])&set(groups[val]) or set(groups[train])&set(groups[test]) or set(groups[val])&set(groups[test]))

def metric(actual,pred):
 e=np.abs(actual-pred);return dict(log_mae=float(e.mean()),median_error_factor=float(np.exp(np.median(e))),within_2x=float((e<=np.log(2)).mean()),within_3x=float((e<=np.log(3)).mean()),p90_error_factor=float(np.exp(np.quantile(e,.9))))

class Net(nn.Module):
 def __init__(self,widths,dropout):
  super().__init__();layers=[];n=X.shape[1]
  for width in widths:layers.extend([nn.Linear(n,width),nn.SiLU(),nn.Dropout(dropout)]);n=width
  layers.append(nn.Linear(n,1));self.net=nn.Sequential(*layers);self.skip=nn.Linear(X.shape[1],1)
  nn.init.zeros_(self.skip.weight);nn.init.zeros_(self.skip.bias)
 def forward(self,x):return (self.net(x)+self.skip(x)).squeeze(-1)

configs=[dict(name='mlp_small',widths=[96,48],dropout=.05,lr=.001,wd=.003),dict(name='mlp_deep',widths=[128,96,48],dropout=.10,lr=.0008,wd=.01)]
mean=X[train].mean(0);std=X[train].std(0);std[std<1e-6]=1
ym=float(y[train].mean());ys=float(y[train].std())
Z=np.clip((X-mean)/std,-8,8).astype(np.float32);T=torch.from_numpy(Z);Y=torch.tensor((y-ym)/ys,dtype=torch.float32)
results={};models={};learning={}
start=time.time();print('START',json.dumps(dict(host=platform.node(),torch=torch.__version__,sklearn=sklearn.__version__,rows=len(X),features=X.shape[1],train=len(train),val=len(val),test=len(test),threads=4,device='cpu')),flush=True)
for config in configs:
 preds=[];nets=[];histories=[]
 for seed in (2026,2027,2028):
  torch.manual_seed(seed);np.random.seed(seed);random.seed(seed)
  net=Net(config['widths'],config['dropout']);optimizer=torch.optim.AdamW(net.parameters(),lr=config['lr'],weight_decay=config['wd'])
  scheduler=torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer,mode='min',factor=.5,patience=10,min_lr=1e-5)
  best=float('inf');best_state=None;best_epoch=0;history=[]
  train_idx=torch.tensor(train,dtype=torch.long)
  for epoch in range(1,301):
   net.train();order=train_idx[torch.randperm(len(train_idx))]
   total=0.
   for offset in range(0,len(order),512):
    batch=order[offset:offset+512];optimizer.zero_grad(set_to_none=True);loss=torch.nn.functional.smooth_l1_loss(net(T[batch]),Y[batch],beta=.25);loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),5);optimizer.step();total+=float(loss.detach())*len(batch)
   net.eval()
   with torch.no_grad():pv=net(T[val]).numpy()*ys+ym
   score=float(np.abs(pv-y[val]).mean());scheduler.step(score);history.append(dict(epoch=epoch,train_loss=total/len(train),validation_log_mae=score))
   if score<best-1e-4:best=score;best_state=copy.deepcopy(net.state_dict());best_epoch=epoch
   if epoch%50==0:print('EPOCH',config['name'],seed,epoch,round(score,5),'best',round(best,5),flush=True)
   if epoch-best_epoch>=35:break
  net.load_state_dict(best_state);net.eval()
  with torch.no_grad():pred=net(T).numpy()*ys+ym
  preds.append(pred);nets.append(net);histories.append(history)
  label=config['name']+'_'+str(seed);results[label]=dict(validation=metric(y[val],pred[val]),epochs=epoch,best_epoch=best_epoch,parameters=sum(p.numel() for p in net.parameters()))
  torch.save(dict(state_dict=net.state_dict(),config=config,mean=mean.tolist(),std=std.tolist(),y_mean=ym,y_std=ys),P/'results'/f'{label}.pt')
  print('MODEL_DONE',label,json.dumps(results[label]),flush=True)
 ensemble=np.mean(preds,axis=0);label=config['name']+'_ensemble';results[label]=dict(validation=metric(y[val],ensemble[val]),members=3);models[label]=(ensemble,nets,config);learning[config['name']]=histories
for loss in ('absolute_error','squared_error'):
 label='hgb_'+loss
 g=HistGradientBoostingRegressor(loss=loss,max_iter=500,max_leaf_nodes=23,min_samples_leaf=20,l2_regularization=10,learning_rate=.06,early_stopping=False,random_state=2026).fit(X[train],y[train])
 pred=g.predict(X);results[label]=dict(validation=metric(y[val],pred[val]));models[label]=(pred,g,None);print('MODEL_DONE',label,json.dumps(results[label]),flush=True)
# All selection is on validation. Test is opened only now; never used for choosing.
best=min(models,key=lambda label:results[label]['validation']['log_mae']);prediction,chosen,config=models[best]
for label,(pred,_,_) in models.items():results[label]['test']=metric(y[test],pred[test])
report=dict(status='COMPLETED',selected_on_validation=best,selection_metric='validation log-MAE; player groups disjoint; test not used in selection',results=results,selected_test=metric(y[test],prediction[test]),previous_frozen_benchmark=meta['current_attributes_baseline'],split_counts=dict(train_rows=len(train),val_rows=len(val),test_rows=len(test),train_players=len(set(groups[train])),val_players=len(set(groups[val])),test_players=len(set(groups[test]))),features=meta['features'],identity_or_season_features=False,device='cpu',threads=4,elapsed_seconds=time.time()-start,environment=dict(torch=torch.__version__,sklearn=sklearn.__version__,numpy=np.__version__,hostname=platform.node()),data_sha256=hashlib.sha256((P/'data.npz').read_bytes()).hexdigest(),limitations=['Only historical +1 prices are labels; scarcity and popularity remain unobserved confounders.','Not a measured match-performance or native animation model.','No production deployment was performed.'])
# Portable selected model: numeric-only inference without Torch/sklearn in the server.
export=dict(schema=1,features=meta['features'],price_unit='historical normalized EP at +1',input_clip=8,validation_report='training-report.json')
if isinstance(chosen,list):
 export.update(type='mlp_ensemble',x_mean=mean.tolist(),x_std=std.tolist(),y_mean=ym,y_std=ys,members=[])
 for net in chosen:
  layers=[]
  for layer in net.net:
   if isinstance(layer,nn.Linear):layers.append(dict(type='linear',weight=layer.weight.detach().tolist(),bias=layer.bias.detach().tolist()))
   elif isinstance(layer,nn.SiLU):layers.append(dict(type='silu'))
  export['members'].append(dict(layers=layers,skip_weight=net.skip.weight.detach().tolist()[0],skip_bias=float(net.skip.bias.detach()[0])))
else:
 export.update(type='hgb',baseline=float(chosen._baseline_prediction[0,0]),trees=[])
 for group in chosen._predictors:
  nodes=group[0].nodes;assert not nodes['is_categorical'].any()
  export['trees'].append([[int(n['feature_idx']),float(n['num_threshold']),int(n['left']),int(n['right']),float(n['value']),int(n['is_leaf'])] for n in nodes])
(P/'results/selected-model.json').write_text(json.dumps(export),encoding='utf8')
probes=[dict(attributes=X[i].tolist(),log_prediction=float(prediction[i])) for i in test[:100]]
(P/'results/inference-probes.json').write_text(json.dumps(probes),encoding='utf8')
(P/'results/training-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(P/'results/learning-curves.json').write_text(json.dumps(learning),encoding='utf8')
(P/'results/split-indices.json').write_text(json.dumps(dict(train=train.tolist(),validation=val.tolist(),test=test.tolist())),encoding='utf8')
print('COMPLETED',best,json.dumps(report['selected_test']),'elapsed',round(report['elapsed_seconds'],1),flush=True)
