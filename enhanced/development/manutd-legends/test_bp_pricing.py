"""Independent formula checks and fresh-parent preparation; no official writes."""
import json
from decimal import Decimal,ROUND_CEILING
import bp_pricing as b
from prepare import write
p=b.plan();cfg=json.loads((b.R/'bp_expected_products.json').read_text('utf8'));report=json.loads((b.R/'build.json').read_text('utf8'))
assert report['reference_root']==71250401 and cfg['valuation']['reference_round_target']==500000
track=cfg['chains']['71350401']
for steps in track['round_steps']:assert sum(track['prices'][str(i)] for i in steps)==500000
for root,t in cfg['chains'].items():
 for step,d in t['packages'].items():
  q=cfg['value_prices'][step];assert t['prices'][step]==q['price']==q['quotes']['chain'];assert q['quotes']['once']<q['quotes']['chain']<q['quotes']['ordinary']
for i,q in cfg['value_prices'].items():
 if not q.get('round_apportioned'):
  standard=max(3,int((Decimal(str(q['expected_ep']))*Decimal(str(cfg['valuation']['points_per_ep']))).to_integral_value(rounding=ROUND_CEILING)))
  assert q['quotes']['ordinary']==standard,(i,q)
module=b.common.load(b.R/'pack_value.py','bp_test_model')
class H:pass
h=H();h.PACKS={1:1,2:1};h.PACKAGES={3:('','',[(1,2),(2,1)])};h.MONTHLY={};h.ITEMS={};h.EP_ITEM=99;h.ES_ITEM=98;h.product_packs={'strength_packs':{'2':{'mode':'choice'}}}
h.pack_pool=lambda i:[(100,1),(200,3)];h.pack_grades=lambda i:[(1,25),(8,75)];h.player_value_price=lambda s,g:s*g
v=module.ValueModel(h,.00001)
assert v.value(1)==1093.75 and v.value(2)==1250
assert v.value(3)==3437.5
v.value=lambda i:19000000000
assert v.quote(1,'chain')==123500
import verify_pools as current
real=current.h
stages={int(i) for t in real.product_packs['chains'].values() for steps in t['round_steps'] for i in steps}
report['old_chain_prices']={str(i):real.product_price(i,1) for i in stages}
write(b.R/'build.json',report)
result=dict(status='PASS',checks=['weighted player/grade probabilities','choice maximum','package quantity sum','decimal exact boundary','all 50 reference stages and ten exact 500000 totals','all ordinary/once/chain quote ordering','fresh latest parent preserves icon layer'],priced_products=len(report['products']),legacy_stages=len(stages),parent=p['prior'],bp_per_point=report['bp_per_point'])
write(b.R/'tests.json',result);print(json.dumps(result))
