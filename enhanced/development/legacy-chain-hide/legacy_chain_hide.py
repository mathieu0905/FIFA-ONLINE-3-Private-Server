"""Withdraw legacy chain offers without deleting any paid inventory or progress."""
import hashlib,json
from urllib.parse import parse_qs

def install(h):
 if getattr(h,'_legacy_chain_hide_installed',False):return
 retired=set(map(int,h.product_packs.get('retired_chains',[])))|{70000001,71010101}
 def root(i):
  try:i=int(i or 0)
  except (ValueError,TypeError):return None
  for candidate in [i]+[i-n for n in (getattr(h,'MP_SHOPID',900000000),getattr(h,'STSHOPID',910000000)) if i>=n]:
   mapped=h.CHAIN_STEPS.get(candidate,(candidate,0))[0]
   if mapped in retired:return mapped
  return h.CHAIN_STEPS.get(i,(i,0))[0]
 def legacy(row):
  return root(row.get('shopid')) in retired or root(row.get('product',{}).get('itemid')) in retired
 def filtered(rows):return [row for row in rows if not legacy(row)]
 def unavailable():return h._json(dict(result=False,message='旧期连锁已下架，已购买奖励仍在背包；请到新版连锁选购。',reason='LEGACY_CHAIN_WITHDRAWN'))
 old_listing=h.shop_list
 h.shop_list=lambda st:filtered(old_listing(st))
 old_list_endpoint=h.ENDPOINTS['/shop/list']
 h.ENDPOINTS['/shop/list']=lambda q,b:h._json(filtered(json.loads(old_list_endpoint(q,b)[1])))
 old_limited=h.ENDPOINTS['/shop/remained/limited']
 h.ENDPOINTS['/shop/remained/limited']=lambda q,b:h._json(filtered(json.loads(old_limited(q,b)[1])))
 old_file=h.from_file
 def file(path):
  if path in ('/shop/list','/shop/remained/limited'):return h._json(filtered(json.loads(old_file(path)[1])))
  return old_file(path)
 h.from_file=file
 def response(result):
  out=json.loads(result[1])
  for resource in out.get('resources',[]):
   if resource.get('uri') in ('/shop/list','/shop/remained/limited'):resource['body']=filtered(resource['body'])
  return h._json(out)
 old_entry=h.chained_entry
 def entry(st,i):
  row=old_entry(st,i)
  if root(i) not in retired:return row
  return dict(row,visible=False,buy=False,remained=0,remainedperaccount=0,
              chained=[dict(p,visible=False,buy=False,remained=0,remainedperaccount=0) for p in row.get('chained',[])])
 h.chained_entry=entry
 old_purchase=h.ENDPOINTS['/shop/purchase']
 def purchase(q,b):
  try:req=json.loads(b or b'{}')
  except (ValueError,TypeError):return old_purchase(q,b)
  if isinstance(req,dict) and (root(req.get('shopid')) in retired or root(req.get('productid')) in retired):return unavailable()
  return response(old_purchase(q,b))
 h.ENDPOINTS['/shop/purchase']=purchase;h.ep_shop_purchase=purchase
 old_quote=h.ENDPOINTS['/shop/chain/round/quote']
 def quote(q,b):
  try:i=int(parse_qs(q.lstrip('?')).get('root',['0'])[0])
  except (ValueError,TypeError):return old_quote(q,b)
  return unavailable() if root(i) in retired else old_quote(q,b)
 h.ENDPOINTS['/shop/chain/round/quote']=quote
 old_bulk=h.ENDPOINTS['/shop/chain/round/purchase']
 def bulk(q,b):
  try:req=json.loads(b or b'{}');token=req.get('quote',{})
  except (ValueError,TypeError,AttributeError):return old_bulk(q,b)
  if isinstance(token,dict) and root(token.get('root')) in retired:
   # A retry of a previously committed transaction must remain idempotent.
   # Nothing new is sold; the original endpoint still verifies the owner/HMAC.
   nonce=token.get('nonce');sig=token.get('signature')
   if not isinstance(nonce,str) or not isinstance(sig,str):return unavailable()
   key=hashlib.sha256((nonce+sig).encode()).hexdigest()
   if key not in h._state().get('product_chain_bulk_receipts',{}):return unavailable()
  return response(old_bulk(q,b))
 h.ENDPOINTS['/shop/chain/round/purchase']=bulk
 h.legacy_chain_withdrawn_roots=retired;h._legacy_chain_hide_installed=True
