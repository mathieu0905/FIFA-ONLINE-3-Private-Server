from pathlib import Path
import sys,json,ast,copy,types,hashlib
sys.path.insert(0,r'D:\fifaol3\pack-reprice')
import host
from hot_update_runtime import compile_handlers
h=host.h;R=Path(__file__).parent
a=json.loads((R/'active-before.json').read_text('utf8'));raw=(R/'before-business.py').read_bytes();src=raw.decode('utf8')
audit=json.loads((R/'audit.json').read_text('utf8'))
low={p['id'] for p in audit if p['median']<85}
duplicates={98310016,98310017,98310018,98310019,98310020,98310022,98310038,98248008,98448010,98418010}
retired=sorted(low|duplicates)
addition='''def retired_shop_product(host, itemid, trail):
    if itemid in trail:raise ValueError('Cyclic package')
    if itemid in %s:return True
    trail=trail+(itemid,)
    if itemid in host.PACKAGES:
        return any(retired_shop_product(host,i,trail) for i,n in host.PACKAGES[itemid][2] if n>0)
    if itemid in host.MONTHLY:
        return any(retired_shop_product(host,i,trail) for i,n in host.MONTHLY[itemid][3]+host.MONTHLY[itemid][4] if n>0)
    return False

''' % repr(tuple(retired))
src=src.replace('def blocked(host, itemid):','def blocked(host, itemid):\n    if retired_shop_product(host,itemid,()):return True',1)
src=src.replace('自选商品已停售，请选择随机卡包；已持有的自选包仍可正常使用。','该商品已下架，请刷新商城选择在售商品；已持有的卡包仍可正常使用。',1)
src=addition+src
newraw=src.encode('utf8');(R/'business.py').write_bytes(newraw)
old=compile_handlers(raw,'before',a['routes'],allow_templates=True);new=compile_handlers(newraw,'after',a['routes'],allow_templates=True);ns=new['/shop/list'].__globals__
before=json.loads(old['/shop/list'](h,'',b'')[1]);after=json.loads(new['/shop/list'](h,'',b'')[1]);by=lambda rows:{int(r['product']['itemid']):r for r in rows}
b=by(before);n=by(after);removed=set(b)-set(n)
assert set(retired)<=removed
assert all(n[i]==b[i] for i in n),'Retained product changed'
assert sum(isinstance(r.get('chained'),list) for r in after)==5
assert all(not ns['blocked'](h,i) for i in (98448081,98448082,98418081,98418082,98432701,98432702,97310084,97010100))
def forbidden(*args):raise AssertionError('Retired purchase reached native transaction')
proxy=types.SimpleNamespace(**vars(h));proxy.ENDPOINTS=dict(h.ENDPOINTS,**{'/shop/purchase':forbidden})
for i in removed:
 for req in ({'productid':i},{'shopid':i},{'shopid':i+h.MP_SHOPID},{'shopid':i+h.STSHOPID,'productid':i}):
  result=json.loads(new['/shop/purchase'](proxy,'',json.dumps(req).encode())[1]);assert result['result'] is False and result['reason']=='NOT_EXIST_PRODUCT',(i,req,result)
# Verify the opening, chain and pricing functions are byte-for-byte AST identical.
def defs(raw):return {v.name:ast.dump(v) for v in ast.parse(raw).body if isinstance(v,ast.FunctionDef)}
od=defs(raw);nd=defs(newraw);changed=[k for k in od if od[k]!=nd[k]]
assert changed==['blocked','_pricing_base_purchase'],changed
for i in retired:assert list(h.pack_pool(i)) and h.item_def(i),'Owned definitions lost'
plan=dict(retired=retired,low_quality=sorted(low),duplicates=sorted(duplicates),removed=[dict(id=i,name=h.item_def(i)['name']) for i in sorted(removed)])
(R/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),'utf8')
result=dict(passed=True,before=len(before),after=len(after),removed=len(removed),retired_purchase_rejections=4*len(removed),retained_rows_identical=True,chains=5,changed_functions=changed,inventory_definitions_preserved=True,source_sha256=hashlib.sha256(newraw).hexdigest())
(R/'tests.json').write_text(json.dumps(result,indent=2),'utf8');print(json.dumps(result));host.close()

