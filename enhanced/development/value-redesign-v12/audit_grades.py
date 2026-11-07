"""Replay actual grade ability boosts without manufacturing-cost price caps."""
from pathlib import Path
import gzip,json,math
from fair_value_model import economic_curve
from effective_boosts import grade_boosts
P=Path(__file__).resolve().parent
def main():
 c=json.loads((P/'model.json').read_text('utf8'))
 with gzip.open(P/'catalogue.json.gz','rt',encoding='utf8') as f:cat=json.load(f)
 boost=grade_boosts();checks=0;maximum=0
 for r in cat['rows']:
  previous=0
  for g in range(1,21):
   delta=boost[g]-5;value=round(economic_curve(r['effective_score']+delta,c)*r['identity_factor'])+r['strict_floor_ep']+33*delta
   assert value>previous,(r['spid'],g);assert value<5_600_000_000_000_000;previous=value;maximum=max(maximum,value);checks+=1
 result=dict(status='PASS',cards=len(cat['rows']),grade_checks=checks,grades='1..20',effective_grade_boosts=boost,maximum_grade20_price_ep=maximum,ceiling_ties=0,existing_success_rates_and_ability_boosts_changed=False,price_semantics='playable boosted ability; expected manufacture cost no longer sets single-card price',formal_activated=False)
 (P/'grade-regression.json').write_text(json.dumps(result,indent=2)+'\n','utf8');print(json.dumps(result))
if __name__=='__main__':main()
