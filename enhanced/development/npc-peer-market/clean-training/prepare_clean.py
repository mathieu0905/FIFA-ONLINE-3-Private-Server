"""Build a single-region dataset without modifying game databases or saves."""
from pathlib import Path
import collections,hashlib,json,math,sqlite3,sys
P=Path(__file__).resolve().parent;R=P.parent
sys.path.insert(0,str(R/'analysis-deps'))
import numpy as np

source=json.loads((P/'regional-source.json').read_text('utf8'))
audit=json.loads((P/'attribute-audit.json').read_text('utf8'))
assert audit['complete'],'Finish the planned attribute audit before training'
assert not any(r['status']=='FAILED' for r in audit['public_results']),'Resolve failed attribute audits first'
old=json.loads((R/'historical-data.json').read_text('utf8'))
old=[r for r in old if r['season'] not in (12,13,48,84) and r['height']>0 and r['weight']>0]
oldsplit=json.loads((R/'expanded-training/split-indices.json').read_text())
oldencoder=json.loads((R/'expanded-training/encoder.json').read_text())
oldgroups={}
for name,indices in oldsplit.items():
 for i in indices:
  pid=old[i]['playerid'];assert pid not in oldgroups or oldgroups[pid]==name;oldgroups[pid]=name
quotes={r['spid']:r for r in source['quotes']}
drift={r['spid'] for r in audit['native_drift']}
conflicts={r['spid'] for r in source['inconsistent_observations']}
public_mismatches={r['spid'] for r in audit['public_results'] if r['status']=='MISMATCH'}
rows=[];removed=[];summary_matches=0;summary_mismatches=[]
fields=oldencoder['raw_fields']
with sqlite3.connect(Path(audit['native_source']).as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;native={r['spid']:dict(r) for r in db.execute('select * from players')}
for i,r in enumerate(old):
 spid=r['spid'];q=quotes.get(spid);n=native.get(spid);reason=None
 if n is None:reason='no_pre_import_native_record'
 elif spid in drift:reason='locally_modified_attributes'
 elif spid in public_mismatches:reason='public_native_full_attribute_mismatch'
 elif q is None:reason='not_observed_in_fresh_collection'
 elif spid in conflicts:reason='conflicting_source_observations'
 else:
  delta={f:[n[f],v] for f,v in q['summary_attributes'].items() if n[f]!=v}
  if len(q['summary_attributes'])!=5:reason='incomplete_public_summary'
  elif delta:
   reason='public_native_summary_mismatch';summary_mismatches.append(dict(spid=spid,differences=delta))
  else:
   summary_matches+=1
   if not q['prices'].get('id',0)>0:reason='no_indonesia_quote'
 if reason:
  removed.append(dict(spid=spid,name=r['name'],reason=reason));continue
 clean=dict(r)
 # Explicit native season-specific key, never playerid-only joining.
 for f in fields:clean[f]=n[f]
 clean.update(price=q['prices']['id'],old_mixed_price=r['price'],price_region='id',source_url=q['source_url'],source_page_sha256=q['source_sha256'],retrieved_at=q['retrieved_at'],old_row_index=i,split=oldgroups[r['playerid']])
 rows.append(clean)
assert rows and len({r['spid'] for r in rows})==len(rows)
# A fixed, declared conflict gate, applied before any training: same player and
# all 58 gameplay inputs identical, but same-region native quotes differ >=10x.
# Keep an explicit quarantine rather than averaging away contradictory labels.
exact=collections.defaultdict(list)
for r in rows:exact[(r['playerid'],)+tuple(r[f] for f in fields)].append(r)
anomalies=[];quarantine=set()
for rs in exact.values():
 if len(rs)>1 and max(r['price'] for r in rs)>=10*min(r['price'] for r in rs):
  anomalies.append(dict(reason='same_player_identical_58_inputs_price_ratio_at_least_10',spids=[r['spid'] for r in rs],prices=[r['price'] for r in rs],ratio=max(r['price'] for r in rs)/min(r['price'] for r in rs)))
  quarantine.update(r['spid'] for r in rs)
for r in rows:
 if r['spid'] in quarantine:removed.append(dict(spid=r['spid'],name=r['name'],reason='identical_input_price_conflict_at_least_10x'))
rows=[r for r in rows if r['spid'] not in quarantine]
(P/'quarantined-anomalies.json').write_text(json.dumps(anomalies,ensure_ascii=False,indent=2),'utf8')
split={k:[i for i,r in enumerate(rows) if r['split']==k] for k in ('train','validation','test')}
assert all(split.values())
train=split['train'];base=oldencoder['numeric'];cat=oldencoder['categorical_vocab'];bits=oldencoder['trait_bits']
vocab={f:sorted({int(rows[i][f]) for i in train}) for f in cat}
flags={f:[b for b in range(32) if any((int(rows[i][f])&0xffffffff)>>b&1 for i in train)] for f in bits}
features=base+[f'cat:{f}:{v}' for f in cat for v in vocab[f]]+[f'bit:{f}:{b}' for f in bits for b in flags[f]]
encoder=dict(oldencoder,categorical_vocab=vocab,trait_bits=flags,encoded_features=features)
def encode(row,e):
 values=[row[f] for f in e['numeric']]
 for feature in e['encoded_features'][len(e['numeric']):]:
  kind,f,k=feature.split(':');k=int(k)
  values.append(int(row[f]==k) if kind=='cat' else (int(row[f])&0xffffffff)>>k&1)
 return values
X=np.array([encode(r,encoder) for r in rows],dtype=np.float32)
Xold=np.array([encode(r,oldencoder) for r in rows],dtype=np.float32)
y=np.log([r['price'] for r in rows]);mixed=np.log([r['old_mixed_price'] for r in rows]);groups=np.array([r['playerid'] for r in rows],dtype=np.int64)
assert np.isfinite(X).all() and np.isfinite(y).all()
for a,b in (('train','validation'),('train','test'),('validation','test')):assert not set(groups[split[a]])&set(groups[split[b]])
feature_groups=collections.defaultdict(list)
for i,r in enumerate(rows):feature_groups[tuple(r[f] for f in fields)].append(i)
cross_split_duplicates=[indices for indices in feature_groups.values() if len({rows[i]['split'] for i in indices})>1]
assert not cross_split_duplicates,'Exact-feature duplicates must not cross partitions'
conflicting=[dict(spids=[rows[i]['spid'] for i in ii],prices=[rows[i]['price'] for i in ii],ratio=max(rows[i]['price'] for i in ii)/min(rows[i]['price'] for i in ii)) for ii in feature_groups.values() if len(ii)>1 and max(rows[i]['price'] for i in ii)>4*min(rows[i]['price'] for i in ii)]
np.savez_compressed(P/'data.npz',X=X,X_old_encoder=Xold,y=y,y_mixed=mixed,groups=groups,spids=np.array([r['spid'] for r in rows],dtype=np.int64))
(P/'encoder.json').write_text(json.dumps(encoder,ensure_ascii=False,indent=2),'utf8')
(P/'split-indices.json').write_text(json.dumps(split),'utf8')
(P/'clean-data.json').write_text(json.dumps(rows,ensure_ascii=False),'utf8')
(P/'removed-rows.json').write_text(json.dumps(removed,ensure_ascii=False,indent=2),'utf8')
meta=dict(features=features,base_features=base,raw_fields=fields,rows=len(rows),encoded_dimensions=len(features),price_unit='Unconverted historical Indonesia EP, source default card/level settings',source_sha256=hashlib.sha256((P/'regional-source.json').read_bytes()).hexdigest())
(P/'data-meta.json').write_text(json.dumps(meta,indent=2),'utf8')
report=dict(status='CLEANED',price_region='id',region_chosen_before_model_training=True,region_selection_reason='Project uses Indonesia; retain native quotes and discard missing instead of applying global exchange factors',fallback_or_imputed_prices=0,original_rows=len(old),kept_rows=len(rows),removed_counts=dict(collections.Counter(r['reason'] for r in removed)),split_counts={k:len(v) for k,v in split.items()},same_original_player_split=True,player_overlap=0,cross_split_exact_feature_duplicates=0,raw_fields=len(fields),encoded_dimensions=len(features),source_coverage=source['coverage'],source_pages=len(source['pages']),source_saturated_leaf_queries=source['saturated_leaf_queries'],source_quote_timestamp_available=False,source_retrieval_range=[min(p['retrieved_at'] for p in source['pages']),max(p['retrieved_at'] for p in source['pages'])],native_attribute_matches=audit['native_58_field_matches'],native_modified_rows=audit['native_drift'],public_33_field_sample_counts=dict(collections.Counter(r['status'] for r in audit['public_results'])),five_field_listing_matches=summary_matches,five_field_listing_mismatches=summary_mismatches,exact_input_conflicts_over4x=conflicting,quarantined_exact_conflict_groups=len(anomalies),conflict_threshold_declared_before_training=10,no_global_price_outlier_filter=True,cleaning_policy='Exclude missing native/ID quotes, local attribute edits, public/native mismatches and inconsistent page observations; quarantine identical-58-input/same-player >=10x same-region price conflicts. Do not delete samples on prediction error, absolute high price or test outcome.',limitations=['The public historical site exposes no individual quote date, liquidity or completed-trade proof.','Native-client and website agreement excludes observed import/key errors, not every possible error in original source.','Full 33-stat public verification is stratified sampling; five public summary stats and all 58 native training inputs are checked on every retained card.','Dataset universe is the former positive-price historical cohort; source coverage is reported separately.'],production_changed=False)
legacy_sources=collections.Counter();legacy_reconstruction_mismatches=0
for r in old:
 q=quotes.get(r['spid'])
 if not q:legacy_sources['not_observed']+=1;continue
 for region,scale in [('id',1.),('sg',1.267),('th',1.538),('vn',1.408),('kr',.595)]:
  if q['prices'].get(region,0)>0:
   legacy_sources[region]+=1
   legacy_reconstruction_mismatches+=round(q['prices'][region]*scale)!=r['price']
   break
 else:legacy_sources['no_quote_any_region']+=1
report.update(legacy_region_reconstruction_from_fresh_quotes=dict(legacy_sources),legacy_reconstruction_mismatches=legacy_reconstruction_mismatches,retained_original_label_unchanged=sum(r['price']==r['old_mixed_price'] for r in rows),historical_cohort_observed=source['historical_cohort_observed'],historical_cohort_missing=len(source['historical_cohort_missing']))
(P/'cleaning-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
(P/'encoding-probes.json').write_text(json.dumps([dict(raw={f:rows[i][f] for f in fields},encoded=encode(rows[i],encoder)) for i in split['test'][:100]]),'utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('limitations','source_saturated_leaf_queries','five_field_listing_mismatches')},ensure_ascii=False,indent=2))
