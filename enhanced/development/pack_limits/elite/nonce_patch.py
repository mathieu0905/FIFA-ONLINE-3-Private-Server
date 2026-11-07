"""Apply the minimum stack-sequence and legacy-compatibility delta to product_packs."""
def apply(source):
    start=source.index('    def opening_id(coach,item):\n');end=source.index('    def inventory(st,slot,where=',start)
    source=source[:start]+'''    def lifecycle(coach):
        return (str(coach['_id']),str(coach.get('appat')),str(coach.get('_admin_generation')))
    def stack_owner(coach,item):return lifecycle(coach)+(item['_id'],int(item['itemid']))
    def opening_id(coach,item,legacy=False):
        value=f'{coach["_id"]}:{coach.get("appat")}:{item["_id"]}:{item["itemid"]}:{item["remains"]}:{cfg["edition"]}'
        seq=item.get('product_open_seq',0)
        if not legacy:value+=f':open-v2:{seq}:{coach.get("_admin_generation")}'
        signature=hmac.new(bytes.fromhex(cfg['token_key']),value.encode(),hashlib.sha256).hexdigest()[:24]
        return item['_id']+('_pf_' if legacy else f'_pf_v2_{seq}_')+signature
    legacy_pending={};legacy_receipts=set()
    for coach in prior_state().get('coaches',[]):
        for where in ('items','depot'):
            for item in coach.get(where,[]):
                if item['itemid'] in risks and 'product_open_seq' not in item:
                    legacy_pending[stack_owner(coach,item)]=opening_id(coach,item,legacy=True)
        legacy_receipts.update(lifecycle(coach)+(token,) for token in coach.get('risk_pack_receipts',{}))
    def opening_matches(coach,item,token):
        if opening_id(coach,item)==token:return True
        return ('product_open_seq' not in item and legacy_pending.get(stack_owner(coach,item))==token
                and opening_id(coach,item,legacy=True)==token)
    prior_add=h.inventory_add
    def inventory_add(coach,itemid,count):
        old_ids={item['_id'] for item in coach.get('items',[])}
        item=prior_add(coach,itemid,count)
        if itemid in risks and item['_id'] not in old_ids:item['product_open_seq']=0
        return item
''' +source[end:]
    old="if item['itemid'] in risks and opening_id(coach,item)==i:return prior_move(coach,item['_id'],src,dst)"
    assert source.count(old)==1
    source=source.replace(old,"if item['itemid'] in risks and opening_matches(coach,item,i):return prior_move(coach,item['_id'],src,dst)",1)
    old="x['itemid'] in risks and opening_id(coach,x)==itemid and x['remains']>0"
    assert source.count(old)==1
    source=source.replace(old,"x['itemid'] in risks and opening_matches(coach,x,itemid) and x['remains']>0",1)
    old='            if receipt:\n'
    assert source.count(old)==1
    source=source.replace(old,old+'''                owner=receipt.get('owner_generation')
                if ('owner_generation' in receipt and owner!=coach.get('_admin_generation')) or ('owner_generation' not in receipt and lifecycle(coach)+(itemid,) not in legacy_receipts):
                    return h._json({'result':False,'reason':'INVALID_ITEM'})
''',1)
    old="coach.setdefault('risk_pack_receipts',{})[itemid]={'player':player,'chosen':chosen}"
    assert source.count(old)==1
    source=source.replace(old,"""if not coach.get('_admin_generation'):
                import secrets
                previous_lifecycle=lifecycle(coach)
                coach['_admin_generation']=secrets.token_hex(16)
                current_lifecycle=lifecycle(coach)
                legacy_receipts.update(current_lifecycle+(key[-1],) for key in list(legacy_receipts) if key[:3]==previous_lifecycle)
                legacy_pending.update({current_lifecycle+key[3:]:value for key,value in list(legacy_pending.items()) if key[:3]==previous_lifecycle})
            coach.setdefault('risk_pack_receipts',{})[itemid]={'player':player,'chosen':chosen,'owner_generation':coach.get('_admin_generation'),'open_version':2,'open_seq':item.get('product_open_seq',0)}
            item['product_open_seq']=item.get('product_open_seq',0)+1""",1)
    old='    h.chained_entry=chained_entry;h.coach_items,h.stack_move=inventory,move'
    assert source.count(old)==1
    source=source.replace(old,old+';h.inventory_add=inventory_add',1)
    return source
