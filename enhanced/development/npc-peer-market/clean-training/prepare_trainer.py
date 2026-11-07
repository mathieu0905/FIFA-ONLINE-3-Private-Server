from pathlib import Path
P=Path(__file__).resolve().parent
s=(P.parent/'expanded-training/train_expanded_numeric_scaling.py').read_text('utf-8-sig')
# Reuse prior training procedure and all 58 fields; select architecture on validation.
s=s.replace(" dict(name='full_big',widths=[1024,1024,512,256],dropout=.25,weight_decay=.03,lr=.0003,max_epochs=1000),\n",'')
s=s.replace("price_unit='historical normalized EP at +1'","price_unit='historical Indonesia EP at source default +1'")
marker="start=time.time();print('EXPANDED_START'"
pos=s.index(marker)
baseline='''
# The old model never trained on these player test groups. Evaluate it against
# the exact same freshly collected ID labels, rather than comparing headline
# metrics from different target definitions or different samples.
OLD=Path('/home/zhihao/fo3_value_training/run-20261107-full-features-v5b/results')
old_input=torch.tensor(d['X_old_encoder'],device=device)
old_outputs=[]
for seed in (2026,2027):
 checkpoint=torch.load(OLD/('selected_'+str(seed)+'.pt'),map_location=device,weights_only=False)
 state=checkpoint['state_dict'];z=torch.clamp((old_input-state['mean'])/state['std'],-8,8);h=z[:,state['columns']];base=h
 linear_indices=sorted(int(k.split('.')[1]) for k in state if k.startswith('net.') and k.endswith('.weight'))
 with torch.no_grad():
  for j,k in enumerate(linear_indices):
   h=F.linear(h,state['net.'+str(k)+'.weight'],state['net.'+str(k)+'.bias'])
   if j<len(linear_indices)-1:h=F.silu(h)
  value=h.squeeze(-1)+F.linear(base,state['skip.weight'],state['skip.bias']).squeeze(-1)
  wf=old_input[:,stars[0]];sm=old_input[:,stars[1]];w=F.softplus(state['star_raw'])
  a=torch.stack([sum((wf>=threshold).float()*w[0,j] for j,threshold in enumerate((2,3,4,5,6))),sum((sm>=threshold).float()*w[1,j] for j,threshold in enumerate((1,2,3,4,5)))],dim=1)
  value=value+(a*torch.sigmoid(F.linear(base,state['star_gate.weight'],state['star_gate.bias']))).sum(1)
  old_outputs.append((value*checkpoint['ys']+checkpoint['ym']).cpu().numpy())
old_prediction=np.mean(old_outputs,axis=0)
old_metrics=metrics(y[test],old_prediction[test]);np.save(O/'old_model_common_test_predictions.npy',old_prediction[test])
print('OLD_MODEL_ON_SAME_ID_TEST',json.dumps(old_metrics),flush=True)
'''
s=s[:pos]+baseline+'\n'+s[pos:]
s=s.replace("'production_changed=False'","'production_changed=False'")
needle="(O/'training-report.json').write_text"
pos=s.index(needle)
s=s[:pos]+"report.update(price_region='id',fallback_prices=0,old_model_on_same_test=old_metrics,comparison_policy='Same player-held-out test cards and same raw Indonesia quotes; old refit model weights held fixed',cleaning_report=json.loads((P/'cleaning-report.json').read_text()),label_timestamp_limit='Public source has no per-quote timestamp; collection time does not establish quote freshness')\nnp.savez_compressed(O/'test-predictions.npz',spids=d['spids'][test],y=y[test],new=final[test],old=old_prediction[test])\n"+s[pos:]
(P/'train_clean_gpu.py').write_text(s,'utf8');compile(s,'train_clean_gpu.py','exec')
print('Prepared cleaned single-region trainer; original player split and fixed old-model benchmark retained')
