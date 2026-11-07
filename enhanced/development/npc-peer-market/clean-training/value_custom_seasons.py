"""Read-only official-card valuation using the verified, cleaned model."""
from pathlib import Path
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4');os.environ.setdefault('OMP_NUM_THREADS','4')
import hashlib,json,math,sqlite3,sys
P=Path(__file__).resolve().parent;R=P.parent;sys.path[:0]=[str(R/'analysis-deps'),str(R/'expanded-training')]
import numpy as np
from expanded_value_model import ExpandedValueModel
MODEL=P/'results/final/selected-model.json.gz';model=ExpandedValueModel(MODEL);m=model.model
schema=json.loads((R/'schema.json').read_text('utf8'));registry=json.loads(Path('D:/FO3ID/server/gamedata/custom_rosters.json').read_text('utf8'));labels={19:'怀旧神兽',84:'传奇时刻',30:'终极传奇'}
metadata={c['fo3_spid']:c for c in registry['cards']};data=json.loads((P/'final-clean-data.json').read_text('utf8'));training=[r['attributes'] for r in data if r['final_partition']=='refit_train'];ranges={f:[min(r[f] for r in training),max(r[f] for r in training)] for f in m['encoder']['numeric']}
with sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;names={r['playerid']:dict(r) for r in db.execute('select * from nameschi')};rows=[dict(r) for r in db.execute('select * from players where spid/1000000 in (19,84,30) order by spid')]
X=np.array([model.encode(r) for r in rows],dtype=np.float64);preds=[]
for member in m['members']:
 z=np.clip((X-np.array(member['mean']))/np.array(member['std']),-m['input_clip'],m['input_clip']);base=z[:,member['columns']];h=base
 for layer in member['layers']:
  if layer['type']=='linear':h=h@np.array(layer['weight']).T+np.array(layer['bias'])
  else:h=h/(1+np.exp(-np.clip(h,-700,700)))
 value=h[:,0]+base@np.array(member['skip_weight'])+member['skip_bias'];w=np.log1p(np.exp(np.array(member['star_raw'])));amount=np.zeros((len(rows),2))
 for j,thresholds in enumerate(((2,3,4,5,6),(1,2,3,4,5))):
  for k,threshold in enumerate(thresholds):amount[:,j]+=(X[:,m['star_indices'][j]]>=threshold)*w[j,k]
 gates=1/(1+np.exp(-np.clip(base@np.array(member['star_gate_weight']).T+np.array(member['star_gate_bias']),-700,700)));value+=(amount*gates).sum(1)
 preds.append(value*member['y_std']+member['y_mean'])
