def retired_shop_product(host, itemid, trail):
    if itemid in trail:raise ValueError('Cyclic package')
    if itemid in (98248008, 98310013, 98310014, 98310015, 98310016, 98310017, 98310018, 98310019, 98310020, 98310022, 98310038, 98418010, 98448010, 98632700, 98632705, 98632706, 98632707, 98632708, 98632709, 98632710, 98632712, 98632713, 98632714, 98632715, 98632716, 98632717, 98632720, 98632723, 98632724, 98632725, 98632726, 98632729, 98632732, 98632733, 98632734, 98632735, 98632737, 98632738, 98632739, 98632740, 98632744):return True
    trail=trail+(itemid,)
    if itemid in host.PACKAGES:
        return any(retired_shop_product(host,i,trail) for i,n in host.PACKAGES[itemid][2] if n>0)
    if itemid in host.MONTHLY:
        return any(retired_shop_product(host,i,trail) for i,n in host.MONTHLY[itemid][3]+host.MONTHLY[itemid][4] if n>0)
    return False

def volume_legacy_data():
    import json,zlib,base64
    return json.loads(zlib.decompress(base64.b64decode('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')))

def volume_data():
    import json,zlib,base64
    return json.loads(zlib.decompress(base64.b64decode('eJztndGOHNURht9lpVzhizlVdbp7LMQFTxBxGyHLMQtaxayRba6QJePYsiHGkEDAASvgJEAkEiJLCSZgJw8Tz+76ildIz0zXnuk6Paa3EX32DD9Xo2G6+KfObP/1l8TXr22Vjv3ETdzWyde2dk+/vL11cuvx9d/uv3Fz9uCb2c33D/77x8fvvb7/lwezm9e2TmydP/fq7gsXtk66yYmtCxe3X6lf/kIrnGhekL5gfSH6wj/flDilFx/xav14oe+V+qLSF9PmhZscftxpdafVnVZ3Wt2F6k6rO63utLrT6hSqk1YnrU5anbQ6heqk1Umrk1Ynrc6hOmt11uqs1Vmrc6jOWp21Omt11uoSqotWF60uWl20uoTqotVFq4tWF63uJ8/Xp/zK6TO/Ov3S9oX5z+poP7Ez53Yvbu9eXPw4pmV93aQ+bT+v+cL2hTPnd165uHNuty4xe/vKweVfP3rwyezT63sffDW78e3ee18dfPD2stze7/958PBLP5n/s3/l37MbX+9/ePXxn67u3fn42Z/v/eO9R//5zXcPbi4/W/ifHXx599G397978NHenb/V182u3XMll5NqeWn9/uyjb2Zffji79fHsrbt79z6Z/U7Ff351duMP/7t8ZaH81d2LWyd9/e3P75ypvyZ5ObF17vzOSzu7p8+eat6sm1HUb794+szFc+e3Tk7mn95+eefVl08119fvvLhz9uz2+VOh4NnTv9w++6S+XTqhbaYBba7mXa7/9Fx90oc9n2bUczc5bDrTZBJ3nXha/1QPu+6irjvb9emRus6Du84naLXrrsqo7RTaXvqKOtpeVfPT0LZT1Hayba9vtUfpuwzpO9etru+1stp3KjLqO4e+1+4xLboaX9T+cth4iRovtvG1Lx2l8X5o42vt1Wrjucyo8RJu7jypTS9uPPuyWrm9V1HjK9v42qmP0vgCNjqGjZaw0QQ2WsFGk9joFDaaxEbdBDaaxEYd0ugYNuqQRhPYqEMaTWKjDmk0kY0ijSayUaTRUWwUaTSFjSKNprFRpNE0NkpIo2lslJBGx7BRQhpNYKOENJrERglpNJGNIo0mslGk0VFsFGk0hY0ijaaxUaTRNDbKSKNpbJSRRsewUUYaTWCjjDSaxEYZaTSRjSKNJrJRpNFRbBRpNIWNIo2msVGk0TQ2KkijaWxUkEbHsFFBGk1go4I0msRGBWk0kY0ijSayUaTRUWwUaTSFjSKNprFRpNE0NuqRRse10UvNf9gAjRYWE8A7y5tfQMIs/yoDqqT5tQSERvMtAtphtWBpClam4NQUnP/PxK2Crq3QGYXOKHRWobMKXVuhMwqdUeisQrIKqa2QjEIyCskqJKuQ2grJKCSjkKxCtgq5rZCNQjYK2Spkq5DbCtkoZKOQrUKxCqWtUIxCMQrFKhSrUNoKxSgUo1CsQq8KL+n9ilrwr+WNZXb/r3u3Pzb3q7V8OVJCHCkhjpQQR0qIo7V8ud5X68cLfa/UF5W+aDhnFPhypHw5Ur4cKV+OlC9HgS9Hypcj5cuR8uVI+XIU+HKkfDlSvhwpX46UL0eBL0fKlyPly5Hy5Uj5chT4cqR8OVK+HClfjpQvR4EvR8qXI+XLkfLlSPlyFPhypHw5Ur4cKV+OlC9HgS9Hypcj5cuR8uVI+XK0hi/X+yfWtsSCqaxdZfyA4+uJuOT+Jvj0s889U19c13/8xe363+2/cWP26fuzN+/NL37rbv3dlhfs3bn86OGtp6r6vz67dv/Rw3f3Pruyf+v6weevz965Wn9qTVaq76RV7Ka+9NPp0LC09gzCXYGGHNliinHLsKTnN35YOhbn51YHUdcVvKTiyeDg1eMEecgJLoJXuQwAeoJu/ABwLI5wJcMJc9GRJaZ+jkd9QoiLsoQrjnSGMvgMq2WW0DMk+mme4UoepMJ79h1rJ1cI05MSYRRMars/yin6wfdSmv/xrR7jT/RuupIuPZU07TjGemSbM3OfkC/nf3vmHI92Ry0wxuQ2xpQYYzIfYyqMMdmPMVOMMfmPMS0gIsaYbMcYh21MbmOMwzYm8zHGYRuT/RjjsI3ZhDEG25jNGGOwjclujME2JvcxBtuY/McYbGM2YIwhbGM2YowhbGNyG2MI25jMxxjCNib7MYawjdmEMQbbmM0YY7CNyW6MwTYm9zEG25j8xxhsYzZgjGFsYzZijGFsY3IbYxjbmMzHGMY2JvsxhrGN2YQxBtuYzRhjsI3JbozBNib3MQbbmPzHGGxjNmCMEWxjNmKMEWxjchtjBNuYzMcYwTYm+zFGsI3ZhDEG25jNGGOwjclujME2JvcxBtuY/McYbGM2YIzx2MZkPcbEfPUF0Hfpy4EW29zmA3y0uWkEkqX+AgMVUb9M4Ou1qpa2amWrTm3VOaSoXdUZrc5qdVari7S6SKszWp3V6qxWF2mlSCsZrWS1ktVKkVaKtJLRSlYrWa0UaeVIKxutbLWy1cqRVo60stHKVitbrRxplUirGK1itYrVKpFWibSK0SpWq1itEmn1h1oPiezcwmXvf/v27NrXB//6aPb3P5sb5loiOytTnZWpzspUZ2Wq81oie++r9eOFvlfqi0pfNGRwDkR2ViI7K5GdlcjOSmTnQGRnJbKzEtlZieysRHYORHZWIjsrkZ2VyM5KZOdAZGclsrMS2VmJ7KxEdg5EdlYiOyuRnZXIzkpk50BkZyWysxLZWYnsrER2DkR2ViI7K5GdlcjOSmTnQGRnJbKzEtlZieysRHZeQ2Tv/RM7Jo+cKiaunE5/hEdOTcuyKIfGyLV9C3/JNKDNiwHWudSPnBre85XsV3DXrFJPd5NiaPTr0XUe3HVK/sip4W1fyWuuqKZl56jv+YmB7YkPnerReRnceU7+0KnhnV9JWUVZ1jffjs5XVX0zH/rUqR6d90M6vwhZnPypU8M7vxKMXP0Fqq58W1Tlar494nOnerS+gJeO4aUlvDSBl1bw0kReOoWXpvHSFugaXjqmlzrk0jG81CGXJvBSh1yayEsdcmkqL0UuTealyKWjeClyaQovRS5N5aXIpYm8lJBLU3kpIZeO4aWEXJrASwm5NJGXEnJpKi9FLk3mpcilo3gpcmkKL0UuTeWlyKWJvJSRS1N5KSOXjuGljFyawEsZuTSRlzJyaSovRS5N5qXIpaN4KXJpCi9FLk3lpcilibxUkEtTeakgl47hpYJcmsBLBbk0kZcKcmkqL0UuTealyKWjeClyaQovRS5N5aXIpYm81COXju2lMcNugUBa+ExA9SzvgAEi0/xpBrZJ84sJyA39IoEEsVqyNCUrW3JqSs7/z+N2SddW6YxKZ1U6q9JFKl1bpTMqnVXprEqKVFJbJRmVZFWSVUmRSmqrJKOSrEqyKjlSyW2VbFSyVclWJUcqua2SjUq2KtmqlEiltFWKUSlWpViVEqmUtkoxKsWqFKvSH6o8pNTJJH44x/J2Y+5iayl1opw5Uc6cKGdOlDMnayl1va/Wjxf6XqkvKn3R0NIkUOpEKXWilDpRSp0opU4CpU6UUidKqROl1IlS6iRQ6kQpdaKUOlFKnSilTgKlTpRSJ0qpE6XUiVLqJFDqRCl1opQ6UUqdKKVOAqVOlFInSqkTpdSJUuokUOpEKXWilDpRSp0opU4CpU6UUidKqROl1IlS6mQNpa73T6ydfCo3nVSSApy+cunQ5ON91RF9XH2HlR9GO+9oXPhTjh/a8v19Xo6CRRN9mqYn4PMObvoqotyX3MG3ricdR0OzT4+2x09a6dv2ssk+TdsTZJ/hfV/JPlzVA18H3H9xUx8afXo0XoY0fjGASxN9msYniD7DG78Sfcr6Nt4xf3vfavwRk0+PxsdPNOnbeN8kn6bxCZLP8MavJh/xc4BtfKuRqp6zBiefHq2PH0ICL/0xvDR+cgi8dAQvjR/3AS8dxUvjZ3TAS8fwUhc/VgNeOo6XOuTSUbzUIZem8FKHXJrGSx1yaSIvRS5N5qXIpeN4KXJpEi9FLk3kpcilabyUkEtTeSkhl47ipYRcmsJLCbk0jZcScmkiL0UuTealyKXjeClyaRIvRS5N5KXIpWm8lJFLU3kpI5eO4qWMXJrCSxm5NI2XMnJpIi9FLk3mpcil43gpcmkSL0UuTeSlyKVpvFSQS1N5qSCXjuKlglyawksFuTSNlwpyaSIvRS5N5qXIpeN4KXJpEi9FLk3kpcilabzUI5eO7aUxpW6BQFr6TED1NHfAAJFp/jQD3KT5yQTohn6VwIJoFS1t0coWnZqiC1Jdq6gzSp1V6qxSZ5W6SKkzSp1V6qxSZ5VSpJSMUrJKySolq5QipWSUklVKVilZpRwpZaOUrVK2Stkq5UgpG6VslbJVylapRErFKBWrVKxSsUolUipGqVilYpWKVeoPlR6S63wXVuz+/dk7N8ydbS25zit7zit7zit7zit7zq8l1/W+Wj9e6Hulvqj0RUNQ84Fc55Vc55Vc55Vc55Vc5wO5ziu5ziu5ziu5ziu5zgdynVdynVdynVdynVdynQ/kOq/kOq/kOq/kOq/kOh/IdV7JdV7JdV7JdV7JdT6Q67yS67yS67yS67yS63wg13kl13kl13kl13kl1/lArvNKrvNKrvNKrvNKrvNryHW9f2Jt8yyYytp/EqSh2hIq7m+XTz/73DP1xXX9x1/crv/d/hs3Zp++P3vz3vzit+7W3215wd6dy48e3nqqqv/rs2v3Hz18d++zK/u3rh98/vrsnav1p9YEK0e+w3al4kn1A4NVfAbhrtCxpPz+I1vMO02w0vNLEKyOw/mtZDSWsuiIxhVzMZgl3uMEO/adPU+wYYnrCabIaMfhCFfiXjGd36rj2XdS+XI4lrzHIXbsTnseYn0PXz1E4p/mIa5Ex6q2bvre6FhGZ1hG0ZGPdIYda9ieZ9gAzvUMU0TH43CGLVZ6WbiuhdcPY6X3OMWOjS5mmOM9w3QshzHDZDXDdOyZMcPkNsN07Kwxw+Q1w3ThFTHD5DbDdJEaMcMc6xmmC/qIGSanGaaLH4kZJrMZpotFiRkmsxkGe5hNmGGwh8luhsEeJvcZBnuYDZhhsIfJfobpwolihslthukik2KGOdYzTBfkFDNMTjNMFy8VM0xmM0wXexUzTGYzDPYwmzDDYA+T3QyDPUzuMwz2MBsww2APk/0M04XPxQyT2wzTReLFDHOsZ5guqC9mmJxmmC4+MGaYzGaYLtYwZpjMZhjsYTZhhsEeJrsZBnuY3GcY7GE2YIbBHib7GaYLF40ZJrcZpos8jRnmWM8wXRBrzDA5zTBdPGzMMJnNMF1sbcwwmc0w2MNswgyDPUx2Mwz2MLnPMNjDbMAMgz1M9jNMFx4dM0wuM0xMWl8ge5emHHiwzT0+4EWbO0ZAVTa/vsA91K8SGHqtoqUtWtmiU1N0QVpvFXVGqbNKnVXqrFIXKXVGqbNKnVXqrFKKlJJRSlYpWaVklVKklIxSskrJKiWrlCOlbJSyVcpWKVulHCllo5StUrZK2SqVSKkYpWKVilUqVqlESsUoFatUrFKxSv2h0kuXLv0fy/5d7g==')))



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
    chain_pack_ids={i for t in tracks.values() for p in t['packages'].values() for i,n in p['contents']}
    def price(i,n):
        if i in stages:return tracks[stages[i][0]]['prices'][str(i)]*n
        return host.product_price(i,n)
    h.product_price=price
    def definition(i):
        if i not in stages:
            return clean_pack_definition(host,i) if i in chain_pack_ids else host.item_def(i)
        root,rn,k=stages[i];d=tracks[root]['packages'][str(i)];out=copy.deepcopy(host.item_def(i))
        out.update(name=d['name'],description=f'第{rn+1}轮 / 第{k+1}档<BR>共{d["count"]}个球员包，售价{d["price"]:,}点券。<BR>'+'<BR>'.join(definition(child)['name']+' ×'+str(n) for child,n in d['contents'])+'<BR>每包随机获得1名球员。',bunches=[dict(bunch=1,price=d['price'])],items=[dict(itemid=child,count=n,staticdata=definition(child)) for child,n in d['contents']])
        if d['premium_count']==0:
            featured=definition(d['contents'][0][0])
            out['itemicon']=featured['itemicon'];out['bundleicon']=featured.get('bundleicon',featured['itemicon'])
        return out
    h.item_def=definition
    def chain_entry(st,row):
        root=row.get('shopid')
        if root not in tracks:return row
        row=copy.deepcopy(row);record=st.get('product_chain_rounds',{}).get(str(root),{});versions=record.get('volume_stage_versions',{})
        for part in [row]+row.get('chained',[]):
            i=int(part['product']['itemid'])
            if part.get('currentstep')=='complete' and versions.get(str(i))!='volume110-price-v3':
                old=copy.deepcopy(getattr(host,'_pricing_original',host).item_def(i));items=old.get('items',[])
                if versions.get(str(i)) in ('volume110-v1','volume110-high8-v2'):
                    legacy=(pricing_legacy_data() if versions.get(str(i))=='volume110-high8-v2' else volume_legacy_data())[str(root)]['packages'][str(i)]
                    items=[dict(itemid=child,count=n,staticdata=clean_pack_definition(host,child)) for child,n in legacy['contents']]
                    old['items']=items
                    old['bunches']=[dict(bunch=1,price=legacy['price'])]
                old['name']=tracks[root]['name']
                for child in items:child['staticdata']=clean_pack_definition(host,int(child['itemid']))
                old['description']='本档已购买。<BR>'+'<BR>'.join(x['staticdata']['name']+' ×'+str(x['count']) for x in items)
                part['product']['staticdata']=old
                continue
            d=definition(i);part['product']['staticdata']=d
        row['chainedproductname']=tracks[root]['name']
        return row
    h.chained_entry=lambda st,root:chain_entry(st,host.chained_entry(st,root))
    def old_listing(st):return [chain_entry(st,r) for r in filter_rows(host,host.shop_list(st))]

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

    def listing(st):return decorate(old_listing(st),st)

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
       record.setdefault('volume_stage_versions',{}).update({str(i):'volume110-price-v3' for i in current['steps']})
       st.setdefault('product_chain_rounds',{})[str(q['root'])]=record
       receipt=dict(root=q['root'],spent=current['total'],round_completed=current['round']+1,owner=owner(st),granted=current['rewards'])
       st.setdefault('product_chain_bulk_receipts',{})[key]=receipt
       h._save(st)  # One atomic persistence commit for cash, rewards, progress and receipt.
       return response(st,receipt)
    def counts(st):
        return [dict(shopid=r['shopid'],**{key:r[key] for key in ('step','buy','remained','remainedperaccount') if key in r}) for r in listing(st) if 'remained' in r]
    h.ENDPOINTS['/shop/remained/limited']=lambda q,b:h._json(counts(h._state()))
    def single(req,i):
        root,rn,k=stages[i];st=h._state();coach=h.my_coach(st)
        current=snapshot(st,root)
        if isinstance(req.get('bunch',0),bool) or req.get('bunch',0)!=0 or req.get('shopid',root) not in (root,i) or current is None or current['round']!=rn or current['stage']!=k:
            return h._json(dict(result=False,reason='请按当前轮次的档位顺序购买。'))
        amount=price(i,1)
        if int(coach.get('cash',0))<amount:return h._json(dict(result=False,reason='NOT_ENOUGH_CASH'))
        h.add_cash(st,-amount,'shop:'+str(i))
        for child,n in tracks[root]['packages'][str(i)]['contents']:h.inventory_add(coach,child,n)
        record=copy.deepcopy(st.get('product_chain_rounds',{}).get(str(root),{}))
        record.update(owner=str(coach['_id']),owner_appat=coach.get('appat'),rounds=rn,stage=k+1)
        if k+1==5:record.update(rounds=rn+1,stage=0)
        record.setdefault('volume_stage_versions',{})[str(i)]='volume110-price-v3'
        st.setdefault('product_chain_rounds',{})[str(root)]=record
        h._save(st)
        receipt=dict(root=root,spent=amount,round_completed=record['rounds'])
        out=json.loads(response(st,receipt)[1]);out['message']='本档购买完成，卡包已进入背包。';out['chain_round']=record
        return h._json(out)
    return dict(listing=listing,counts=counts,quote=quote,purchase=purchase,single=single,stages=stages,snapshot=snapshot)

