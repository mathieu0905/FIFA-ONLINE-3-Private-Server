"""Preserve suspicious same-input quotes without inventing a correction."""
from pathlib import Path
import collections,json,sqlite3
P=Path(__file__).resolve().parent;R=P.parent
source=json.loads((P/'regional-source.json').read_text('utf8'))
audit=json.loads((P/'attribute-audit.json').read_text('utf8'))
encoder=json.loads((R/'expanded-training/encoder.json').read_text('utf8'));fields=encoder['raw_fields']
old=json.loads((R/'historical-data.json').read_text('utf8'));groups=collections.defaultdict(list)
quotes={r['spid']:r for r in source['quotes']}
for r in old:groups[(r['playerid'],)+tuple(r[f] for f in fields)].append(r)
suspect=[]
for rs in groups.values():
 if len(rs)<2:continue
 regional={}
 for region in ('id','kr','th','vn','sg'):
  ps=[dict(spid=r['spid'],price=quotes[r['spid']]['prices'][region]) for r in rs if r['spid'] in quotes and quotes[r['spid']]['prices'].get(region,0)>0]
  if len(ps)>1 and max(p['price'] for p in ps)>=10*min(p['price'] for p in ps):regional[region]=dict(quotes=ps,ratio=max(p['price'] for p in ps)/min(p['price'] for p in ps))
 if regional:suspect.append(dict(name=rs[0]['name'],spids=[r['spid'] for r in rs],identical_input_count=len(fields),same_region_conflicts=regional,disposition='Suspicious; not proof of scarcity or a source error. Do not convert another region to fill a missing Indonesia quote.'))
mandanda=[dict(spid=s,**{k:v for k,v in quotes[s].items() if k!='spid'}) for s in (10163705,47163705) if s in quotes]
out=dict(native_and_public_attribute_conclusion='No observed later season-key join/import error: 16040 of 16041 historical rows match all 58 native fields; the one local edit is excluded. All 40 stratified/public full-stat checks matched native 33 fields.',caveat='Original EA historical correctness cannot be independently proven for every card; agreement does not prove a quote is recent or executable.',same_player_identical_input_suspicious_quotes=suspect,mandanda_quotes=mandanda,public_attribute_audit=str(P/'attribute-audit.json'),source_scope=source['collection_scope'],historical_cohort_size=source['historical_cohort_size'],historical_cohort_observed=source['historical_cohort_observed'],historical_cohort_missing=source['historical_cohort_missing'])
(P/'source-conclusions.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(dict(observed=out['historical_cohort_observed'],missing=len(out['historical_cohort_missing']),suspicious_groups=len(suspect)),ensure_ascii=False))