prediction=np.mean(preds,axis=0)
probes=[0,len(rows)//2,len(rows)-1];parity=max(abs(float(prediction[i])-model.log_predict(rows[i])) for i in probes);assert parity<1e-6,parity
out=[]
for r,logvalue in zip(rows,prediction):
 s=r['spid']//1000000;n=names.get(r['playerid'],{});meta=metadata.get(r['spid'],{});role=schema['position_roles'][r['preferredposition1']];ovr=sum(r[f]*v for f,v in schema['role_weights'][role].items())//100
 price=max(1,round(math.exp(float(logvalue))));diag=model.diagnostics(r)
 out.append(dict(spid=r['spid'],playerid=r['playerid'],season_id=s,season=labels[s],name=meta.get('name_zh') or n.get('full') or n.get('short') or str(r['playerid']),name_en=meta.get('name_en') or n.get('full_eng'),position_role=role,position_ovr=ovr,database_overall=r['overallrating'],height=r['height'],weight=r['weight'],weak_foot=r['weakfootabilitytypecode'],skill_moves=r['skillmoves'],predicted_historical_id_ep=price,estimated_game_ep=max(1,price//1000),log_prediction=float(logvalue),numeric_outside_training={f:dict(value=r[f],training_range=ranges[f]) for f in ranges if not ranges[f][0]<=r[f]<=ranges[f][1]},encoding_diagnostics=diag))
out.sort(key=lambda r:(r['season_id'],-r['estimated_game_ep']))
train_ovrs=[sum(a[f]*v for f,v in schema['role_weights'][schema['position_roles'][a['preferredposition1']]].items())//100 for a in training]
raw_by_spid={r['spid']:{f:r[f] for f in m['features']} for r in rows}
for r in out:r['raw_attributes']=raw_by_spid[r['spid']]
report=dict(status='COMPUTED_READ_ONLY',model_sha256=hashlib.sha256(MODEL.read_bytes()).hexdigest(),model_path=str(MODEL),raw_input_fields=len(m['features']),training_position_ovr_range=[min(train_ovrs),max(train_ovrs)],source='Current official server gamedata/fifadb.sqlite, keyed by spid; read-only connection',grade='Single-card base value; no enhancement multiplier or scarcity/season identity premium',unit='Model native unit is historical Indonesia EP. estimated_game_ep uses existing NPC conversion floor(raw EP/1000), not a newly fitted exchange rate.',batch_standard_inference_parity_max_log_error=parity,season_counts={labels[s]:sum(r['season_id']==s for r in out) for s in labels},rows=out,production_changed=False)
(P/'custom-season-values.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
def fmt(x):return f'{x/1000000000000:.2f}万亿' if x>=1000000000000 else f'{x/100000000:.2f}亿' if x>=100000000 else f'{x/10000:.2f}万' if x>=10000 else f'{x:,}'
lines=['使用清洗后58项属性模型，读取当前正式库，只读计算；未修改市场定价。','', '金额列按现有NPC口径：模型原始印尼历史EP ÷ 1000，取整。仅单卡基础值，不含强化倍率或赛季稀缺溢价。','', '| 赛季 | 球员 | SPID | 位置能力 | 游戏口径EP估值 | 原始历史EP估值 | 超出训练范围的数值字段数 |','|---|---|---:|---:|---:|---:|---:|']
for r in out:lines.append(f"| {r['season']} | {r['name']} | {r['spid']} | {r['position_role']} {r['position_ovr']} | {fmt(r['estimated_game_ep'])} | {fmt(r['predicted_historical_id_ep'])} | {len(r['numeric_outside_training'])} |")
lines+=['','自定义赛季或高能力卡可能超出历史训练分布，表中为模型直接输出，不能等同于可靠成交价。完整逐卡超范围字段及未知类别见custom-season-values.json。']
(P/'三个赛季估值.md').write_text('\n'.join(lines),'utf8')
compare=['以下是模型直接输出，按当前NPC的历史EP÷1000换算为游戏EP；仅单卡基础值，不含强化倍率。并非建议成交价。','', '| 球员 | 怀旧神兽 | 传奇时刻 | 终极传奇 |','|---|---:|---:|---:|']
for pid,name in [(1625,'亨利'),(28130,'罗纳尔迪尼奥'),(31432,'德罗巴'),(49369,'托雷斯'),(138449,'卡卡'),(37576,'罗纳尔多'),(190042,'马拉多纳'),(238380,'雅辛'),(214100,'古利特')]:
 values=[]
 for s in (19,84,30):
  found=next((r for r in out if r['playerid']==pid and r['season_id']==s),None);values.append(fmt(found['estimated_game_ep']) if found else '—')
 compare.append('| '+name+' | '+' | '.join(values)+' |')
compare+=['',f'训练数据位置加权能力范围为{min(train_ovrs)}–{max(train_ovrs)}。当前怀旧、传奇时刻、终极传奇的样本全部至少有一项数值超出训练范围，传奇时刻尤为明显，因此高数值卡出现估值爆炸与异常排序。已校验批量与标准推理一致，未手工封顶或改写预测结果，也未改正式市场价格。','', '全部216张卡见三个赛季估值.md；原始58字段与模型诊断见custom-season-values.json。']
(P/'代表卡估值对照.md').write_text('\n'.join(compare),'utf8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False,indent=2))
for season in labels:
 rs=[r for r in out if r['season_id']==season];print('SEASON',labels[season]);print(json.dumps([{k:r[k] for k in ('spid','name','position_ovr','estimated_game_ep','predicted_historical_id_ep')} for r in rs[:12]],ensure_ascii=False))