def contains_choice(host, itemid, trail):
    if itemid in trail:
        raise ValueError('Cyclic package')
    trail=trail+(itemid,)
    if itemid in host.PACKS:
        return host.item_def(itemid).get('category')=='DRAFTPACK'
    if itemid in host.PACKAGES:
        return any(contains_choice(host,i,trail) for i,n in host.PACKAGES[itemid][2] if n>0)
    if itemid in host.MONTHLY:
        return any(contains_choice(host,i,trail) for i,n in host.MONTHLY[itemid][3]+host.MONTHLY[itemid][4] if n>0)
    return False

def blocked(host, itemid):
    if retired_shop_product(host,itemid,()):return True
    if itemid==98432702:return False
    # Existing ordered chain contracts remain on their original purchase path.
    if any(str(itemid) in t['packages'] for t in host.product_packs['chains'].values()):
        return False
    return contains_choice(host,itemid,())

def filter_rows(host, rows):
    return [r for r in rows if isinstance(r.get('chained'),list) or not blocked(host,int(r.get('product',{}).get('itemid',0)))]

def _pricing_base_shop_list(host, query, body):
    with host.STATE_LOCK:return host._json(volume_engine(host)['listing'](host._state()))


def _pricing_base_remained(host, query, body):
    with host.STATE_LOCK:return host._json(volume_engine(host)['counts'](host._state()))


