from pathlib import Path
import sys,json,math
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from predict_attributes_value import AttributeValueModel
m=AttributeValueModel();probes=json.loads((R/'attributes-probes.json').read_text('utf8'))
errors=[abs(m.log_predict(p['attributes'])-p['log_prediction']) for p in probes];assert max(errors)<1e-9
r=probes[0]['attributes'];a=m.predict(dict(r,spid=1,season=93,name='A',playerid=1,price=10));b=m.predict(dict(r,spid=99999,season=12,name='B',playerid=999,price=99999999999));assert a==b
assert not set(m.model['features'])&{'spid','playerid','name','season','price','internationalrep','potential','ovr'}
try:m.predict(dict(r,height=float('nan')));raise AssertionError('NaN was accepted')
except ValueError:pass
try:m.predict({});raise AssertionError('Missing fields were accepted')
except ValueError:pass
# Hold all technical abilities fixed while varying physical inputs.
rows=json.loads((R/'historical-data.json').read_text('utf8'));sample=next(r for r in rows if r['spid']==91041236)
physical=[dict(height=h,weight=w,value=m.predict(dict(sample,height=h,weight=w))) for h,w in ((170,65),(180,75),(190,90),(195,95))]
assert len({p['value'] for p in physical})>1
result=dict(passed=True,portable_parity_checks=len(probes),max_log_error=max(errors),identity_season_price_invariance=True,missing_nan_rejected=True,same_abilities_physical_examples=physical,production_changed=False)
(R/'attributes-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8');print(json.dumps(result,ensure_ascii=False))
