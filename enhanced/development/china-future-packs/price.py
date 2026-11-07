import json
import host
from build import RANDOM,CHOICE,signed,write
try:
 h=host.h;cfg=json.loads((host.R/'club_season_products.json').read_text('utf8'));report={}
 mapping=json.loads((host.R/'upgrade-mapping.json').read_text('utf8')) if (host.R/'upgrade-mapping.json').exists() else {}
 for i in [RANDOM,CHOICE]+list(mapping.values()):
  value=h.pack_expected_value(i);quotes={kind:h.pack_value_quote(i,kind) for kind in ('ordinary','chain','once')}
  row=dict(expected_ep=value,quotes=quotes,kind='ordinary',price=quotes['ordinary'])
  cfg['value_prices'][str(i)]=row;cfg['strength_packs'][str(i)]['price']=row['price'];report[str(i)]=row
 write(host.R/'club_season_products.json',signed(cfg));write(host.R/'price-proof.json',report)
 print(json.dumps(report))
finally:host.close()