def refresh_response(host, response):
    import json
    out=json.loads(response[1]);engine=volume_engine(host);st=host._state()
    for r in out.get('resources',[]):
        if r.get('uri')=='/shop/list':r['body']=engine['listing'](st)
        elif r.get('uri')=='/shop/remained/limited':r['body']=engine['counts'](st)
    return host._json(out)


def _pricing_base_round_purchase(host, query, body):
    with host.STATE_LOCK:return volume_engine(host)['purchase'](query,body)


def _pricing_base_purchase(host, query, body):
    import json
    with host.STATE_LOCK:
        try:
            req=json.loads(body or b'{}')
            itemid=int(req.get('productid') or 0) or int(req.get('shopid') or 0)%host.MP_SHOPID%host.STSHOPID
        except (ValueError,TypeError,AttributeError):
            return host._json(dict(result=False,reason='INVALID_PARAM'))
        engine=volume_engine(host)
        if itemid in engine['stages']:return engine['single'](req,itemid)
        if blocked(host,itemid):
            return host._json(dict(result=False,reason='NOT_EXIST_PRODUCT',message='该商品已下架，请刷新商城选择在售商品；已持有的卡包仍可正常使用。'))
        return refresh_response(host,host.ENDPOINTS['/shop/purchase'](query,body))


def _pricing_base_round_quote(host, query, body):
    with host.STATE_LOCK:return volume_engine(host)['quote'](query,body)



