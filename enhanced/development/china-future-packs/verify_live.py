"""Read-only final acceptance of sale definitions, icons, guards and active hot code."""
from pathlib import Path
import hashlib,json,re,ssl,urllib.request
import install
R=install.R;S=install.S;C=install.C
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
def raw(url):
 with opener.open(url,timeout=20) as r:assert r.status==200;return r.read()
def get(url):return json.loads(raw(url))
def main():
 play=(S/'play-local.bat').read_bytes();relative='patches/'+re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode()
 helper=install.d.load(S/relative,'final_high8_packs_gate');proof=helper.preflight(S,C)
 validator=install.d.load(S/'patches/startup_market_preflight.py','final_high8_composed_guard');validator.verify_manifest(helper.compose_manifest(S,C),S,C)
 hot=install.d.base.hot_status();published=json.loads((R/'hot-active.json').read_text('utf8'))
 assert hot['revision']==published['revision'] and hot['abi']==2 and hot['watcher_running'] and hot['error'] is None
 descriptor=json.loads((S/'hot_updates/active.json').read_text('utf8'))
 assert install.sha(S/descriptor['code'])==install.sha(R/'high8-business.py')
 rows=get('https://127.0.0.1/shop/list');byid={r['product']['itemid']:r for r in rows}
 prices=json.loads((R/'price-proof.json').read_text('utf8'))
 summary=[]
 for i,category in [(98432701,'PLAYERPACK'),(98432702,'DRAFTPACK')]:
  row=byid[i];definition=row['product']['staticdata'];assert row['visible'] and row['buy'] and definition['category']==category
  assert definition['bunches'][0]['price']==prices[str(i)]['price']
  assert definition['itemicon']==f'FO3N_{i}_V3'
  data=raw('https://127.0.0.1/cdn/externalAssets/shop/'+definition['itemicon']+'.png')
  assert hashlib.sha256(data).hexdigest()==install.sha(R/'icons'/(definition['itemicon']+'.png'))
  summary.append(dict(itemid=i,name=definition['name'],price=definition['bunches'][0]['price'],category=category,visible=True,buy=True,icon_http_pass=True))
  if i==98432702:assert definition['draft']==dict(season=327,grade=8,availables=1)
 mapping={int(k):v for k,v in json.loads((R/'upgrade-mapping.json').read_text('utf8')).items()}
 for old,new in mapping.items():assert old not in byid and new in byid
 audit=json.loads((R/'grade-sale-audit.json').read_text('utf8'))
 old={r['itemid']:r for r in audit}
 cfg=json.loads((S/'gamedata/club_season_products.json').read_text('utf8'))
 grade_summary=[]
 for i,row in byid.items():
  definition=row['product']['staticdata']
  if definition.get('category') not in ('PLAYERPACK','DRAFTPACK'):continue
  if str(i) in cfg['strength_packs']:
   data=cfg['strength_packs'][str(i)];low=min(g for g,w in enumerate(data['grades'],1) if w)
   seasons={s//1000000 for t in data['tiers'] for s in t['pool']}
  elif i in old:low=old[i]['minimum'];seasons=set(old[i]['seasons'])
  else:raise AssertionError('New unknown sale SKU needs explicit grade audit '+str(i))
  assert low>=8 or seasons=={84},(i,definition['name'],low,seasons)
  grade_summary.append(dict(itemid=i,name=definition['name'],minimum=low,moments_exempt=seasons=={84}))
 native_body=json.loads(Path(r'D:\fifaol3\china-future\body-native-verification.json').read_text('utf8'));assert native_body['status']=='PASS'
 # Read-only file baseline proves the imported body records were not changed by this task.
 baseline=json.loads((R/'baseline.json').read_text('utf8'))
 assert install.sha(S/'gamedata/fifadb.sqlite')==baseline[str(S/'gamedata/fifadb.sqlite')]
 for rel in ['club_season_products.json','all_item_icon_manifest.json']:assert install.sha(S/'gamedata'/rel)==install.sha(R/rel)
 for p in (R/'icons').glob('*.png'):
  for directory in ['_cache/games/fo3id/externalAssets/shop/','_cache/cdn/externalAssets/shop/']:assert install.sha(C/directory/p.name)==install.sha(p)
 stopped=json.loads((R/'stopped-state.json').read_bytes());current=json.loads((S/'gamedata/state.json').read_bytes())
 business=lambda st:{k:v for k,v in st.items() if k!='market_simulation'}
 assets_exact=business(stopped)==business(current);shop_exact=(R/'stopped-shop.json').read_bytes()==(S/'gamedata/shop.json').read_bytes()
 assert assets_exact and shop_exact,'Later asset progress retained; do not restore old state'
 report=dict(status='FORMAL_ACTIVE_READ_ONLY_PASS',new_china_packs=summary,versioned_other_packs=len(mapping),future_chain_stages=100,
  audited_sale_packs=grade_summary,regression_cases=64,hot_update_status=hot,preflight=proof,
  top_preflight=str(S/relative),composition_api='compose_manifest(server=None,client=None)',state_business_exact=True,shop_exact=True,
  body_records_unchanged=True,native_gui_verified=False,real_purchase_or_open_performed=False,
  files={str(S/p):install.sha(S/p) for p in [relative,helper.MANIFEST,helper.RECEIPT,'play-local.bat']})
 (R/'installed-handback.json').write_bytes(install.encoded(report))
 print(json.dumps({k:v for k,v in report.items() if k!='audited_sale_packs'},ensure_ascii=True))
if __name__=='__main__':main()
