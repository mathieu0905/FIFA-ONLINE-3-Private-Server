"""Atomic purchase of only the remaining stages in the current chain round."""
import copy,functools,hashlib,hmac,json,secrets,time
from urllib.parse import parse_qs

def install(h):
 if getattr(h,'_chain_round_purchase_installed',False):return
 cfg=h.product_packs;tracks={int(k):v for k,v in cfg['chains'].items()};retired=set(cfg.get('retired_chains',[]));secret=bytes.fromhex(cfg['token_key'])
 def owner(st):
  c=h.my_coach(st);return [str(c['_id']),str(c.get('appat')),str(c.get('_admin_generation'))]
 def snapshot(st,root):
  if root not in tracks:return None
  t=tracks[root];r=st.get('product_chain_rounds',{}).get(str(root),{})
  rn=int(r.get('rounds',0));stage=int(r.get('stage',0));c=h.my_coach(st)
  if rn<0 or rn>=t['rounds'] or stage<0 or stage>=len(t['steps']) or (root in retired and stage==0):return None
  if r.get('owner') is not None and (r['owner']!=str(c['_id']) or r.get('owner_appat')!=c.get('appat')):return None
  steps=t['round_steps'][rn][stage:];rewards={};prices=[]
  for i in steps:
   prices.append(h.product_price(i,1))
   for child,n in t['packages'][str(i)]['contents']:rewards[child]=rewards.get(child,0)+n
  return dict(root=root,owner=owner(st),round=rn,stage=stage,steps=steps,prices=prices,total=sum(prices),rewards=[[i,n] for i,n in rewards.items()])
 def sign(q):return hmac.new(secret,json.dumps(q,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode(),hashlib.sha256).hexdigest()
 def decorate(rows,st):
  result=[]
  for row in rows:
   root=row.get('shopid');q=snapshot(st,root) if root in tracks else None
   result.append(dict(row,round_buy_supported=root in tracks,round_buy_enabled=q is not None,
                      round_buy_total=q['total'] if q else 0,round_buy_stages=len(q['steps']) if q else 0))
  return result
 old_listing=h.shop_list
 def listing(st):return decorate(old_listing(st),st)
 h.shop_list=listing
 old_file=h.from_file
 def file(path):return h._json(listing(h._state())) if path=='/shop/list' else old_file(path)
 h.from_file=file;h.ENDPOINTS['/shop/list']=lambda q,b:h._json(listing(h._state()))
 previous=h.ENDPOINTS['/shop/purchase']
 def stage_purchase(q,b):
  result=previous(q,b);out=json.loads(result[1])
  if out.get('result'):
   st=h._state()
   for resource in out.get('resources',[]):
    if resource.get('uri')=='/shop/list':resource['body']=decorate(resource['body'],st)
   return h._json(out)
  return result
 h.ENDPOINTS['/shop/purchase']=stage_purchase;h.ep_shop_purchase=stage_purchase
 def response(st,receipt,replayed=False):
  root=receipt['root'];entry=h.chained_entry(st,root);rows=listing(st)
  counts=json.loads(h.ENDPOINTS['/shop/remained/limited']('',b'')[1])
  return h._json(dict(result=True,currency='cash',spent=receipt['spent'],replayed=replayed,round_completed=receipt['round_completed'],
    message=f'本轮剩余档位已全部购买，共花费{receipt["spent"]:,}点券。奖励已进入背包。',
    states={str(root):{k:entry[k] for k in ('step','buy','remained','remainedperaccount')}},
    resources=h.coach_me_resources(st,h._default_slot(st))+[dict(uri='/shop/list',body=rows),dict(uri='/shop/remained/limited',body=counts)]))
 def quote(query,body):
  try:root=int(parse_qs(query.lstrip('?')).get('root',['0'])[0])
  except (ValueError,TypeError):return h._json(dict(result=False,message='无效的连锁编号。'))
  with h.STATE_LOCK:
   st=h._state();q=snapshot(st,root)
   if q is None:return h._json(dict(result=False,message='当前连锁已完成，或不能继续购买此轮。请刷新商城。'))
   q.update(expires=int(time.time())+180,nonce=secrets.token_hex(16));q['signature']=sign(q)
   t=tracks[root];labels=[f'{h.item_def(i)["name"]} ×{n}' for i,n in q['rewards']]
   message=f'{t["name"]}\n第{q["round"]+1}轮，购买剩余{len(q["steps"])}档。\n总价：{q["total"]:,}点券\n奖励：\n'+'\n'.join(labels)+'\n\n仅购买当前这一轮的剩余档位；不会连续购买下一轮。'
   return h._json(dict(result=True,quote=q,message=message))
 def purchase(query,body):
  try:req=json.loads(body or b'{}');q=req['quote'];sig=q['signature']
  except (ValueError,TypeError,KeyError):return h._json(dict(result=False,message='购买报价缺失，请重新点击本轮购买。'))
  if not isinstance(q,dict) or not isinstance(sig,str):return h._json(dict(result=False,message='无效报价。'))
  unsigned={k:v for k,v in q.items() if k!='signature'}
  expected={'root','owner','round','stage','steps','prices','total','rewards','expires','nonce'}
  if set(unsigned)!=expected or not hmac.compare_digest(sig,sign(unsigned)):return h._json(dict(result=False,message='报价验证失败，请重新获取价格。'))
  key=hashlib.sha256((q['nonce']+sig).encode()).hexdigest()
  with h.STATE_LOCK:
   st=h._state();c=h.my_coach(st);receipt=st.get('product_chain_bulk_receipts',{}).get(key)
   if q['owner']!=owner(st):return h._json(dict(result=False,message='经理已切换，请重新获取报价。'))
   if receipt:return response(st,receipt,True)
   if not isinstance(q['expires'],int) or q['expires']<time.time():return h._json(dict(result=False,message='报价已过期，请重新点击购买。'))
   current=snapshot(st,q['root'])
   if current is None or any(q[k]!=v for k,v in current.items()):return h._json(dict(result=False,message='本轮进度或价格已变化，请刷新后重试。'))
   if int(c.get('cash',0))<current['total']:return h._json(dict(result=False,message=f'点券不足，本轮剩余档位需要{current["total"]:,}点券。'))
   h.add_cash(st,-current['total'],'shop:round:'+str(q['root']))
   for child,n in current['rewards']:h.inventory_add(c,child,n)
   record=copy.deepcopy(st.get('product_chain_rounds',{}).get(str(q['root']),{}))
   record.update(owner=str(c['_id']),owner_appat=c.get('appat'),rounds=current['round']+1,stage=0)
   st.setdefault('product_chain_rounds',{})[str(q['root'])]=record
   receipt=dict(root=q['root'],spent=current['total'],round_completed=current['round']+1,owner=owner(st),granted=current['rewards'])
   st.setdefault('product_chain_bulk_receipts',{})[key]=receipt
   h._save(st)  # One atomic persistence commit for cash, rewards, progress and receipt.
   return response(st,receipt)
 h.ENDPOINTS['/shop/chain/round/quote']=quote;h.ENDPOINTS['/shop/chain/round/purchase']=purchase
 h.chain_round_snapshot=snapshot;h._chain_round_purchase_installed=True
