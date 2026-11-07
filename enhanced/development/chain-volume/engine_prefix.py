def volume_engine(host):
    import copy,json,hmac,hashlib,secrets,time,types
    from urllib.parse import parse_qs
    tracks={int(k):v for k,v in volume_data().items()}
    h=types.SimpleNamespace(**vars(host))
    h.ENDPOINTS=dict(host.ENDPOINTS)
    cfg={**host.product_packs,'chains':{**host.product_packs['chains'],**{str(k):v for k,v in tracks.items()}}}
    h.product_packs=cfg
    retired=set(cfg.get('retired_chains',[]));secret=bytes.fromhex(cfg['token_key'])
    stages={int(i):(root,rn,k) for root,t in tracks.items() for rn,steps in enumerate(t['round_steps']) for k,i in enumerate(steps)}
    def price(i,n):
        if i in stages:return tracks[stages[i][0]]['prices'][str(i)]*n
        return host.product_price(i,n)
    h.product_price=price
    def definition(i):
        if i not in stages:return host.item_def(i)
        root,rn,k=stages[i];d=tracks[root]['packages'][str(i)];out=copy.deepcopy(host.item_def(i))
        out.update(name=d['name'],description=f'第{rn+1}/10轮，第{k+1}/5档：共{d["count"]}包，其中精品包{d["premium_count"]}个。<BR>本档{d["price"]:,}点券；整轮110包。<BR>'+'<BR>'.join(host.item_def(child)['name']+' ×'+str(n) for child,n in d['contents']),bunches=[dict(bunch=1,price=d['price'])],items=[dict(itemid=child,count=n,staticdata=host.item_def(child)) for child,n in d['contents']])
        if d['premium_count']==0:
            featured=host.item_def(d['contents'][0][0])
            out['itemicon']=featured['itemicon'];out['bundleicon']=featured.get('bundleicon',featured['itemicon'])
        return out
    h.item_def=definition
    def chain_entry(st,row):
        root=row.get('shopid')
        if root not in tracks:return row
        row=copy.deepcopy(row);record=st.get('product_chain_rounds',{}).get(str(root),{});versions=record.get('volume_stage_versions',{})
        for part in [row]+row.get('chained',[]):
            i=int(part['product']['itemid'])
            if part.get('currentstep')=='complete' and versions.get(str(i))!='volume110-v1':continue
            d=definition(i);part['product']['staticdata']=d
        row['chainedproductname']=tracks[root]['name']+f'（第{min(record.get("rounds",0)+1,10)}/10轮·整轮110包）'
        return row
    h.chained_entry=lambda st,root:chain_entry(st,host.chained_entry(st,root))
    def old_listing(st):return [chain_entry(st,r) for r in filter_rows(host,host.shop_list(st))]
