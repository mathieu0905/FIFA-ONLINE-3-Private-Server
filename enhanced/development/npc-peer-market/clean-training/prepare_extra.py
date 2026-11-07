from pathlib import Path
import collections,hashlib,json,sqlite3,sys
P=Path(__file__).resolve().parent;R=P.parent;sys.path.insert(0,str(R/'analysis-deps'))
import numpy as np
source=json.loads((P/'regional-source.json').read_text('utf8'));old=json.loads((R/'historical-data.json').read_text('utf8'));oldids={r['spid'] for r in old}
oldsplit=json.loads((R/'expanded-training/split-indices.json').read_text());heldout={old[i]['playerid'] for i in oldsplit['test']}
encoder=json.loads((P/'encoder.json').read_text());audit=json.loads((P/'attribute-audit.json').read_text());rows=[];removed=[]
with sqlite3.connect(Path(audit['native_source']).as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;native={r['spid']:dict(r) for r in db.execute('select * from players')}
for q in source['quotes']:
 if q['spid'] in oldids or q['prices'].get('id',0)<=0:continue
 r=native.get(q['spid'])
 if r is None:removed.append(dict(spid=q['spid'],reason='not_in_native_client'));continue
 if len(q['summary_attributes'])!=5 or any(r[k]!=v for k,v in q['summary_attributes'].items()):removed.append(dict(spid=q['spid'],reason='native_public_summary_mismatch'));continue
 rows.append(dict(spid=r['spid'],playerid=r['playerid'],price=q['prices']['id'],refit_eligible=r['playerid'] not in heldout,raw={f:r[f] for f in encoder['raw_fields']},source_url=q['source_url'],source_sha256=q['source_sha256']))
def encode(r):
 a=r['raw'];x=[a[f] for f in encoder['numeric']]
 for feature in encoder['encoded_features'][len(encoder['numeric']):]:
  kind,f,n=feature.split(':');n=int(n);x.append(int(a[f]==n) if kind=='cat' else (int(a[f])&0xffffffff)>>n&1)
 return x
X=np.array([encode(r) for r in rows],dtype=np.float32);assert np.isfinite(X).all()
np.savez_compressed(P/'extra.npz',X=X,y=np.log([r['price'] for r in rows]),groups=np.array([r['playerid'] for r in rows]),spids=np.array([r['spid'] for r in rows]),refit_eligible=np.array([r['refit_eligible'] for r in rows],dtype=bool))
(P/'extra-data.json').write_text(json.dumps(rows,ensure_ascii=False),'utf8')
report=dict(status='AUDITED',native_extra_cards=len(rows),eligible_refit_rows=sum(r['refit_eligible'] for r in rows),original_test_player_extra_rows=sum(not r['refit_eligible'] for r in rows),excluded=removed,policy='Append only audited, native-client, raw-ID-price cards to final refit; all original test players remain excluded from training. Freeze validation-selected architecture, LR schedule, encoder and epochs; do not select by augmented test results.',raw_fields=len(encoder['raw_fields']),source_sha256=hashlib.sha256((P/'regional-source.json').read_bytes()).hexdigest(),categorical_oov={f:sum(r['raw'][f] not in vs for r in rows) for f,vs in encoder['categorical_vocab'].items()})
clean=json.loads((P/'clean-data.json').read_text('utf8'));groups=collections.defaultdict(list);fields=encoder['raw_fields']
for r in clean:groups[(r['playerid'],)+tuple(r[f] for f in fields)].append(r['price'])
for r in rows:groups[(r['playerid'],)+tuple(r['raw'][f] for f in fields)].append(r['price'])
conflicts=[prices for prices in groups.values() if len(prices)>1 and max(prices)>=10*min(prices)]
extra_train={tuple(r['raw'][f] for f in fields) for r in rows if r['refit_eligible']};test={tuple(r[f] for f in fields) for r in clean if r['split']=='test'}
assert not conflicts and not extra_train&test
report.update(combined_exact58_same_player_conflicts_at_least_10x=len(conflicts),extra_train_original_test_exact_feature_overlap=len(extra_train&test))
(P/'extra-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');print(json.dumps(report,ensure_ascii=False))