def market_supply_activate(host, query, body):
    import copy
    import json
    import time
    from market_supply_settings import validate
    request=json.loads(body or b'{}')
    settings=validate(request.get('settings'))
    keys={quality+'_'+str(grade) for quality in ('low','mid','high','elite') for grade in range(11,21)}
    if set(settings['rare_overrides'])!=keys or any(rule['period_seconds']!=300 or rule['slots']!=5 for rule in settings['rare_overrides'].values()):
        raise ValueError('Minute activation requires exactly five independent one-minute slots per five-minute batch in every rare tier')
    engine=host.market_engine
    control=engine.supply_settings
    raw=(json.dumps(settings,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode('utf8')
    target=control.digest(raw)
    with host.STATE_LOCK:
        current=control.get()
        state=host._state()
        if not engine.has_active(state):raise ValueError('No active manager; market activation deferred')
        market=state.get('market_simulation')
        if not market:raise ValueError('Market has not initialized')
        if current['active_revision']==target and market.get('supply_activation_revision')==target:
            return host._json(dict(result=True,replayed=True,revision=target))
        if request.get('revision')!=current['revision']:raise ValueError('Configuration changed; reload before activation')
        old_settings=copy.deepcopy(current['settings'])
        saved=control.set(dict(revision=current['revision'],settings=settings))
        try:
            stamp=time.time()
            legacy=market.setdefault('legacy_supply',[])
            moved=0
            for tier in engine.supply_plan():
                previous=market['rare_books'].get(tier['key'])
                if previous:
                    for row in previous['rows']:
                        archived=copy.deepcopy(row)
                        # Visible quotes and consumed history retain their exact values.
                        # Unquoted future opportunities are cancelled by the new policy.
                        if archived.get('price') is None:archived['count']=0
                        legacy.append(archived)
                        moved+=1
                period=tier['period']
                boundary=int(stamp//period)*period
                # Existing stock is moved above before the existing generator runs.
                # An expired empty batch lets it create this five-minute interval
                # under a new epoch; no classes, worker or global hooks are changed.
                market['rare_books'][tier['key']]=dict(epoch=(previous or {}).get('epoch',0),start=boundary-period,
                    period=period,slots=tier['slots'],chance=tier['chance'],pool_size=tier['pool_size'],rows=[])
            engine.rare_stock(state,stamp)
            market['supply_activation_revision']=saved['active_revision']
            host._save(state)
        except Exception:
            # Save may have committed before returning an I/O error. Its receipt
            # decides whether to retain the new configuration; never replay state.
            committed=host._state().get('market_simulation',{}).get('supply_activation_revision')==saved['active_revision']
            if committed:return host._json(dict(result=True,replayed=False,committed=True,revision=saved['active_revision']))
            control.set(dict(revision=saved['revision'],settings=old_settings))
            raise
        return host._json(dict(result=True,replayed=False,revision=saved['active_revision'],check_seconds=60,
            batch_seconds=300,preserved_rows=moved,policy='one independent opportunity per minute and tier; no weekly wait'))

def clean_pack_definition(host,itemid):
    import copy,re
    out=copy.deepcopy(host.item_def(itemid))
    if itemid not in host.PACKS:return out
    raw=out['name'];top=re.search(r'TOP\s*(\d+)',raw,re.I)
    if '传奇时刻' in raw:family='传奇时刻'
    elif 'ICON' in raw:family='ICON'
    elif '怀旧神兽' in raw or '经典8赛季' in raw:family='经典赛季混合'
    elif '纯传奇' in raw or '经典传奇' in raw:family='传奇混合'
    elif '精选球星' in raw:family='巨星混合'
    else:family=raw.replace('臻选新期·','').replace('·抽卡版','').replace('·印记','').split('·')[0]
    grades=[g for g,w in host.pack_grades(itemid) if w>0]
    strength=str(grades[0])+'强' if len(grades)==1 else str(min(grades))+'~'+str(max(grades))+'强'
    kind='指定球员包' if out.get('category')=='DRAFTPACK' else '球员包'
    name=family+('BEST'+top[1] if top else '')+kind+'（'+strength+'）'
    out['name']=name
    description=out.get('description','').replace(raw,name)
    out['description']=description.replace('臻选新期·','').replace('·抽卡版','').replace('·印记','').replace('怀旧神兽','经典赛季').replace('经典8赛季','经典赛季')
    return out

"""Atomic same-SKU random player-pack opening; normal and choice use stay native."""

def _pricing_base_open_pack(host, query, body):
    import json
    try:
        request = json.loads(body or b'{}')
    except (ValueError, TypeError, UnicodeError):
        return host._json({'result': False, 'reason': 'INVALID_PARAM'})
    if not isinstance(request, dict):
        return host._json({'result': False, 'reason': 'INVALID_PARAM'})
    if 'bulk' not in request:
        return host.ep_item_use(host.hot_path_params['item_id'], query, body)
    return bulk_open(host, request, host.hot_path_params['item_id'])

def bulk_open(host, request, token):
    import copy
    import re
    if (request.get('bulk') is not True or set(request) != {'bulk', 'requestId', 'expectedRemains'}
            or not isinstance(request.get('requestId'), str)
            or not re.fullmatch(r'[A-Za-z0-9_-]{16,96}', request['requestId'])
            or type(request.get('expectedRemains')) is not int or request['expectedRemains'] <= 0):
        return host._json({'result': False, 'reason': 'INVALID_PARAM'})
    with host.STATE_LOCK:
        # A detached transaction is also safe when a host caches its read snapshot.
        state = copy.deepcopy(host._state())
        coach = host.my_coach(state)
        slot = host._default_slot(state)
        owner = [str(coach['_id']), str(coach.get('appat')), str(coach.get('_admin_generation'))]
        fingerprint = {'token': token, 'expectedRemains': request['expectedRemains'], 'owner': owner}
        saved = coach.get('bulk_player_pack_receipts', {}).get(request['requestId'])
        if saved is not None:
            if saved['request'] != fingerprint:
                return host._json({'result': False, 'reason': 'INVALID_PARAM'})
            return host._json(dict(saved['response'], replayed=True,
                                   items=host.coach_items(state, slot),
                                   playerCount=len(state['teams'][str(slot)]['players']),
                                   resources=host.coach_me_resources(state, slot)))
        visible = next((row for row in host.coach_items(state, slot)
                        if str(row['_id']) == token and row.get('remains', 0) > 0), None)
        if visible is None:
            return host._json({'result': False, 'reason': 'INVALID_ITEM'})
        itemid = int(visible['itemid'])
        definition = host.item_def(itemid)
        product = host.product_packs
        risk = product.get('risk_packs', {}).get(str(itemid)) or product.get('strength_packs', {}).get(str(itemid))
        catalogue = host.pack_catalogue.get('items', {}).get(str(itemid))
        if (itemid not in host.PACKS or definition.get('category') != 'PLAYERPACK'
                or definition.get('draft') or risk and risk.get('mode') == 'choice'
                or catalogue and catalogue.get('mode') == 'choice'):
            return host._json({'result': False, 'reason': 'INVALID_ITEM'})
        stacks = [item for item in coach.get('items', []) if item['itemid'] == itemid and item['remains'] > 0]
        available = sum(item['remains'] for item in stacks)
        if available != request['expectedRemains']:
            return host._json({'result': False, 'reason': 'PACK_STOCK_CHANGED',
                               'resources': host.coach_me_resources(state, slot)})
        team = state['teams'][str(slot)]
        count = min(available, max(0, host.MAX_PLAYERS - len(team['players'])))
        if count == 0:
            return host._json({'result': False, 'reason': 'Exceed plyer limit'})
        players = []
        # Capture the original stock: any cadence exchange reward is for a later click.
        left = count
        for item in stacks:
            take = min(item['remains'], left)
            for unused in range(take):
                players.append(bulk_draw(host, state, coach, team, itemid))
            if take:
                if risk:
                    item['product_open_seq'] = item.get('product_open_seq', 0) + take
                item['remains'] -= take
                if item['remains'] == 0:
                    coach['items'].remove(item)
            left -= take
            if not left:
                break
        remaining = sum(item['remains'] for item in coach.get('items', []) if item['itemid'] == itemid)
        response = {'result': True, 'players': players, 'opened': count, 'remaining': remaining,
                    'itemid': itemid, 'limitedByCapacity': count < available,
                    'playerCount': len(team['players'])}
        coach.setdefault('bulk_player_pack_receipts', {})[request['requestId']] = {
            'request': fingerprint, 'response': copy.deepcopy(response)}
        resources = host.coach_me_resources(state, slot)
        items = host.coach_items(state, slot)
        # Cards, inventory, pity/marks, and replay receipt commit exactly once together.
        host._save(state)
        return host._json(dict(response, items=items, resources=resources))

def bulk_draw(host, state, coach, team, itemid):
    product = host.product_packs
    risk = product.get('risk_packs', {}).get(str(itemid)) or product.get('strength_packs', {}).get(str(itemid))
    catalogue = host.pack_catalogue.get('items', {}).get(str(itemid))
    cadence = host.pack_cadence
    data = cadence.items.get(itemid)
    origin = None
    if risk:
        tier = host.random.choices(risk['tiers'], [row['weight'] for row in risk['tiers']])[0]
        spid = host.random.choice(tier['pool'])
        grade = host.random.choices(range(1, len(risk['grades']) + 1), risk['grades'])[0]
        origin = ('product_pack_origin', {'edition': product['edition'], 'itemid': itemid, 'tier': tier['name']})
    elif catalogue:
        spid = host.random.choice(catalogue['pool'])
        grade = 1
        origin = ('pack_catalogue_origin', {'itemid': itemid, 'edition': host.pack_catalogue['edition'], 'mode': catalogue['mode']})
    elif data:
        ledger = cadence.ledger(coach)
        pity = data.get('pity')
        if pity and ledger['pity'].get(pity['key'], 0) >= pity['after'] - 1:
            tier = next(row for row in data['tiers'] if row['name'] == pity['tier'])
        else:
            tier = host.random.choices(data['tiers'], [row['chance'] for row in data['tiers']])[0]
        row = host.random.choices(tier['pool'], [row[1] for row in tier['pool']])[0]
        spid = row[0]
        grade = host.random.choices(range(1, len(data['grades']) + 1), data['grades'])[0]
        origin = ('pack_cadence_origin', {'edition': data['version'], 'itemid': data['itemid'],
                  'tier': tier['name'], 'issued_at': host.w3c(host.time.time())})
        if pity:
            ledger['pity'][pity['key']] = 0 if tier['name'] == pity['tier'] else ledger['pity'].get(pity['key'], 0) + 1
        ledger['marks'] += data['marks']
        ledger['opens'][str(data['itemid'])] = ledger['opens'].get(str(data['itemid']), 0) + 1
    else:
        pool = host.pack_pool(itemid)
        if not pool:
            raise ValueError('Random pack pool is empty')
        spid = host.random.choices([row[0] for row in pool], [row[1] for row in pool])[0]
        grade = host.pack_grade(itemid)
    card = host.add_player(team, spid, grade)
    if origin:
        card[origin[0]] = origin[1]
    if data and not risk and not catalogue:
        cadence.exchange(state)
    price = host.player_value_price(spid, grade) if risk or not catalogue and not data else host.card_price(spid, grade)
    return {'_id': card['_id'], 'spid': spid, 'grade': grade, 'price': price}

def pricing_legacy_data():
    import json,zlib,base64
    return json.loads(zlib.decompress(base64.b64decode('eJztnV+PHNURxb/LSnnCD3Or6vYfC/HAJ4h4jZDlmAVZMTayzROyZBxbNsQYEgg4YAWcBIhEQmQpwQTs5MPEs7t+4iukZ2dq78ytHjPbiK7t5vhpNJ4pn6k706dOSf71a1tl4DgJk7B1/LWtsydf3t46vvX4+m9337g5ffDN9Ob7e//94+P3Xt/9y4PpzWtbx7bOn3v17AsXto6HybGtCxe3X2ke/kIrHFs8IH3A+kD0QXx+UeKEvvmQ79aXF/pcqQ8qfVAvHoTJwcuDVg9aPWj1oNVDqh60etDqQasHrU6pOml10uqk1UmrU6pOWp20Oml10uqcqrNWZ63OWp21OqfqrNVZq7NWZ60uqbpoddHqotVFq0uqLlpdtLpoddHqcfJ8c8qvnDz1q5MvbV+Yfa0O9xU7de7sxe2zF/e/HHXZvG/SnHac1Xxh+8Kp86dfuXj63NmmxPTtK3uXf/3owSfTT6/vfPDV9Ma3O+99tffB2/NyO7//597DL+Nk9mf3yr+nN77e/fDq4z9d3bnz8bM/3/nHe4/+85vvHtycv7aIP9v78u6jb+9/9+CjnTt/a943vXYvlFxOqvlbm+enH30z/fLD6a2Pp2/d3bn3yfR3Kv7zq9Mbf/jf5Sv7yl89e3HreGw+/fnTp5qPyVXV/E7OnT/90umzJ8+cWDzbdKOQY1svnjx18dz5reOT2cu3Xz796ssnFgWaZ148febM9vkTqeKZk7/cPvOkxl06pn2mDn2uZm1ufnuhOeqDptcDanqYpK5P6ua3YtpOXDdf1oO2B9P2kLe9PlTbuXPb+Rgttz1UA+o7pb6XIRZVS9+bH8Ek9Z1M3ynve3O1PUzjpUvjuel1c7mV5cZTMaDGc2p8YwRFJW2dLxqPOei8mM5L3vnGmw7T+di18434arnzXA6o87J0gW9sr63zHMtq6RJfmc5Xeecbuz5M5wt4aS9eWsJLPby0gpf6eGkNL/Xx0jCBl/p4aUAu7cVLA3Kph5cG5FIfLw3IpV5eilzq5aXIpf14KXKpi5cilzp5KXKpk5cScqmTlxJyaS9eSsilHl5KyKU+XkrIpV5eilzq5aXIpf14KXKpi5cilzp5KXKpk5cycqmTlzJyaS9eysilHl7KyKU+XsrIpV5eilzq5aXIpf14KXKpi5cilzp5KXKpk5cKcqmTlwpyaS9eKsilHl4qyKU+XirIpV5eilzq5aXIpf14KXKpi5cilzp5KXKpk5dG5NKevfTS4l/OEEhzn0monsUVMEFkFj/NBDfRr0yCbuhHSTCIlaplXrXKq9Z51dl/P16tGjKtIdcacq3BaA1Ga8i0hlxryLUGo5WMVsq0Uq6Vcq1ktJLRSplWyrVSrpWMVjZaOdPKuVbOtbLRykYrZ1o518q5VjZaxWiVTKvkWiXXKkarGK2SaZVcq+RaxWiNB1ov6SWOVgBj82vR9P5fd25/nF3i1jLsSCl0pBQ6UgodKYWO1jLsNn63vrzQ50p9UOmDBUuNEsOOlGFHyrAjZdiRMuwoMexIGXakDDtShh0pw44Sw46UYUfKsCNl2JEy7Cgx7EgZdqQMO1KGHSnDjhLDjpRhR8qwI2XYkTLsKDHsSBl2pAw7UoYdKcOOEsOOlGFHyrAjZdiRMuwoMexIGXakDDtShh0pw47WMOw2/oqtumjBVDZG1H8uis0YXfLmvvn0s88907y5qf/4i9vN3+2+cWP66fvTN+/N3vzW3eazzd+wc+fyo4e3nqqaf3167f6jh+/ufHZl99b1vc9fn75ztXnVmojVfKfqaA04lrGuu2astYeQLgvU5cz2J58wz1h6gP1nrCNxgEtxLZYSWk5QKp50jmsbnCB3OcH9uFbOU4OeYOg/NRyJI1xKfo3NT9o2HXWcQVifEP1MAAnFoQ5ROh9iNQ8geohEP81DXEqRHLmY2Z3dV4VCZoPU+hxp0kzj+Ic5xtj5akqzn9/yOf5Er6dLmbRoLpzSTIl2HRDKGZv3Cal09uvLDvJwF9UCo8zgRpkSo8zAR5kKo8zwR5kao8wIRpkV5CJGmeGOMgFbmcGNMgFbmYGPMgFbmeGPMgFbmVGMMtjKjGSUwVZmeKMMtjJDH2WwlRnBKIOtzBhGGcJWZhyjDGErM7hRhrCVGfgoQ9jKDH+UIWxlRjHKYCszklEGW5nhjTLYygx9lMFWZgSjDLYyYxhlGFuZcYwyjK3M4EYZxlZm4KMMYysz/FGGsZUZxSiDrcxIRhlsZYY3ymArM/RRBluZEYwy2MqMYZQRbGXGMcoItjKDG2UEW5mBjzKCrczwRxnBVmYUowy2MiMZZbCVGd4og63M0EcZbGVGMMpgKzOGUSZiKzPsUcaS2/fBvwtvTlTZxaU+QUr1wpGIlwffwkRPPPhAicO3WrnMK1emcm0qz2BGWeWQaw655mA0B6s5WM0h1xxyzcFoDlYzWc2Ua6ZcMxnNZDWT1Uy5Zso1k9FMVjNbzZxr5lwzG81sNbPVzLlmzjWz0cxWs1jNkmuWXLMYzWI1i9UsuWbJNYvRLFZzTJoPCO+8gt/e/fbt6bWv9/710fTvf86urGsJ76yMdlZGOyujnZXRzmsJ7xu/W19e6HOlPqj0wYI0zonwzkp4ZyW8sxLeWQnvnAjvrIR3VsI7K+GdlfDOifDOSnhnJbyzEt5ZCe+cCO+shHdWwjsr4Z2V8M6J8M5KeGclvLMS3lkJ75wI76yEd1bCOyvhnZXwzonwzkp4ZyW8sxLeWQnvnAjvrIR3VsI7K+GdlfDOawjvG3/Fjsidr4pJKOv6x7jzVV2WRdk1cq5tXPopU4c+78+6IXjf+ap705dyYphEqtv6Xs2uGx2D4gZ95859J/dbX3Vv/FK6awxpdk+jtlwQ+Ynx7ok3v9qg9dK59ex+86vurV/KZFLHKC23HQuhqporete7X23Q+til9fuRjN3vftW99UsxKnBZtd7yLRRVuRyHD3n/qw16X8BRe3HUEo7q4qgVHNXLUWs4qpOjrsCz4ai9OmpARu3FUQMyqoujBmRUL0cNyKhujoqM6ueoyKj9OCoyqo+jIqO6OSoyqpejEjKqm6MSMmovjkrIqC6OSsioXo5KyKhujoqM6ueoyKj9OCoyqo+jIqO6OSoyqpejMjKqm6MyMmovjsrIqC6OysioXo7KyKhujoqM6ueoyKj9OCoyqo+jIqO6OSoyqpejCjKqm6MKMmovjirIqC6OKsioXo4qyKhujoqM6ueoyKj9OCoyqo+jIqO6OSoyqpejRmTU3h3VcvL28Ulzt0mYH70OJgCN/kATF0W/NwnXcfBxEkVipXBpClemcJ0Xnv2v5axwyBQHozgYxcEoDlZxyBQHozgYxcEoJquYMsVkFJNRTEYxWcWUKSajmIxiMorZKuZMMRvFbBSzUcxWMWeK2Shmo5iNYrGKJVMsRrEYxWIUi1UsmWIxisUoFqM4JsUHdDyZ2JuIzK9V2SVwLR1PlG8nyrcT5duJ8u1kLR1v43frywt9rtQHlT5YUNok0fFE6XiidDxROp4oHU8SHU+UjidKxxOl44nS8STR8UTpeKJ0PFE6nigdTxIdT5SOJ0rHE6XjidLxJNHxROl4onQ8UTqeKB1PEh1PlI4nSscTpeOJ0vEk0fFE6XiidDxROp4oHU8SHU+UjidKxxOl44nS8WQNHW/jr9hqdqpCPanEA+6+9Nau2SnGqgXnHZqrsPwwIHtL49JP2d5b5vv7PB8ki0V2WjTdASDcuelL2YnKumhre1kH6hqdNmi7vSHMpm0vF9Fp0XaH6NS978voc5rUoSU6za/qXZPTBp2XLp3fH99lkZwWnXdITt07v5ScKE6K2Nb5uNL5QwanDTpvb7yyaefjIjgtOu8QnLp3fjk4EdUcWwjjQao44c7BaYPe23ulwE5/DDu19zeBnfZgp/amJLDTfuzU3kkEdtqLnQZ78w/YaU92GpBOe7HTgHTqYacB6dTJTgPSqZedIp362SnSaT92inTqYqdIp152inTqZKeEdOpmp4R02oudEtKph50S0qmTnRLSqZedIp362SnSaT92inTqYqdIp152inTqZKeMdOpmp4x02oudMtKph50y0qmTnTLSqZedIp362SnSaT92inTqYqdIp152inTqZKeCdOpmp4J02oudCtKph50K0qmTnQrSqZedIp362SnSaT92inTqYqdIp152inTqZKcR6bR3O7X8u31A0txqEshncRFMiBn9dSb0iX5rEpLj4NMkUsRK3TKvW5m6dV53n363WjdkekOuNxi9wegNVm/I9IZcbzB6g9FLVi9leinXS0YvGb1k9VKml3K9ZPSS0ctWL2d6OdfLRi8bvWz1cqaXc71s9LLRK1avZHol1ytGrxi9YvVKpldyvWL0itEbk94D6l1sQ5Ldvz9950Z24VtLvYvKrYvKrYvKrYvKrYtrqXcbv1tfXuhzpT6o9MGCvhYT9S4q9S4q9S4q9S4q9S4m6l1U6l1U6l1U6l1U6l1M1Luo1Luo1Luo1Luo1LuYqHdRqXdRqXdRqXdRqXcxUe+iUu+iUu+iUu+iUu9iot5Fpd5Fpd5Fpd5Fpd7FRL2LSr2LSr2LSr2LSr2LiXoXlXoXlXoXlXoXlXoX11DvNv6KrXprwVQ29uQQlxq3qHhzN3362eeead7c1H/8xe3m73bfuDH99P3pm/dmb37rbvPZ5m/YuXP50cNbT1XNvz69dv/Rw3d3Pruye+v63uevT9+52rxqTfIi4rolA0jFk+oHRi97COmy0LLJ/P4z25+HFtFLD9Aheh2FA1wGmXNz/SZ7hBVz0RlkvsERtmxFNzzCBchcj9Ajxh2FM1xKhHWoQlW0DMeTKpbdmegbnGLLhnXDU2wu48unSPzTPMWldBmaGTPObtrwPfGyNKdYmnjJhzrFlm3thqe4wKvrKXrEy6NwiktJteBiIm1B9YeB2jc4xZa9LwaZIz7ItOyQMcgMa5Bp2UdjkBncINOy28YgM7RBpo3PiEFmaINMG+kRg8zRHmTaqJEYZAY1yLQRKDHIDG2QaaNZYpAZ3CCDjcwYBhlsZIY3yGAjM/hBBhuZMQwy2MiMYJBpY5JikBnaINNGN8Ugc7QHmTZSKgaZQQ0ybdRVDDJDG2TaCK4YZAY3yGAjM4ZBBhuZ4Q0y2MgMfpDBRmYMgww2MiMYZNo4vBhkhjbItBF9Mcgc7UGmjQ6MQWZQg0wbaRiDzNAGmTZqMQaZwQ0y2MiMYZDBRmZ4gww2MoMfZLCRGcMgg43MCAaZNvY0BpmhDTJtFGsMMkd7kGkjYmOQGdQg00bXxiAztEGmjdSNQWZwgww2MmMYZLCRGd4gg43M4AcZbGTGMMhgIzOCQaaNt45BZiiDjCW370N+F86cCLJ6oU9AUr1sJLjlwVcwkRL18yTq3mrl0lSuTOXaVJ6hi1Yrh1xzMJqD0Rys5mA0h1xzMJqD0RysZjKaKddMRjMZzWQ1k9FMuWYymsloJquZjWbONbPRzEYzW81sNHOumY1mNprZahajWXLNYjSL0SxWsxjNkmsWo1mMZrGa44HmS5cu/R/2Grhm')))

def pricing_data():
    import json,zlib,base64
    return json.loads(zlib.decompress(base64.b64decode('eJztfW2vJUeR5l9B9yuNnRkR+eZvQ8urHU2zWFo8XgkhlK9grem2/LISi5DMImN7Bi8eCfyCLQNaEOwyMCw7gxkbDxK/xfe2+9P8hY2sc2+dqjx1z61zuqm61oxlaOe5t6ueek7kExEZGVnfOHk2fjV/zZ88Im+cPH3nqSfj108eOfnK8/4Zf/u5nNNnvvKMT/kzTz/lv56f+czXcnrS3/7Mf5MnN07C019+Oj/z5afvPHn7Of7bRinpHlJ8kWeejPnZk0e+caKEAHnyCNw4sVLUf3hAqAWef8D/2/5U1YHbDOqYL2lvnDjTDejkES1dP1T8QwnbH+uTR8x2ZE4esajPh909COTFUPIQkczFGOtYGqxj5F+2VJ9lc2uG5OpfV91vU4eYR7L/ZckPpGw/gu4B+Dd5APyb3ZN2w82TKkN1bKUb3mbDDVSUHczNGLsbiX7MDyX5g+0vWP6F+ufFBxWLk91zb8Z8RQngVP8BVghKbf8G02YNbf9GvQeBq09rgWx3D4lUn8l2D8hXwH5Aw4EaDvi6avC3+LIgne7HtgLtR45/atXFsNKG1vRDWb9pJ/oxNGNGxOz2Q8akYPu3GYgj0SOBahmkt2NbSUfqx4yFSPUPUm1Dkewvj3LwJXQfwOBL6D6oDAHqHgJ23zOp/h7ITMHor+j2GgPWSdrO5ixtvsc6thUFM9GPYfBzBFNnmdwg6IaVMr3hiGhzOee2Y7uheDuG7c91/fv8+6YfyPOZthnVX1X9qD77YFi/C92PLgykG+jhwAwHdjhwg0E3b/tBVRXZo6qmvv0ZDgc0HAwxyCEGOcRQ7fPcfLthNVDofwpDHJ26nZt2N4YRBTCEAkMoMIQCQyjVRvV2VG1Bb68/ZKRaJ1trP6zfoxX9cMgJDoHgEAgOgVRTlLgdDlnB4TeDQxxUcfQDeTG5uxH0k7sbVhg9QhriIHU+7/n7U1WXq1ZRP6wPA3WKnI/5QkZZ6Md1loGtX8T5B/VyVaP6D/T4gqa5oG0u6JoLduY3vKAcI5QNQtkglC1C2SKUY4SyQSgbhLJFCC1CGCOEBiE0CKFFCC1CGCOEBiE0CKFFiC1CHCPEBiE2CLFFiC1CHCPEBiE2CLFFSC1CGiOkBiE1CKlFSC1CGiOkBiE1CKlFqBqE0Kk91CDkfNy5fdlfEupcIUSt+w8YJGilUPWfqM5tdrHC+Se6uappr2rbq7r2ql2sNLqqbLDKFqtsscodrHIHq2ywyharbLHKHaywgxUarNBihRYr7GCFHazQYIUWK7RYYQcr7mDFBiu2WLHFijtYcQcrNlixxYotVtzBSjtYqcFKLVZqsdIOVtrBSg1WarFSi5V2sKoWK469ENappXHw4xp8autM/0FNU4ypscP5BzVR4aDJbv+OHl/SNJe07SVdc8k6q8aXHHsilA1K2aKULUq5g3Lsi1A2KGWLUrYoYQfl2BshNCihRQktSthBOfZHCA1KaFFCixJ3UI49EmKDEluU2KLEHZRjn4TYoMQWJbYoaQfl2CshNSipRUktStpBOfZLSA1KalFSi1K1KKnOHqUs9eM605VB3X9Qw0Gr+6iP6vzhsFBuL1FxckImbf+Jbi5q2ova9qKuuWg3g0YXlQ1S2SKVLVLZIpU7SGWDVLZIZYtUtkhhByk0SKFFCi1SaJHCDlJokEKLFFqk0CLFHaTYIMUWKbZIsUWKO0ixQYotUmyRYouUdpBSg5RapNQipRYp7SClBim1SKlFSi1S1SJVTaynurSIjKb+A0aqnYLtbzBSqzgo7D/oZr7RUvef6Oaipr2obS/qmotufNLwok2kp2SLVLZIZYtU7iBtAj0lW6SyRSpbpLCDtInzFLRIoUUKLVLYQdqEeQpapNAihRYp7iBtojyFLVJskWKLFHeQNkGewhYptkixRUo7SJsYT1GLlFqk1CKlHaRNiKeoRUotUmqRqh7pN+sy9Z07ZbBK/Y2T2/5r+eSRE44aP/r9S5969LFPnb76k5MbJ3eeSnzh83Xtbr36vz55mz86eerOc8/lZ75el8L9s/nL5z9XD2ln0HBsqZWrq4/fHC5/93f57GNnL7927wd/PHvn5cFtzlfHzy91Pjq/3dfu3H7uq0/V20X+r3z7uYs7OnbM8iE2dnSWs+666JaefDbeeb6uy4uH6tB//dmaN35zuPDeQzn9w/un33397v/457Mf/Kb+5BwLTjxyeP52eirvQoCHxPim/VOrS2+ltreSor+Xu/JeUlx2s03Z4LLn6u8G27tVbb3q0SZvt61L9Lf76A8/Pv3ZS/rjf3r79Ff/60/v3fvh987eef/T9l8/fPfTsr+3NWZ7966kcX77Z/ztdOdrF7bUFV34t3l45/bz/N0998zz+fxn4elasRDg2M66ms2dp7787JP/PVf30Q+/cts/9/wzFRY4sFHzv559n2GTct6o7IvPQCn7pJ0tHpX2MSYHzooYTeGw1HkdtSvEkIqPz915pj56zZaif7pfwo7+qfj8U/65nM6fpgPOeL/4RXvDiC/d+KK7AYr/4G9YfelLW+LUgLhHbz38+K2Hbz566zN/8fATt/70XsuZtFDjzIuvrCv8HMUaz0hNNV0ZsVYlZoe1oLUwCr2DSJh05kRMeAMBbfTkik5QXMgxeC/5P+vKRQ5UlM8SNH9sZrO2eZwhbaQ62khsaJMj3vSAt7sffO/0xd/bC4M7ffU3H//6N6dvv3/66x9+2vbksSz03JnZzBX/1LMjg7OmrtvbMXO1ErZDXXQUIYeQhXU5ywCBhUkVjma1i8yp5bDH+WI5NE/ALgmy5WcrMhR2WD6W2dSZhjjmZ0iVGVB187GHbz328M2bDz/xWSZqQ9HAwDgrMz1JXe1wH0tVrS6hiWN4ydlzjeoGPMEUTZilTlYpI3zguJAJCZbYdYZidEFvMYEU2cZoveZ/JflC1hU0Njhbl1rm0tQ9z5analJDosa+QNLGnL7w+cf4Bxcq1hoVpwxbFeuKq8dZFT+hZYtwjVnVJ9jhi1M/yylpzCE6l4KWmFKWpJkVK0wKwfIkRetDEMxW8T4q470OtrgImOebVfc8l9pVVwlopOuJW5/q+OpF3/WuhlPirWVt6s77qHKXUiW14cckKxvxmqIqZC9UBis827W3nN86CJCVLkoHnmYREThDIZsllmA4tMKcDDGHUoecxWyqNg+05co1XOGQK91bFraG1fPFKZLYhlqbuvyRfCnHtuVIqxFfOMlXijKDShy3BR90kB5lElhYrWTKmnNZ9gMYSrU/wVTJ6i1tMZEzY37QOJ+v7oGm+brYfNDEE2dv/O705Q8avmTPV7eF4MIzGnmFvsvL6WI3oThvoTFdclK6THLZ+2IUh7cyueBklBBTSVlEnpIqgKNANpFA5ZAnI5Mro9eCfae2IszmC9CO5qIc8HWxOaPn6+yNn9995eU/vXf3/X/YUHf62sv33v5OPyl1F1X01LFH285MdcW81JeFFMCxCSOhxi9OhRTRS832bZmKpDm/M85mDjNYSg07woBRG2C+gJktJXEKwYqXEgiKhqOPYmezpkZzUt9AjmA5ljA3wHb/YTkke2gTm8nNj1hF9OY/mOGHLhi+2PDSWOS9X75ZI+tXv/XxH9+9+9M/nH73xQGlejt7u30yVwTXPN2no+uL3TV7vt2f/vzuh2+cfue3py/x9Gi/XZ6zsEVyxbTY8+2yeKIzzberpuaEK0A8CbT3bLWGJ0PiSCf5QN4IKEFxXO2pgJBOZE7YgvP8ryDwSYHSMP/btQ/m273YsbTD8Ee//+Dsn77FX/HHL7zIX+4ut1Lh9lu+IoO5lFqq60hmPG9QT6kz0wjMopBROI6MjIboCyAmwx9wzIjkAquziooTIhYeC56sx8w/da6umsxl1j2gaXO+jWk7bQaEfvT+d3nmMK3jmaMs1YWMi7xQXD1z9GUzh9qQbnj7u2/9y869q+irrRfZ7FK7Kim2+pLbX2xu25rVCy+wZbFW3Pv+t9i4Bk7t353ZhTPrtwD2rH380gf3Xnjl7PXfnL3zIxa9LtPbcHceP+0kMagt0SAovyoq35fFGMEPyv7RXh07GSMocJISsBBHSN4lF6VVmYWQEximM3AYHrJK0YNIlqP1oLMzWakijQc/oo/d497AfByZDzOZftPk4QxufQbhIFjf7L7cy+DlFqgMx5+A4MR6DKoJ39E904DBHRs0cxmUAwbhgkF2Kkptp/Bmq+ReCmFPwmM5XFKmdRJ//oxnP4fnTzUgEVoS7TEkYr9E6JTeLtmcI9hLIl5KoqnugNmw14zE848GJGJD4ij4G5O48Sh3f/bu6YsfWvvR+++f/d8fT0xn/qKABgvL8sp1nT0eRdSNtlRD4hGP1k7w6NBb4OzRCdBOKP7vzGlk4YDLWaMU55PZFA72PeoEikqIIRUtY6y1aY5hDuBx81B7JrS83KkMabxMEqVxYAZOebOf/FgS0dR9ixa0vFoVRZLFGcPZkZIhl2zQWlE4niteq1SLOAmcDYkyIMfoPls2WoNg2SIp63TIjN481T4WL3cs+42xV0ZpwSINgqxuH/6R0ghsiewLOX6Ga2WN50+1RxqlvpTIYWQ4NsdeGYHxDtZpu9aFfRRerovsVBRnB4ZmrA4VkGxTIIOOwXBoBJzekyo1d8dUWAqdEkG7lIkTOzZKTZG9N4fBbOsq6XhAhLN5pC1/O6J4uXu+nD7qvTNL9jYpPu/02Mcf7VtdQxCasyt3rQg8f6gtgzRg8KKlpWfwc4/fOnv7Dx9/6/sb8v70Hsk6gV/536cvvtilwhc1vD7GVri1v02PxnEL39po9qWSxgE2yQn2EqtTTjwxU1ZUSyeUODYsIliVgi+obC6aEzinfNEhRXCegybg39LEgeIBlajueSYXvvvun0FB5d6bP7r3gz9ySPPat0//7s1xnYBl8W8+PH31J0zidiV8u6x7LGtSkuzK+UPOYGo1xsmSoPA3XoxjZrIIIjjFvLHFBiuLVY6dCid2GvmaLrtAGZNOyUjvtJpfXMG9jA3z4FuPnf7xxx//ww+XZYwfrq1GoZgyM2+KE8lY64JEKBwKmsQRVGEjlTxp2QSdibFoX+ctBpsSh3wovSq2xJzmr07uZ2xYF7558+wff3vvrRdPv/Pj0++8PZ83c/+8WeagKXZ2O4V3w5RohHOWnBXJ8UzM6ApncD6yyWUZ+f+sClRqLSRLMLGGpMoJpwwaS0k/INr0qCZ19vc/Z+YuRG0ubRzdb7OO46WNnXTds0pjxyDNBHkoEicVUooitNdAHJwkpTj9tT57StlGYgOT7CGolu61djFbzRmJsTLVfWmz10yvULahW3381t0PXj5791sH0mcUDDbMdD1hx4pc7cUhB+PQZMr4bExFWRMyB28sYix5EC0oW6AUTtCCAY7sBPtdiIVypoIxcfynSzEsjiLN5m/zPHsIHHrVJz770e9fv/uD756988JHH/6/2QR2fZp9rnYse6RU3VGBYx8xte7nvEmWZV/VAART9pw+MFc+u8TRSK27pyBjiBpQBWOjdIX5y1qBZymI8/fFuMvKyX3/65a6WxvqDrQ9iW6QWtgrMrR93qLWMzWNc1wzxZ5yUYaAnmMTmYGZ8jp4m3xKUga23sSe2qESmtil5FxUEjIbXUwMshyye6F7nMvpGy2071T+5kqfoG2O23UhHsmfQ22Qmpm7cjWwe549BMopAs/XpqTgDEP2mcQUd7WKM9ib5a7Iai8nTznNxrIpIF6X/Q2b59lD3nB15fTFX5y98+q/MzePObzUY8xnkPSAQHG0z+haUbSDq+krSmRHJtXlfXa7ATGbgNnVnSIc8nEKlnMUmChF4ZNLqZAGG9BxJC29PIA+sddpAF3qNOazx/n71mt0pyYcGfBptIrD2hn8EScZgYJnwdPAUatVpTjvfRS6hsqqxMJOJbKVFpQYnXGaJS9rgSahP8BrdI+zhz+9s6thvIFLygnC3ChE6QZHroRqAQ5kbVlba8pOLoMKwEuXQS/Oz9jWdd/69b0Xfnjvrdc+/sdfsaf99q/uvfGL8w0iczncnMVxRam5/o3JUnN/hMeg0v3C2d//5FBImxNA+ropXl39vgKSO6T8c4FMTOUUhgbNAN3BJMdWdJ3m4E5au7TBXVHR7Z7pkoruxQksh3N5peFtDnX5pE3eK0pq3TPtmb14eUVtD5cw5Tnqqtm/6TLvxeE/h/NJE3xq4sRrW6mcU/K9fGmeEy+rlALndrZVX7eaL7WMziuzzbBQVzswtynd5kSmIy0UtdCubupyM7ZeW621EDHYUrerlfo/SKUEzt5KEhw5OiZVFg8luAg2ZZQ2UuHHNzWypAP4PH+qfRZKc8tFAz6nDBScNHrQgrM50OrI0pEjYnhEZoZ+olAxJyRpEplc+81rnQNIK0sJaoOOrv0W2VsOvg14kCr54EHnIFJx+gBfdP5Q06Wji5O7DmZTTQUc1m62pV80mF053dXlxglKS2etFjOMc0E2oZ3sqmXz8krwX978/H/aMHr3t//CnzfzHadWwIjsYA3n/jbNWOTcRIFFnOGSTIycyGthiyKgXChq8gVyZrWszR+2BM520CZVz2wzgRUhReT8UaXaLHRpcfPgTTMXR8cdXt2cWptAGOzj+jdU6Lw4cG+7JPazd+/+8mdM1luv3Xvpe7utY8YaYQcZzZX7Y/YE6aCcQ01Niw9NmZ3T2sTaYydKZs9SEDkmBWcSJA2ZiJ1MwsKzOSTWhijYHotzMvgUJRzUPUbN3hjRsGXlBFtn3/6b09ff2TTgnrdz9lthrHKDHp/NSYbHtXPyk1jrUF8jujaPM7QtNe6ClWqzX9zWP+AGDJmEKbv75Zv33vzdhk+2u45KtQ3EWaLxOOtr9+N/QoxPne+33/DJEQ/UP/GGqX/QDap/qC2t52dWDpYIfnX69odnb/7Pszd+9tE//+3Zmz/qW6u6VofGVsEMd79dFUReaqkWlSMLzWZgmKI2WxTWxoiOCvlsnPeOoMQgSEXBQlfqj6yITibWP1V4Aook6m9oaQ8wVG2OstPzYz/3EvrxS/+H3fY5oT2VYAezXg+Wa+NX79QPZ5f46r4g/l7kwmyaczI3Zzm0bO4s2F4QRo1DGfvkS9wKWkF2sDy7OZD1+MUfcvU0xHFVVE+V5HmyxrrFIykrZYrUnf1nS/KJKmfgIz+qUMELY0r2GCjXfpxkkTP4aObb3+aJLvMr1PiVMWn7vEs9LAAG50lsjrY9zr84I7SGZsvvurRtHueIeUuNf2nMcJ+X4ZhLknPHGWPrZj4htniYm7k4J3nnvIG7v3pFDU4D2ToYNuLXfzNKYLbx9rFeBlEZTY0sqilmPWrgIIx9Nyhbtc+q2uvkBNiodIS6YTPHZPif4k2RSpIhNNoai5zbqNnMHuVjdOu0B2zaeWzi4HyC+YdetHzOP/NCS86mATPnLEYWr5BjqWLrXnSHQXklZNJBoldSlQiykhgt54GO0wef0vwmsvbMiwMYHdWqX3n13vf/1o7PqtlnnYMNJlfFmJfySQata5vy0E35baVNhgglK+lCLFEbl7LPkJ0hGy1YqAc+cGoYrZEQrY4KdOFoOEhZDrDPcXh5EJ04ufFk3JR8CZ3GiO1sx6P5rFGQBoutga7anoz3Qeno9IOdLuRLyASAQWFn9ra7ttO7ap1svNLK/chKH83kcKlS6Ksn+JbB2VtmW7FUimzTDOCmLJH5wWh8VibVYzSSiBxo+1Sbyq0XjqexMFpTUuzP66YWtEV4Ylss7OvzAcs8eDR7w6VJYRZiz9lWGKe6eSxbk64LlJkvqF0WgTMbkJY4gGBPojg8wsz+J0gRYm0SgiBBOys5AWW9OHpj+wHsDTcJCLsIe3xfPa4mkJ7KB63ROQXmT5QSWPNC0VoED9HI2s/CmVoRKWTJ6s7JogSpQjEG6xYVXxc7FmBvuIIr3DLsGeeaDbNqcoGWtCq2lkmkssxZ5piXhc2BI1LZRS2ziTYEH4ys4TiIwhEP8Kw2h23XPp694daLbc3gz8pe3Y7ZrEDqqRAxB44Hi+NMRdfKn5NBJJv4T8psvZCSKp4nbyLhRJKSgOmrjQQxCk7Ayny3cTR7o2WKuoniyrBQ3D99lqPhsfDRZKNFJuW9sUkCKKE5MQysbBwhcj5cjzAEJrHwZC0WXBQR2BlbZXIGTuIVgp9//Nfx9A1Tlv9wc1O7uprEzRlafePAsclfPUlNQrspZcoQPUeMLtWYRQcbqsRlFSKzaUM9V40dcwhGJ6qttEikpRUcYcuSYs0N5fyWle5hjuRymKzUPRNXsXhEz89OBMgG0yz1CDuVPWdR9z5Ex743hJSKUBwva1HqgQ1BMncsgy4Yz+45GHa9UhqnHYlYgGMk5RcwxWFyItUi9Fmtmi20asjnILlLuZ5yaGsTsxees7soNCcnhVDGHFURkYxXidURkuCEjlxxZFxtTE45zU/ujqdvmIjIGeHzA6CPvWizgdt25/Hvroopdq9IyqErJms01mcOY0rhYFopdsecYtSTXnOQGNmNaNZM40XM6Fzm4HEB+kZNfH2j6JUk3r8zPqBBFAynFJx9ZAhQD+AEpbSOUNvCyXFOB+yaQ3AA0XkVrQ6xBEI2P+u1CrgAi8MsZNs8eiWL92+L179p9AAWR6fANg2lV8c3eN9kXvtO0gO4HOYmbZfpVVxaOehnPqC9dMdLfwK6Sw+gdJiwPP7ZTefpRePkVZQyF4O2PzheNNmd1NxpbKRTCaDGoqO1HGkqqSIloZ1OxfCj1I1iwvtMsQirbCgQq7PxqfbBMO/Z1zcrzI4c4WgjHTUEPg44Y5ar+89itDE4TqHl1Lq2cYmN0nOskwR6oZLljCU7kzIG9OzLIYQgU8mcAHImo6LnWMQytcy35dTxzz/HR+2AbSv0jCLW4NTNQ5qgd0zyk9ADfQCrw3Tm5qO3ZrhxbR5UicAaats+JuPKYgMH3kyLK+x1kuQ43BSUtd2heCzWp7rtX7sAWnjBboojqHpme/bRER2Q1RxfIRh1DUr96M0ZNmnve3aTwM2p1FsGHU319JaoshNSxFBfu1gnrbHFc76d2docmx35LNm5s3E6z99LkQVN9CEpzhRFOeAc6aMJHGU25gv/cU4t9b4JVISiOfNr8ihOdhJJOuVlcJLjH7YrCMRRt/b17KP6ojPWBBcT5zklyhRqhpQigBXSsgDMr6Iez58aGeAs/u5/kYyEbRfJ5FQ4ztNVO1KefTk7EKtrnzjPW8PqyJ6F7Qx1ClJLR1mR4WDSMcfKe84oM8/rJfjTowXaJ+ZM4AfhntGJsQQqMVVdYUJkSRTrCyxyCHXbCUrOWjirxCKI2cNUunNfI3sSKpFciTYTcPJeDz5YgMBhPvOFm593MCcl3GbW+mgOJYq63fpKhyyjM8TT0khM1jNfwoN14OoRxy6lTJrVriC7DTZE9il8zYhYS86JQ/E0v76njydxmMh8YYY3llptk5fufdzH5YJgLbr2yLSpiWzqO1QwCysgO4WRshGotPSRmDARVV2X9aKukJGVxH5YFiYzKp7pzs6PE7tnOZLEUa2FvjBnpfsBLPDYmv+NffHUImM0lucrygxC26xl4ZBQAgffoTbocwSTa9d5wOIS1vS6JoScW9dduhzK2wVc8ai19XOP/8VmQ97pT3/+0YczFsu0ttvApnsL/HHpNCsXu4OmajCVTdsSUJpoU9Hgraod+8EL1BHq6jb6klVk0nlyc1LNgY4gYn/DP6uepb62evbrV+jo8HDU4frXM+Y1bN4FdfEusNkncLTz2jmjdOuhpwrQhSexDVgdMufKmkzk5E5Z7YQu2uqUkgLO/6RzgYOfurnRCCODckXICAeYZfcwR7IIo80jjy8SY0+U8BGmJrYVnDNzmlyjRMvUyawDkkzeFo5gTI5Yay78xVrhY/ROAWitS1Bsjl6XBRZuR12sQs+Kce5fGZH47uMkRU02byQjakxoc2Qzs2Q5g4PAQQwHjs6EyJO3vnQ0yWxK0cWnxAZriANJVc83kQvsIBm1rQr76Az+4EHwR6ZZAlOTazg1+1A1r1OseZy4ycSTmc0NqCB7GhGYNxOgduNhinxX9jGcuHiUQAmXMMBRkiLmTOAHYX91DXXMH0zF2EL4nHj+8vQOInoptQ/RFGFMJIraSKE4MuRwRildSqoTXFj+KOgi6iuaFuBvmKR8bk54aIbvJ8RjKdQaJA73F18WHlKs55RqD5CSYf/NMxoUJ3iW57HoFhNzrVTphCJzilL7ylkYeVqLoKs1zvcieDyJw0Tlr//zDBKPOO60zZPrOz+apa7JxgImhR2tNbIEY6HU5tyEmePrSMFFp0w9q5iDwahzBl83wUYDyef6NuBwwJrh8ezZUXA9y4c8gM04ZG3zvrT69oCpOIbqG0OD4Dimvg7Ndkc2iWI4Z06oM+sf1fSOY0FicjnMcRRkt/edQn0D5AIMjtKTGZs4H0QN3xho2vAVTL6UlUWPeAqbAuQwk4/ZclZiOakylgJY2e0qdraefSXBeuvrGzR1SSqGEnGBwimN2lnmrFhv12muOBvi8uyOlR4b/Zuav/VNDIDe6Zysy4ZY+jiWAVAcCGqetJJz5EiRk8XCY4QEPMtz4DBHcw6o5u8goaPZG2Yi7YGoV6946W08c3T32ifgJNQD+BzmJO0pqVfxyR5w8Pru+cej7myL+AScjnoApcM05a9uiRkLicPzFq96OdIeGpXjVG/M4mSqZ3TkyIaKiJHTt/pCkAJ1BVY5G+t2O1LsS1gIUhCQSg5RkLeaOMNWiaP0A15jenSuTMNU5a/+y18uE+ZIztGb0xYny1HFaS8CQklJmcAhNhVOmhUro2aetOCwJ3vrOBoX0Uo2RCAvvbfCAefjC0TaNMxULnlv5541MOsGZM4/tnenRvpJOLV3DqlGsqbIUevkvZf+7u4r3920Sm/ewde//K/vvvdP3u6XaO3gHLJu/2Fz9CG6nff+abW9NdzHrYUbHECPXdt1c3Niu9x3dzz+7oad7nYVyygLO3dni9C07/Z0/O0lp892cKQeexq9C8BZ2su+ug/2JbkBAKwvr9jlX3Omuw+AXs/yzKqWZ9e1PLey5Y06R9awPLme5slVNU+uq3lybc2Ta2ueXE/z5KqaJ9fVPLm25sHamgfraR6sqnmwrubB2poHa2serKd5sKrmwbqaB2trHq6tebie5uGqmofrah6urXm4tubhepqHq2oerqt5uLbm0dqaR+tpHq2qebSu5tHamkdrax6tp3m0qubRuppHa2ueWlnzYHxm86Yq9N4vzt780QwA9YTpweH1oOzE86Pad3c4/u7KkBzeXU5Yn7Ra7n16PP7+7K/EYOYRot79/rU2Uu8DQMcDwPput8F75kGrruG9tQBh1X4S1PEY6glfNGjeV7VdYReDlfU48n0Ydt8Tt6QZmpXN0K5thm59MxyVNlYyQ7mqGsqV1VCurYbyGqihvAZqKFdVQ7myGsq11VBeAzWEa6CGsKoawspqCGurIVwDNYRroIYT7xBe0gxXVkNYWw3hGqghXgM1xFXVEFdWQ1xbDfEaqCFeAzXEVdUQV1ZDXFsN8RqoIV0DNaRV1ZBWVkNaWw3pGqghXQM1pFXVkFZWQ1pbDekaqKFaXw1xVEXZvJN+88anP3v9DkcllANvLYUCt725xolndxbtvtvj8bfn+SNwe3uprTM7969vS93z9eOognIgAHL1XTrb5zfd8QLtJBTESdg+BOo+vgE0dljFlEZIu/slgJYWYB8GvZ4BmnUN0K5tgG5tAxy/RnsdA5TrKaBcVwHl2gooV1dAeQ0UUK6ngHJdBZRrK6BcXQHhGiggrKeAsK4CwtoKCKsrIFwDBYT1FBDWVUBYWwFhdQXEa6CAuJ4C4roKiGsrIK6ugHgNFBDXU0BcVwFxbQXE1RWQroEC0noKSOsqIK2tgLS6AtI1UEBaTwFpXQWktRWQVldAtb4C0kQ/ydkbvzt9+YM5JTFltxUxHuxaoFX7TJAm2klm3xyM04N6nDK4Ww4DArHnC6CJdpLZ95cg3PBkWdu9GLIBoJySewHsloXnE6CEVlsAhrr65E5DFZHdMwtoopnkAArqWY3balw9Hl3uFmUBUOk9VUmaaCZZ0AZ3a8LL2uBuTXhhG9ytCS9sgxOdJIvb4EQnyXI2ONFIsqgNTjSSLGuDE40kS9vgNdDBiTaSBW1wZR2c6CJZ2AZX18GJHpLFbXCih2Q5G5xoIVnUBidaSJa1wYkWkqVt8Bro4EQDyYI2uLIOTvSPLGyDq+vgRPfI4jY40T2ynA1ONI8saoMTzSPL2uBE88jSNngNdHCidWRBG1xZByc6Rxa2wdV1cKJvZHEbnOgbWc4GJ9pGFrXBibaRZW1wom1kaRu8Bjo40TSyoA2urIMTPSML2+DqOjjRMbK0DaqpOsl7752+9vISjUtqqlAy9+4SeQINTn0jo3cngUKyexpm1FSlZC4AJ6202/dMade9/nKnWKbd/i9gQgpnU8AphRq8oskqEBOHz6EUxu2DMKGFcyFo1IIGZmiMlhNiYBDUXkOYkMIFzXBCC5c1wwkxXNgMJ9RwYTOcKpcsbIZT1ZLlzHCqXLKoGU7VS5Y1w6mCydJmuL4aThVMFjTDtdVwqmSysBmur4ZTRZOFzXCqZrKcGU4VTRY1w6mqybJmOFU2WdoM11fDqbLJgma4thpOFU4WNsP11XCqdLKwGU5VTpYzw6nSyaJmOFU7WdYMp4onS5vh+mo4VTxZ0AzXVsOp8snCZri+Gk4VUBY2w6n6yXJmOFVAWdQMpyooy5rhVAllaTNcXw2nSigLmuHaajhVRFnYDNdXw6kyykJm+M1v/n/OcMXs')))

def pricing_ui(value,data):
    import copy,re
    prices=data['prices'];proof=data['proof']
    def visit(v):
        if isinstance(v,list):return [visit(x) for x in v]
        if not isinstance(v,dict):return v
        historical=v.get('currentstep')=='complete'
        out={k:(copy.deepcopy(x) if historical and k=='product' else visit(x)) for k,x in v.items()}
        if 'bunches' in out and 'category' in out:
            key=str(out.get('itemid',out.get('productid','')))
            if key in prices:
                unit=prices[key];out['bunches']=[{**b,'price':unit*b['bunch']} for b in out['bunches']]
                desc=out.get('description','')
                desc=re.sub(r'同等内容基准价\d+点券',f'同等内容基准价{unit}点券',desc)
                desc=re.sub(r'售价\d+点券',f'售价{unit}点券',desc)
                row=proof.get(key,{})
                if row.get('bonus'):
                    note=f'按{row["base_grade"]}强基础档定价；更高强化为额外奖励。'
                    if note not in desc:desc+='<BR>'+note
                if desc:out['description']=desc
        return out
    return visit(value)

def pricing_host(host,data):
    import copy,types
    original=getattr(host,'_host',host)
    view=types.SimpleNamespace(**vars(original))
    view._pricing_original=original
    if hasattr(host,'hot_path_params'):view.hot_path_params=host.hot_path_params
    snapshot=[None]
    def state():
        if snapshot[0] is None:snapshot[0]=copy.deepcopy(original._state())
        return snapshot[0]
    def save(st):
        result=original._save(st)
        snapshot[0]=st
        return result
    view._state=state;view._save=save
    view.item_def=lambda i:pricing_ui(original.item_def(i),data)
    def price(i,n,value):
        key=str(i)
        return data['prices'][key]*n if key in data['prices'] else original.product_price(i,n,value)
    # Native call sites use both two-argument and three-argument price contracts.
    view.product_price=lambda *args:price(args[0],args[1],args[2] if len(args)>2 else (lambda:0))
    view.shop_list=lambda st:pricing_ui(original.shop_list(st),data)
    view.ENDPOINTS=dict(original.ENDPOINTS)
    memo={}
    def cell(value):return (lambda:value).__closure__[0]
    def clone(fn):
        if not isinstance(fn,types.FunctionType):return fn
        if id(fn) in memo:return memo[id(fn)]
        old_cells=fn.__closure__ or ()
        cells=tuple(cell(None) for c in old_cells)
        copied=types.FunctionType(fn.__code__,fn.__globals__,fn.__name__,fn.__defaults__,cells or None)
        memo[id(fn)]=copied;copied.__kwdefaults__=fn.__kwdefaults__
        for src,dst in zip(old_cells,cells):
            value=src.cell_contents
            if value is original:dst.cell_contents=view
            elif isinstance(value,types.FunctionType) and str(value.__code__.co_filename).replace('\\','/').casefold().startswith(str(original.HERE).replace('\\','/').casefold()+'/'):
                dst.cell_contents=clone(value)
            else:dst.cell_contents=value
        return copied
    # Preserve the exact native wrapper chain and every validation/commit hook.
    # Rebinding creates new local closure cells; it never assigns host globals,
    # changes original function objects, or reruns installation hooks.
    native=original.ENDPOINTS['/shop/purchase']
    view.ENDPOINTS['/shop/purchase']=clone(native)
    if view.ENDPOINTS['/shop/purchase'] is native:raise RuntimeError('Native purchase adapter is not a Python closure')
    return view

def pricing_dispatch(host,query,body,fn):
    import json
    with host.STATE_LOCK:
        data=pricing_data();view=pricing_host(host,data)
        response=fn(view,query,body)
        return host._json(pricing_ui(json.loads(response[1]),data))

def open_pack(host,query,body):
    return pricing_dispatch(host,query,body,_pricing_base_open_pack)

def purchase(host,query,body):
    return pricing_dispatch(host,query,body,_pricing_base_purchase)

def remained(host,query,body):
    return pricing_dispatch(host,query,body,_pricing_base_remained)

def round_purchase(host,query,body):
    return pricing_dispatch(host,query,body,_pricing_base_round_purchase)

def round_quote(host,query,body):
    return pricing_dispatch(host,query,body,_pricing_base_round_quote)

def shop_list(host,query,body):
    return pricing_dispatch(host,query,body,_pricing_base_shop_list)
