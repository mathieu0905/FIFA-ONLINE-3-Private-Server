"""Check full quote coverage and the real future-product price dispatcher."""
import ast,json
from types import SimpleNamespace
import all_prices as a
from prepare import write
p=a.plan();cfg=json.loads((a.R/'all_pack_expected_prices.json').read_text('utf8'));report=json.loads((a.R/'build.json').read_text('utf8'))
assert len(cfg['value_prices'])==313
assert {str(r['id']) for r in report['rows']}==set(cfg['value_prices'])
for r in report['rows']:
 q=cfg['value_prices'][str(r['id'])];assert q['price']==r['expected_price'] and q['price']==q['quotes'][q['kind']]
source=ast.parse((a.R/'product_packs.py').read_text('utf8'));installer=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='install');price=next(n for n in installer.body if isinstance(n,ast.FunctionDef) and n.name=='price')
h=SimpleNamespace(PACKS={1:1},PACKAGES={2:1},MONTHLY={3:1},ITEMS={4:('','','EP_LOTTERY'),5:('','','ITEM_LOTTERY'),6:('','','PLAYER_EXP_CAPSULE')})
model=SimpleNamespace(quote=lambda i,kind:11 if kind=='ordinary' else 5)
env=dict(h=h,value_prices={},value_model=model,stages={77:(99,0,0)},risks={},bundles={},tracks={99:{'prices':{'77':900}}},rules={3:{'period':'once'}},chain_only=set(),previous_price=lambda i,n,v:-9)
exec(compile(ast.Module(body=[price],type_ignores=[]),'real_product_price','exec'),env);fn=env['price']
for i in (1,2,4,5):assert fn(i,10)==110
assert fn(3,1)==5 and fn(6,1)==-9 and fn(77,1)==900
env['value_prices']['77']={'price':800};assert fn(77,1)==800
write(a.R/'tests.json',dict(status='PASS',full_coverage=313,changed=43,groups=report['groups'],new_pack_package_monthly_lottery_auto_quote=True,unrelated_utility_price_retained=True,existing_chain_exact_price_retained=True,real_function_extracted=True,latest_parent=p['prior']))
print('Full coverage / real price dispatcher / chain contract tests PASS')
