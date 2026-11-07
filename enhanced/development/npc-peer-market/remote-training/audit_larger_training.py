"""After training, measure train-vs-validation gaps at the saved best checkpoints."""
from pathlib import Path
import ast,json
P=Path(__file__).resolve().parent
source=(P/'train_larger_gpu.py').read_text();prefix=source[:source.index('CONFIGS=[')]
exec(compile(prefix,str(P/'train_larger_gpu.py'),'exec'),globals())
report=json.loads((O/'training-report.json').read_text());audits={}
for config in report['configurations']:
 for seed in (2026,2027):
  label=config['name']+'_'+str(seed);checkpoint=torch.load(O/(label+'.pt'),map_location='cpu',weights_only=True)
  ACTIVE_CONFIG=checkpoint['config'];state=checkpoint['state_dict'];mean=state['mean'].numpy();std=state['std'].numpy()
  net=ValueNet('stars',mean,std,checkpoint['ym'],checkpoint['ys']).to(device);net.load_state_dict(state);net.eval()
  preds=[]
  with torch.no_grad():
   for off in range(0,len(X),1024):preds.append((net(T[off:off+1024])*net.ys+net.ym).cpu().numpy())
  pred=np.concatenate(preds);audits[label]=dict(train=metrics(y[train],pred[train]),validation=metrics(y[val],pred[val]),test=metrics(y[test],pred[test]),parameters=sum(p.numel() for p in net.parameters()))
  del net;torch.cuda.empty_cache();print('AUDIT',label,audits[label]['train']['log_mae'],audits[label]['validation']['log_mae'],flush=True)
(O/'overfit-audit.json').write_text(json.dumps(audits,indent=2))
