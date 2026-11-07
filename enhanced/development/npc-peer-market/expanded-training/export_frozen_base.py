"""Export validation-selected old numeric network for a frozen residual experiment."""
from pathlib import Path
import json,gzip
OLD=Path('/home/zhihao/fo3_value_training/run-20261107-large-v4');HERE=Path(__file__).resolve().parent
source=(OLD/'train_larger_gpu.py').read_text();scope={'__file__':str(OLD/'train_larger_gpu.py')};exec(compile(source[:source.index('CONFIGS=[')],str(OLD/'train_larger_gpu.py'),'exec'),scope)
torch=scope['torch'];np=scope['np'];ValueNet=scope['ValueNet'];T=scope['T'];X=scope['X'];features=scope['features'];stars=scope['stars'];nonstar=scope['nonstar'];device=scope['device'];nets=[];preds=[]
for seed in (2026,2027):
 checkpoint=torch.load(OLD/'results'/('large_long_'+str(seed)+'.pt'),map_location='cpu',weights_only=True);scope['ACTIVE_CONFIG']=checkpoint['config'];state=checkpoint['state_dict']
 net=ValueNet('stars',state['mean'].numpy(),state['std'].numpy(),checkpoint['ym'],checkpoint['ys']).to(device);net.load_state_dict(state);net.eval();nets.append(net)
 with torch.no_grad():preds.append((net(T)*net.ys+net.ym).cpu().numpy())
np.savez_compressed(HERE/'frozen-base-predictions.npz',log_prediction=np.mean(preds,axis=0))
export=dict(schema=2,type='gpu_attribute_ensemble',kind='stars',features=features,input_clip=8,star_indices=stars,nonstar_indices=nonstar,members=[],price_unit='historical normalized EP at +1')
for net in nets:
 layers=[]
 for layer in net.net:
  if isinstance(layer,scope['nn'].Linear):layers.append(dict(type='linear',weight=layer.weight.detach().cpu().tolist(),bias=layer.bias.detach().cpu().tolist()))
  elif isinstance(layer,scope['nn'].SiLU):layers.append(dict(type='silu'))
 export['members'].append(dict(mean=net.mean.cpu().tolist(),std=net.std.cpu().tolist(),y_mean=net.ym,y_std=net.ys,columns=net.columns.cpu().tolist(),layers=layers,skip_weight=net.skip.weight.detach().cpu().tolist()[0],skip_bias=float(net.skip.bias.detach().cpu()[0]),star_raw=net.star_raw.detach().cpu().tolist(),star_gate_weight=net.star_gate.weight.detach().cpu().tolist(),star_gate_bias=net.star_gate.bias.detach().cpu().tolist()))
with gzip.open(HERE/'frozen-base-model.json.gz','wt',encoding='utf8') as file:json.dump(export,file)
print('FROZEN_BASE_READY',len(X),flush=True)
