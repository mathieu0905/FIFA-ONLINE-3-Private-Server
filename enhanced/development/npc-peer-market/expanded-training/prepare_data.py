from pathlib import Path
import json,sys,collections,hashlib
R=Path('D:/fifaol3/npc-peer-market');O=R/'expanded-training';sys.path.insert(0,str(R/'analysis-deps'))
import numpy as np
rows=json.loads((R/'historical-data.json').read_text('utf8'));rows=[r for r in rows if r['season'] not in (12,13,48,84) and r['height']>0 and r['weight']>0]
base=json.loads((R/'attributes-value-model.json').read_text('utf8'))['features'];split=json.loads((R/'remote-training/cpu-results/split-indices.json').read_text('utf8'));train=split['train']
cat=['preferredposition1','preferredposition2','preferredposition3','preferredposition4','preferredfoot','bodytypecode','runningcode1','runningcode2','finishingcode1','finishingcode2','animpenaltieskickstylecode','animpenaltiesmotionstylecode','animpenaltiesstartposcode','animfreekickstartposcode','gkkickstyle','gksavetype','perfconsistencytype']
vocabs={f:sorted({int(rows[i][f]) for i in train}) for f in cat};bits={f:[b for b in range(32) if any((int(rows[i][f])&0xffffffff)>>b&1 for i in train)] for f in ('trait1','trait2')}
features=base+[f'cat:{f}:{v}' for f in cat for v in vocabs[f]]+[f'bit:{f}:{b}' for f in bits for b in bits[f]]
def encode(r):return [r[f] for f in base]+[int(int(r[f])==v) for f in cat for v in vocabs[f]]+[(int(r[f])&0xffffffff)>>b&1 for f in bits for b in bits[f]]
X=np.array([encode(r) for r in rows],dtype=np.float32);Xbase=np.array([[r[f] for f in base] for r in rows],dtype=np.float32);y=np.log(np.array([r['price'] for r in rows],dtype=np.float64));groups=np.array([r['playerid'] for r in rows],dtype=np.int64)
old=np.load(R/'remote-training/data.npz');assert np.array_equal(old['X'],Xbase) and np.array_equal(old['groups'],groups) and np.array_equal(old['y'],y)
np.savez_compressed(O/'data.npz',X=X,X_base=Xbase,y=y,groups=groups)
schema=dict(schema=1,numeric=base,categorical_vocab=vocabs,trait_bits=bits,raw_fields=base+cat+list(bits),encoded_features=features,unknown_category='all-zero one-hot block; report OOV',unknown_trait_bits='ignored and reported, never assigned an invented trait meaning',vocabulary_fit='train player groups only',identity_and_season_excluded=True)
(O/'encoder.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2),'utf8');(O/'split-indices.json').write_text(json.dumps(split),'utf8')
meta=dict(features=features,raw_fields=schema['raw_fields'],base_features=base,rows=len(rows),encoded_dimensions=len(features),categorical_fields=len(cat),trait_flags=sum(map(len,bits.values())),source_sha256=hashlib.sha256((R/'historical-data.json').read_bytes()).hexdigest())
(O/'data-meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),'utf8')
audit=dict(rows=len(rows),raw_fields=len(schema['raw_fields']),encoded_features=len(features),numeric=len(base),categorical={f:dict(categories=len(vocabs[f]),validation_oov=sum(int(rows[i][f]) not in vocabs[f] for i in split['validation']),test_oov=sum(int(rows[i][f]) not in vocabs[f] for i in split['test'])) for f in cat},trait_bit_counts={f:len(bs) for f,bs in bits.items()},missing_values=int(np.isnan(X).sum()),old_39_input_values_exact=True,same_targets_and_groups=True)
(O/'encoding-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),'utf8');print(json.dumps(audit,ensure_ascii=False))
# Probe raw-to-encoded parity without transporting game saves or manager assets.
(O/'encoding-probes.json').write_text(json.dumps([dict(raw={f:rows[i][f] for f in schema['raw_fields']},encoded=encode(rows[i])) for i in split['test'][:100]]),'utf8')
