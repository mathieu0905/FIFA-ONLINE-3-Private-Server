from pathlib import Path
P=Path(__file__).resolve().parent;s=(P/'train_highend_gpu.py').read_text('utf8')
needle="net,p,info=fit('stars',seed,indices,val);info['validation']=cohort_metrics(val,p[val]);"
replacement="""
  if config['name']=='real_only_control':
   old=Path('/home/zhihao/fo3_value_training/run-20261107-highend-kr-v7/results')
   checkpoint=torch.load(old/('real_only_control_'+str(seed)+'.pt'),map_location=device,weights_only=False)
   assert checkpoint['features']==features,'Changed encoder invalidates control reuse'
   state=checkpoint['state_dict'];net=ValueNet('stars',state['mean'].cpu().numpy(),state['std'].cpu().numpy(),checkpoint['ym'],checkpoint['ys']).to(device);net.load_state_dict(state);net.eval()
   with torch.no_grad():p=(net(T)*net.ys+net.ym).cpu().numpy()
   info=json.loads((old/'training-report.json').read_text())['runs']['real_only_control_'+str(seed)]
  else:net,p,info=fit('stars',seed,indices,val)
  info['validation']=cohort_metrics(val,p[val]);"""
assert needle in s;s=s.replace(needle,replacement)
s=s.replace("model_policy='Fixed requested high-end augmentation; early stopping on real grouped validation only'","model_policy='Corrected Nostalgia anchor priority: UL then WL, not ordinary native template; real-control checkpoints reused unchanged; early stopping on real grouped validation only'")
(P/'train_highend_gpu.py').write_text(s,'utf8');compile(s,'train_highend_gpu.py','exec')
launch=(P/'launch_remote.sh').read_text('utf8').replace('run-20261107-highend-kr-v7','run-20261107-highend-kr-v7b')
(P/'launch_corrected.sh').write_bytes(launch.encode('utf8'));print('Prepared corrected augmentation; real-only control weights retained')
