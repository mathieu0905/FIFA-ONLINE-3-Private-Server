"""Uniform Korean quotes plus explicitly labelled gameplay-prior augmentation.

Synthetic labels are never used as real validation/test observations. All source
anchors and every generated row remain in the same player-group partition.
"""
from pathlib import Path
import ast,collections,hashlib,json,math,sqlite3,sys
P=Path(__file__).resolve().parent;R=P.parent;P.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'analysis-deps'))
import numpy as np

source=json.loads((R/'clean-training/regional-source.json').read_text('utf8'))
old=json.loads((R/'historical-data.json').read_text('utf8'));oldsplit=json.loads((R/'expanded-training/split-indices.json').read_text())
partition={old[i]['playerid']:k for k,ii in oldsplit.items() for i in ii}
previous=json.loads((R/'clean-training/encoder.json').read_text());fields=previous['raw_fields'];numeric=previous['numeric'];cat=list(previous['categorical_vocab']);maskfields=list(previous['trait_bits'])
schema=json.loads((R/'schema.json').read_text('utf8'))
def ovr(a):return sum(a[f]*v for f,v in schema['role_weights'][schema['position_roles'][a['preferredposition1']]].items())//100
def split(pid):
 if pid in partition:return partition[pid]
 v=int(hashlib.sha256(f'fo3-highend-20261107:{pid}'.encode()).hexdigest()[:8],16)%100
 return 'train' if v<60 else 'validation' if v<75 else 'test'
