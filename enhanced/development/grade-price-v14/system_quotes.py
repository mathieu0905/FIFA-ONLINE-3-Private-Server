"""Reissue only system-owned stock quotes; never alter player offers/assets or fills."""
import copy,hashlib,json,math
def reissue(state,old_model,new_model,values,factors,boost,stamp,curve):
 out=copy.deepcopy(state);m=out['market_simulation'];revision=new_model['revision']
 if m.get('system_quote_price_revision')==revision:return out,dict(replayed=True,changed=0),[]
 def reference(sid,grade,config):
  pid,econ,floor,score,_=values[int(sid)];factor=factors[pid];base=round(econ*factor)+floor
  if grade==1:return base
  if config.get('enhancement_price_curve'):return round(base*config['enhancement_price_curve']['multipliers'][grade])
  delta=boost[grade]-config['grade1_boost'];identity=econ/curve(score,config)
  return round(curve(score+delta,config)*identity*factor)+floor+33*delta
 rows=[]
 for key,book in m.get('books',{}).items():
  if stamp<book.get('expires_at',(book['epoch']+1)*900):rows +=[(r,'regular:'+str(key)) for r in book.get('rows',[])]
 for key,book in m.get('rare_books',{}).items():rows +=[(r,'rare:'+str(key)) for r in book.get('rows',[])]
 rows +=[(r,'legacy') for r in m.get('legacy_supply',[])]
 rows +=[(a['listing'],'npc:'+str(key)) for key,a in m.get('npc_exchange',{}).get('assets',{}).items() if isinstance(a.get('listing'),dict)]
 changes=[]
 for r,source in rows:
  if r.get('count',0)<=0 or r.get('price') is None or r.get('_market_expires',float('inf'))<=stamp:continue
  sid=int(r['spid']);grade=int(r['grade']);before=int(r['price']);oldref=reference(sid,grade,old_model);newref=reference(sid,grade,new_model)
  # Retain an ordinary NPC discount/premium, but not stale unit-scale mistakes.
  relative=max(.6,min(1.6,before/max(1,oldref)));after=before if grade==1 and .6<=before/max(1,newref)<=1.6 else max(1,round(newref*relative))
  if before!=after:changes.append(dict(spid=sid,grade=grade,source=source,before=before,after=after,count=r['count']))
  r['price']=after;r['_market_price_revision']=revision
 receipt=dict(replayed=False,changed=len(changes),at=stamp,revision=revision,old_revision=old_model['revision'],changes_sha256=hashlib.sha256(json.dumps(changes,sort_keys=True,separators=(',',':')).encode()).hexdigest(),policy='withdraw old system quote and reissue with identical count/expiry; player orders and completed trades unchanged')
 m['system_quote_price_revision']=revision;m.setdefault('system_quote_repricing_receipts',{})[revision]=receipt
 return out,receipt,changes
