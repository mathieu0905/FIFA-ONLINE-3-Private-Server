from pathlib import Path
import ast,textwrap
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
source=(S/'chain_round_purchase.py').read_text('utf8');tree=ast.parse(source);install=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='install')
functions={x.name:textwrap.dedent(ast.get_source_segment(source,x)) for x in install.body if isinstance(x,ast.FunctionDef)}
engine=(R/'engine_prefix.py').read_text('utf8')
for name in ('owner','snapshot','sign','decorate','listing','response','quote','purchase'):
 code=functions[name]
 if name=='purchase':
  anchor="st.setdefault('product_chain_rounds',{})[str(q['root'])]=record"
  code=code.replace(anchor,"record.setdefault('volume_stage_versions',{}).update({str(i):'volume110-v1' for i in current['steps']})\n   "+anchor)
 engine+='\n'+textwrap.indent(code,'    ')+'\n'
engine+=(R/'single_suffix.py').read_text('utf8')
base=(R.parent/'draw-first/hot-v2/business.py').read_text('utf8')
tree=ast.parse(base);parts=[]
overrides={
 'shop_list':"def shop_list(host, query, body):\n    with host.STATE_LOCK:return host._json(volume_engine(host)['listing'](host._state()))\n",
 'remained':"def remained(host, query, body):\n    with host.STATE_LOCK:return host._json(volume_engine(host)['counts'](host._state()))\n",
 'round_purchase':"def round_purchase(host, query, body):\n    with host.STATE_LOCK:return volume_engine(host)['purchase'](query,body)\n",
 'refresh_response':"def refresh_response(host, response):\n    import json\n    out=json.loads(response[1]);engine=volume_engine(host);st=host._state()\n    for r in out.get('resources',[]):\n        if r.get('uri')=='/shop/list':r['body']=engine['listing'](st)\n        elif r.get('uri')=='/shop/remained/limited':r['body']=engine['counts'](st)\n    return host._json(out)\n",
}
for node in tree.body:
 if not isinstance(node,ast.FunctionDef):continue
 code=overrides.get(node.name,ast.get_source_segment(base,node))
 if node.name=='purchase':
  anchor='        if blocked(host,itemid):'
  code=code.replace(anchor,"        engine=volume_engine(host)\n        if itemid in engine['stages']:return engine['single'](req,itemid)\n"+anchor)
 parts.append(code)
parts.append("def round_quote(host, query, body):\n    with host.STATE_LOCK:return volume_engine(host)['quote'](query,body)\n")
result=(R/'data_function.py').read_text('utf8')+'\n'+engine+'\n'+'\n\n'.join(parts)+'\n'
compile(result,str(R/'business.py'),'exec');(R/'business.py').write_text(result,encoding='utf8');print('Prepared '+str(len(result.encode()))+' bytes')