with sqlite3.connect('file:D:/fifaol3/releases/bulk-seasons-main-v1/fifadb.db.db2.before.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;native={r['spid']:dict(r) for r in db.execute('select * from players')};names={r['playerid']:r['full'] for r in db.execute('select * from nameschi')}
quotes={q['spid']:q for q in source['quotes']};real=[];removed=[]
for q in source['quotes']:
 spid=q['spid'];n=native.get(spid)
 if n is None or not q['prices'].get('kr',0)>0:continue
 if len(q['summary_attributes'])!=5 or any(n[f]!=v for f,v in q['summary_attributes'].items()):removed.append(dict(spid=spid,reason='native_public_summary_mismatch'));continue
 a={f:n[f] for f in fields}
 real.append(dict(spid=spid,playerid=n['playerid'],name=names.get(n['playerid'],q['name']),season=spid//1000000,attributes=a,price=q['prices']['kr'],region='kr',kind='real',partition=split(n['playerid']),ovr=ovr(a),source_url=q['source_url'],source_sha256=q['source_sha256']))
identical=collections.defaultdict(list)
for r in real:identical[(r['playerid'],)+tuple(r['attributes'][f] for f in fields)].append(r)
quarantined=[];bad=set()
for rr in identical.values():
 if len(rr)>1 and max(r['price'] for r in rr)>=10*min(r['price'] for r in rr):
  quarantined.append(dict(spids=[r['spid'] for r in rr],prices=[r['price'] for r in rr],ratio=max(r['price'] for r in rr)/min(r['price'] for r in rr)))
  bad.update(r['spid'] for r in rr)
real=[r for r in real if r['spid'] not in bad]
assert all(r['region']=='kr' and r['kind']=='real' for r in real)
missing_high=[]
for s in (30,93):
 expected={k for k in native if k//1000000==s};observed={r['spid'] for r in real if r['season']==s}
 missing_high.extend(native[k] for k in sorted(expected-observed))
 assert not (expected-set(quotes)),('High-end cards not observed in source',s,expected-set(quotes))

# Read actual current custom attributes, never alter live files or assets.
registry=json.loads(Path('D:/FO3ID/server/gamedata/custom_rosters.json').read_text('utf8'));custom_meta={r['fo3_spid']:r for r in registry['cards']}
with sqlite3.connect('file:D:/FO3ID/server/gamedata/fifadb.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;custom=[dict(r) for r in db.execute('select * from players where spid/1000000 in (19,84)')]
tree=ast.parse(Path('D:/FO3ID/server/http_config.py').read_text('utf8'))
assign={t.id:n.value for n in tree.body if isinstance(n,ast.Assign) for t in n.targets if isinstance(t,ast.Name)}
grade_price=ast.literal_eval(assign['GRADE_PRICE'].left);grade_boost=ast.literal_eval(assign['GRADE_BOOST'].left)
core=[f for f in numeric if f not in ('height','weight','weakfootabilitytypecode','skillmoves','attackingworkrate','defensiveworkrate')];assert len(core)==33
synthetic=[];unanchored=[]

def generate(part):
 pool=[r for r in real if r['partition']==part]
 by_player=collections.defaultdict(list)
 for r in pool:by_player[r['playerid']].append(r)
 scales={f:max(1.,float(np.std([r['attributes'][f] for r in pool]))) for f in numeric}
 def comparable(a):
  role=schema['position_roles'][a['preferredposition1']]
  family={'ST','CF','W'} if role in ('ST','CF','W') else {'WM','CM','AM','DM'} if role in ('WM','CM','AM','DM') else {role}
  peers=[r for r in pool if r['season'] in (30,93) and schema['position_roles'][r['attributes']['preferredposition1']] in family]
  if len(peers)<3:peers=[r for r in pool if r['ovr']>=78 and schema['position_roles'][r['attributes']['preferredposition1']] in family]
  assert peers,('No same-partition high-end comparables',part,role)
  peers.sort(key=lambda r:sum(((a[f]-r['attributes'][f])/scales[f])**2 for f in numeric))
  peers=peers[:12];logs=[math.log(r['price'])+.04*(ovr(a)-r['ovr']) for r in peers]
  return max(1,round(math.exp(float(np.median(logs))))),[r['spid'] for r in peers]
 for c in missing_high:
  if split(c['playerid'])!=part:continue
  a={f:c[f] for f in fields};price,anchors=comparable(a)
  synthetic.append(dict(spid=c['spid'],playerid=c['playerid'],name=names.get(c['playerid']),attributes=a,price=price,region='kr',kind='synthetic',partition=part,ovr=ovr(a),rule='missing_native_legend_KR_quote_same_partition_attribute_neighbor_median',grade=1,anchor_spids=anchors,anchor_price=price,anchor_partition=part,weight=.15))
 # At most two strong cards per player; provide both outfield and goalkeeper
 # examples without letting low-OVR mass-market cards set the high-end curve.
 selected=[]
 for pid,rr in by_player.items():
  candidates=[r for r in rr if r['ovr']>=(74 if r['attributes']['preferredposition1']==0 else 78) or r['season'] in (30,93)]
  candidates.sort(key=lambda r:(r['season']==30,r['season']==93,r['ovr'],r['price']),reverse=True);selected.extend(candidates[:2])
 selected.sort(key=lambda r:(r['season']==30,r['season']==93,r['attributes']['preferredposition1']==0,r['ovr']),reverse=True)
 # A fixed ceiling bounds synthetic influence; metadata preserves every anchor.
 selected=selected[:900]
 for r in selected:
  for g in (2,4,6,8):
   boost=grade_boost[g]-grade_boost[1];a=dict(r['attributes'])
   for f in core:a[f]+=boost
   synthetic.append(dict(spid=r['spid'],playerid=r['playerid'],name=r['name'],attributes=a,price=round(r['price']*grade_price[g]),region='kr',kind='synthetic',partition=part,ovr=ovr(a),rule='native_grade_attribute_boost_and_existing_price_multiplier',grade=g,anchor_spid=r['spid'],anchor_price=r['price'],anchor_partition=part,weight=.2))
 for c in custom:
  pid=c['playerid']
  if split(pid)!=part:continue
  rr=by_player.get(pid,[])
  a={f:c[f] for f in fields};s=c['spid']//1000000
  meta=custom_meta.get(c['spid'],{});template=meta.get('template_spid')
  # Moments inherit their explicit template; Nostalgia inherits the player's
  # strongest legendary quote, as required by the user's tier-equivalence rule.
  anchor=next((r for r in rr if r['spid']==template),None) if s==84 else None
  if anchor is None and rr:anchor=max(rr,key=lambda r:(r['season']==30,r['season']==93,r['season']==91,r['ovr'],r['price']))
  if anchor is None:
   anchor_price,anchor_spids=comparable(a);anchor_ovr=ovr(a);anchor_spid=None
   unanchored.append(dict(spid=c['spid'],partition=part,reason='no_same_player_real_KR_anchor_used_same_partition_neighbors',neighbor_spids=anchor_spids))
  else:anchor_price=anchor['price'];anchor_ovr=anchor['ovr'];anchor_spid=anchor['spid'];anchor_spids=[anchor_spid]
  if s==84:
   price=round(anchor_price*grade_price[8]);rule='user_moments_plus1_equivalent_to_corresponding_legend_plus8'
  else:
   # User's tier constraint: Nostalgia and UL remain comparable. Four percent
   # log premium per positional point is a disclosed prior, bounded to 0.5–2x.
   price=round(anchor_price*math.exp(max(-math.log(2),min(math.log(2),.04*(ovr(a)-anchor_ovr)))));rule='user_nostalgia_same_tier_as_best_same_player_legend_bounded_attribute_adjustment'
  synthetic.append(dict(spid=c['spid'],playerid=pid,name=meta.get('name_zh') or names.get(pid),attributes=a,price=price,region='kr',kind='synthetic',partition=part,ovr=ovr(a),rule=rule,grade=1,anchor_spid=anchor_spid,anchor_spids=anchor_spids,anchor_price=anchor_price,anchor_partition=part,weight=.5))

generate('train');generate('validation') # latter available only during final refit
assert all(r['partition']==r['anchor_partition'] for r in synthetic)
allrows=real+synthetic;train=[i for i,r in enumerate(allrows) if r['partition']=='train'];validation=[i for i,r in enumerate(allrows) if r['partition']=='validation' and r['kind']=='real'];test=[i for i,r in enumerate(allrows) if r['partition']=='test' and r['kind']=='real'];outer=[i for i,r in enumerate(allrows) if r['partition'] in ('train','validation')]
joint=collections.defaultdict(list)
for r in allrows:joint[(r['playerid'],)+tuple(r['attributes'][f] for f in fields)].append(r)
joint_conflicts=[rr for rr in joint.values() if len(rr)>1 and max(r['price'] for r in rr)>=10*min(r['price'] for r in rr)]
assert not joint_conflicts,'Synthesis must not reintroduce exact-input >=10x conflicts'
train_groups={allrows[i]['playerid'] for i in train};held_groups={allrows[i]['playerid'] for i in validation+test};assert not train_groups&held_groups
assert not {allrows[i]['playerid'] for i in outer}&{allrows[i]['playerid'] for i in test}
vocab={f:sorted({int(allrows[i]['attributes'][f]) for i in train}) for f in cat};bits={f:[b for b in range(32) if any((int(allrows[i]['attributes'][f])&0xffffffff)>>b&1 for i in train)] for f in maskfields}
encoded=numeric+[f'cat:{f}:{v}' for f in cat for v in vocab[f]]+[f'bit:{f}:{b}' for f in bits for b in bits[f]]
encoder=dict(previous,categorical_vocab=vocab,trait_bits=bits,encoded_features=encoded,vocabulary_fit='Real training and training-only synthetic rows; validation/test identities never fit vocabulary')
def encode(a):
 x=[a[f] for f in numeric]
 for token in encoded[len(numeric):]:
  kind,f,v=token.split(':');v=int(v);x.append(int(a[f]==v) if kind=='cat' else (int(a[f])&0xffffffff)>>v&1)
 return x
X=np.array([encode(r['attributes']) for r in allrows],dtype=np.float32);y=np.log([r['price'] for r in allrows]);groups=np.array([r['playerid'] for r in allrows]);is_real=np.array([r['kind']=='real' for r in allrows]);season=np.array([r.get('season',r['spid']//1000000) for r in allrows]);ratings=np.array([r['ovr'] for r in allrows]);gk=np.array([r['attributes']['preferredposition1']==0 for r in allrows])
weights=[]
for r in allrows:
 if r['kind']=='synthetic':w=r['weight']
 else:
  w=40. if r['season']==30 else 8. if r['season']==93 else 3. if r['ovr']>=80 else 1.
  if r['attributes']['preferredposition1']==0 and (r['season'] in (30,93,27,28) or r['ovr']>=80):w=max(w,15.)
 weights.append(w)
np.savez_compressed(P/'data.npz',X=X,y=y,groups=groups,is_real=is_real,weights=np.array(weights,dtype=np.float32),season=season,ovr=ratings,gk=gk,spids=np.array([r['spid'] for r in allrows]))
splits=dict(train=train,validation=validation,test=test,outer=outer,real_train=[i for i in train if is_real[i]],real_outer=[i for i in outer if is_real[i]])
(P/'split-indices.json').write_text(json.dumps(splits),'utf8');(P/'encoder.json').write_text(json.dumps(encoder,indent=2),'utf8');(P/'data-meta.json').write_text(json.dumps(dict(features=encoded,base_features=numeric,raw_fields=fields,rows=len(allrows),price_region='kr',real_rows=len(real),synthetic_rows=len(synthetic)),indent=2),'utf8')
(P/'dataset.json').write_text(json.dumps(allrows,ensure_ascii=False),'utf8');(P/'quarantine.json').write_text(json.dumps(dict(conflicts=quarantined,removed=removed,unanchored_custom=unanchored),ensure_ascii=False,indent=2),'utf8')
report=dict(status='PREPARED',price_region='kr',region_selection='Only inspected region with full native UL and WL coverage, including top legendary keepers; all real targets are untouched KR quotes, no region conversion.',real_rows=len(real),synthetic_rows=len(synthetic),counts_by_kind_partition=dict(collections.Counter(r['kind']+'_'+r['partition'] for r in allrows)),UL_real=[dict(spid=r['spid'],name=r['name'],price=r['price'],partition=r['partition']) for r in real if r['season']==30],WL_real_count=sum(r['season']==93 for r in real),real_gk=sum(r['attributes']['preferredposition1']==0 for r in real),top_real_gk=[dict(spid=r['spid'],name=r['name'],price=r['price'],partition=r['partition']) for r in sorted([r for r in real if r['attributes']['preferredposition1']==0],key=lambda r:-r['price'])[:12]],synthetic_rules=dict(collections.Counter(r['rule'] for r in synthetic)),synth_train_only_for_selection=True,synthetic_validation_only_for_final_refit=True,no_synthetic_test=True,group_overlap=0,raw_fields=len(fields),encoded_dimensions=len(encoded),native_grade_prices=list(grade_price),native_grade_boosts=list(grade_boost),quarantined_groups=len(quarantined),unanchored_custom=unanchored,source_sha256=hashlib.sha256((R/'clean-training/regional-source.json').read_bytes()).hexdigest(),synthetic_warning='Explicit game-design priors, not additional observed trades; improvement on these examples is constraint fitting, not external validation.',validation_selection_policy='Real validation only; score = overall log MAE + 0.5*high-end log MAE + 0.25*top-GK log MAE; high-end means UL/WL or OVR>=82, top GK means goalkeeper OVR>=80 or UL/WL.',production_changed=False)
report['region_selection']='KR has the best high-end coverage: all 5 native UL and 72 of 73 native WL quotes. All real targets are untouched KR quotes, with no region conversion.'
report['native_high_missing_quotes']=[dict(spid=c['spid'],name=names.get(c['playerid']),partition=split(c['playerid'])) for c in missing_high]
report['combined_exact_input_conflicts_at_least_10x']=len(joint_conflicts)
(P/'data-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8');(P/'encoding-probes.json').write_text(json.dumps([dict(raw=allrows[i]['attributes'],encoded=encode(allrows[i]['attributes'])) for i in test[:100]]),'utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
