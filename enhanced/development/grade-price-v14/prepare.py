"""Build independent enhancement multipliers; base prices and attributes stay exact."""
from pathlib import Path
from contextlib import closing
from fractions import Fraction as F
import copy,gzip,hashlib,importlib.util,json,math,sqlite3,sys,urllib.request
P=Path(__file__).resolve().parent;S=Path('D:/FO3ID/server')
sys.path.insert(0,str(P));sys.path.append(str(S))
from fair_value_model import canonical
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text('utf8'))
def save(name,v):(P/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf8')
def main():
 baseline={str(p):sha(p) for p in [S/'fair_value_store.py',S/'npc_exchange.py',S/'gamedata/fair-value-v13-model.json',S/'gamedata/fair-value-v13-catalogue.json.gz',S/'gamedata/enhancement_rates.json',S/'enhancement_progression.py']}
 with urllib.request.urlopen('http://127.0.0.1:8088/api/enhancement',timeout=10) as r:settings=json.load(r)
 spec=importlib.util.spec_from_file_location('original_cost_rules',S/'enhancement_progression.py');rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
 values=[F(0),F(1)];choices=[]
 for grade in range(1,20):
  best=None;choice=None
  for material in range(1,grade+1):
   probability=F(str(settings['rates'][str(grade)]))/100*F(str(rules.material_factor(grade,material)))
   if probability<=0:continue
   for protected in [False,True]:
    failed=grade if protected else rules.failure_grade(grade);fee=values[grade]*(F(2,5) if protected else F(1,50));loss=values[grade]-values[failed]
    cost=values[grade]+((probability*values[material] if protected else values[material])+fee+(1-probability)*loss)/probability
    if best is None or cost<best:best=cost;choice=dict(material=material,protected=protected,probability=float(probability))
  if best is None:raise ValueError('An enhancement step is unreachable; cannot invent its cost curve')
  values.append(best);choices.append(choice)
 maximum=5000.;anchor=float(values[5]);power=math.log(maximum/anchor)/math.log(float(values[20]/values[5]));multipliers=[0.]+[float(values[g]) if g<=5 else anchor*float(values[g]/values[5])**power for g in range(1,21)];multipliers[-1]=maximum
 assert all(b>a for a,b in zip(multipliers,multipliers[1:]))
 old=read(S/'gamedata/fair-value-v13-model.json');cfg=copy.deepcopy(old);cfg.update(revision='base-times-enhancement-v14',previous_revision=old['revision']);cfg['enhancement_price_curve']=dict(schema=1,kind='base_times_independent_enhancement_multiplier',multipliers=multipliers,raw_normalized_expected_cost=[float(v) for v in values],selected_materials=choices,unchanged_low_grades='1..5 exact normalized original expected cost',high_grade_compression=dict(anchor_grade=5,power=power,maximum_grade20_multiplier=maximum),source_rates=settings['rates'],source_revision=settings['revision'],source_cost_rules_sha256=baseline[str(S/'enhancement_progression.py')],policy='fixed publication curve; success rates remain independently configurable, no ability/XP/team-colour change')
 with gzip.open(S/'gamedata/fair-value-v13-catalogue.json.gz','rt',encoding='utf8') as f:oldcat=json.load(f)
 cat=copy.deepcopy(oldcat);cat.update(revision=cfg['revision'],expected_previous_revision=old['revision'],model_sha256=hashlib.sha256(canonical(cfg)).hexdigest())
 # Identical economics/floors and preserved market factors mean all +1 prices are unchanged.
 assert cat['rows']==oldcat['rows'];peak=max(round(r['economic_value']*1.15)+r['strict_floor_ep'] for r in cat['rows']);quote_ceiling=(2**53-1)//3;assert peak*maximum<quote_ceiling,'Enhancement curve cannot fit the native safe quote range'
 save('model.json',cfg)
 with gzip.open(P/'catalogue.json.gz','wt',encoding='utf8') as f:json.dump(cat,f,ensure_ascii=False,separators=(',',':'))
 source=(S/'fair_value_store.py').read_text('utf8');marker="  if grade==0:return 0\n";assert source.count(marker)==1
 source=source.replace(marker,marker+"  curve=self.model.get('enhancement_price_curve')\n  if curve is not None:return round(self.value(sid,factor)*curve['multipliers'][grade])\n")
 compile(source,'fair_value_store.py','exec');(P/'fair_value_store.py').write_text(source,'utf8')
 source=(S/'npc_exchange.py').read_text('utf8');marker="        hc.PROGRESSION20['value_model']=dict(kind='fair_strength_curve',market_base='profile-bound fair value',enhancement='same bounded curve at actual grade ability boost',rounding='round economics then add integer ability floor',manufacturing_expected_cost='diagnostic only; not single-card market price')";assert source.count(marker)==1
 source=source.replace(marker,marker+"\n        if engine.exchange.price_store.fair.model.get('enhancement_price_curve'):\n            hc.PROGRESSION20['value_model']=dict(kind='base_times_independent_enhancement_curve',market_base='unchanged profile-bound +1 price',enhancement='independent normalized original manufacturing-cost multipliers; bounded high-grade compression',maximum_grade20_multiplier=engine.exchange.price_store.fair.model['enhancement_price_curve']['multipliers'][20],success_rates_changed=False)")
 compile(source,'npc_exchange.py','exec');(P/'npc_exchange.py').write_text(source,'utf8')
 assert baseline=={p:sha(p) for p in baseline}
 report=dict(status='PREPARED',baseline=baseline,model_sha256=cat['model_sha256'],profile_sha256=cat['profile_sha256'],rows=len(cat['rows']),base_rows_byte_equivalent=True,source_revision=settings['revision'],multipliers=multipliers,peak_grade20_at_maximum_market_factor=peak*maximum,native_quote_ceiling=quote_ceiling,outputs={n:sha(P/n) for n in ['model.json','catalogue.json.gz','fair_value_store.py','npc_exchange.py']},formal_activated=False);save('prepared.json',report)
 print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
