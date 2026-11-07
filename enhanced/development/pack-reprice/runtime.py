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
