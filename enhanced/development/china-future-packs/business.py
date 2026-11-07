"""Build a new immutable business source while preserving bulk opening routes."""
import base64,copy,importlib.util,json,zlib
import host
from build import write
try:
 R=host.R;S=host.S;h=host.h
 active=json.loads((S/'hot_updates/active.json').read_text('utf8'));source=(S/active['code']).read_text('utf8')
 mapping={int(k):v for k,v in json.loads((R/'upgrade-mapping.json').read_text('utf8')).items()}
 old=json.loads((R/'volume-before.json').read_text('utf8'));volume=copy.deepcopy(old);changed=[]
 for root,t in volume.items():
  for sid,p in t['packages'].items():
   if not any(i in mapping for i,n in p['contents']):continue
   before=copy.deepcopy(p);p['contents']=[[mapping.get(i,i),n] for i,n in p['contents']]
   p['price']=sum(h.pack_value_quote(i,'chain')*n for i,n in p['contents']);t['prices'][sid]=p['price']
   p['description']=p.get('description','')+'<BR>本期高强版奖励；卡包强化最低+8，具体概率见各包。'
   changed.append(dict(root=root,stage=sid,before=before,after=p))
 # Preserve the original volume definition for already-completed v1 stages.
 assert source.count('def volume_data():')==1
 source=source.replace('def volume_data():','def volume_legacy_data():',1)
 encoded=base64.b64encode(zlib.compress(json.dumps(volume,separators=(',',':'),ensure_ascii=False).encode(),9)).decode()
 function="def volume_data():\n    import json,zlib,base64\n    return json.loads(zlib.decompress(base64.b64decode("+repr(encoded)+")))\n\n\n"
 source=source.replace('def volume_engine(host):',function+'def volume_engine(host):',1)
 source=source.replace("'volume110-v1'","'volume110-high8-v2'")
 anchor="                old=copy.deepcopy(host.item_def(i));items=old.get('items',[])"
 assert source.count(anchor)==1
 prior="""                old=copy.deepcopy(host.item_def(i));items=old.get('items',[])
                if versions.get(str(i))=='volume110-v1':
                    legacy=volume_legacy_data()[str(root)]['packages'][str(i)]
                    items=[dict(itemid=child,count=n,staticdata=clean_pack_definition(host,child)) for child,n in legacy['contents']]
                    old['items']=items
                    old['bunches']=[dict(bunch=1,price=legacy['price'])]"""
 source=source.replace(anchor,prior,1)
 source=source.replace('def blocked(host, itemid):','def blocked(host, itemid):\n    if itemid==98432702:return False',1)
 compile(source,'high8-business.py','exec');(R/'high8-business.py').write_text(source,'utf8')
 write(R/'volume-after.json',volume);write(R/'chain-upgrade-review.json',changed)
 print(json.dumps(dict(status='BUILT_NOT_PUBLISHED',upgraded_chain_stages=len(changed),all_old_handlers_preserved=True,choice_exception=98432702)))
finally:host.close()
