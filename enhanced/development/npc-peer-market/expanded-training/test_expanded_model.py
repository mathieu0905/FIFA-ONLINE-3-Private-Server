from pathlib import Path
import json,sys,math,argparse
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from expanded_value_model import ExpandedValueModel
parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,default=P/'results');args=parser.parse_args();D=args.results
m=ExpandedValueModel(D/'selected-model.json.gz');probes=json.loads((D/'inference-probes.json').read_text('utf8'));errors=[]
for probe in probes:
 assert m.encode(probe['raw'])==probe['encoded']
 if len(errors)<20:errors.append(abs(m.log_predict(probe['raw'])-probe['log_prediction']))
assert max(errors)<1e-4,max(errors)
r=probes[0]['raw'];assert m.predict(dict(r,name='A',spid=1,season=93))==m.predict(dict(r,name='B',spid=999,season=13))
# Unknown enum values have no arbitrary ordering; each becomes the same zero block.
a=dict(r,bodytypecode=999991);b=dict(r,bodytypecode=999992);assert m.encode(a)==m.encode(b)
assert 'bodytypecode' in m.diagnostics(a)['unknown_categories']
# A signed and unsigned view of the same UInt32 bitmask encode identically.
mask=int(r['trait1'])&0xffffffff
if mask>=2**31:assert m.encode(dict(r,trait1=mask))==m.encode(dict(r,trait1=mask-2**32))
# Explicit stable handling of malformed category/bitmask values.
for bad in (dict(r,trait1=1.5),dict(r,bodytypecode=2.5),dict(r,height=float('nan'))):
 try:m.predict(bad);raise AssertionError('Malformed input accepted')
 except ValueError:pass
matrix=[]
for weak in (2,3,4,5):
 values=[m.predict(dict(r,weakfootabilitytypecode=weak,skillmoves=sm)) for sm in (1,2,3,4)]
 assert values==sorted(values);matrix.append(values)
for col in range(4):assert [row[col] for row in matrix]==sorted(row[col] for row in matrix)
result=dict(passed=True,encoding_probes=len(probes),inference_probes=len(errors),max_log_error=max(errors),identity_season_ignored=True,unknown_categories_safe=True,malformed_input_rejected=True,star_monotone=True,production_changed=False)
(D/'local-verification.json').write_text(json.dumps(result,indent=2),'utf8');print(result)
