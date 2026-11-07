from pathlib import Path
import ast,base64,copy,hashlib,json,sys,textwrap,zlib
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True
from hot_update_runtime import compile_handlers
active=json.loads((S/'hot_updates/active.json').read_text('utf8'));raw_source=(S/active['code']).read_bytes();assert hashlib.sha256(raw_source).hexdigest()==active['sha256'];source=raw_source.decode('utf8').replace('\r\n','\n')
ns=compile_handlers(source,'current',active['routes'],allow_templates=True)['/shop/list'].__globals__
before=ns['volume_data']();plan=copy.deepcopy(before)
titles={71350101:'球星精选连锁',71350201:'传奇强化连锁',71350301:'经典赛季连锁',71350401:'传奇时刻连锁',71350501:'传奇精选连锁'}
for raw,t in plan.items():
 t['name']=titles[int(raw)]
 for steps in t['round_steps']:
  for k,i in enumerate(steps):
   d=t['packages'][str(i)];d['name']=f'第{k+1}档 · {d["count"]}包';d['label']=f'第{k+1}档'
engine=next(x for x in ast.parse(source).body if isinstance(x,ast.FunctionDef) and x.name=='volume_engine')
new_source=source
definition=next(x for x in engine.body if isinstance(x,ast.FunctionDef) and x.name=='definition')
old=textwrap.dedent(ast.get_source_segment(source,definition))
new="""def definition(i):
    if i not in stages:
        return clean_pack_definition(host,i) if i in chain_pack_ids else host.item_def(i)
    root,rn,k=stages[i];d=tracks[root]['packages'][str(i)];out=copy.deepcopy(host.item_def(i))
    out.update(name=d['name'],description=f'第{rn+1}轮 / 第{k+1}档<BR>共{d["count"]}个球员包，售价{d["price"]:,}点券。<BR>'+'<BR>'.join(definition(child)['name']+' ×'+str(n) for child,n in d['contents'])+'<BR>每包随机获得1名球员。',bunches=[dict(bunch=1,price=d['price'])],items=[dict(itemid=child,count=n,staticdata=definition(child)) for child,n in d['contents']])
    if d['premium_count']==0:
        featured=definition(d['contents'][0][0])
        out['itemicon']=featured['itemicon'];out['bundleicon']=featured.get('bundleicon',featured['itemicon'])
    return out"""
# ast.get_source_segment retains indentation after its first line.
start=sum(len(s) for s in source.splitlines(keepends=True)[:definition.lineno-1]);end=sum(len(s) for s in source.splitlines(keepends=True)[:definition.end_lineno])
new_source=source[:start]+textwrap.indent(new,'    ')+'\n'+source[end:]
anchor='    stages={int(i):(root,rn,k)'
assert anchor in new_source
idx=new_source.index('\n',new_source.index(anchor))
new_source=new_source[:idx]+"\n    chain_pack_ids={i for t in tracks.values() for p in t['packages'].values() for i,n in p['contents']}"+new_source[idx:]
new_source=new_source.replace("            if part.get('currentstep')=='complete' and versions.get(str(i))!='volume110-v1':continue", """            if part.get('currentstep')=='complete' and versions.get(str(i))!='volume110-v1':
                old=copy.deepcopy(host.item_def(i));items=old.get('items',[])
                old['name']=f'第{stages[i][2]+1}档 · {sum(x["count"] for x in items)}包'
                for child in items:child['staticdata']=clean_pack_definition(host,int(child['itemid']))
                old['description']='本档已购买。<BR>'+'<BR>'.join(x['staticdata']['name']+' ×'+str(x['count']) for x in items)
                part['product']['staticdata']=old
                continue""")
data=next(x for x in ast.parse(new_source).body if isinstance(x,ast.FunctionDef) and x.name=='volume_data')
encoded=base64.b64encode(zlib.compress(json.dumps(plan,ensure_ascii=False,separators=(',',':')).encode())).decode()
data_source="def volume_data():\n    import json,zlib,base64\n    return json.loads(zlib.decompress(base64.b64decode("+repr(encoded)+")))"
start=sum(len(s) for s in new_source.splitlines(keepends=True)[:data.lineno-1]);end=sum(len(s) for s in new_source.splitlines(keepends=True)[:data.end_lineno])
new_source=new_source[:start]+data_source+'\n'+new_source[end:]+'\n'+(R/'pack_names.py').read_text('utf8')
compile_handlers(new_source,'renamed',active['routes'],allow_templates=True)
(R/'before-business.py').write_bytes(source.encode());(R/'business.py').write_bytes(new_source.encode());(R/'before-plan.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf8');(R/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
(R/'build.json').write_text(json.dumps(dict(expected_revision=active['revision'],routes=active['routes'],before_sha256=active['sha256'],after_sha256=hashlib.sha256(new_source.encode()).hexdigest(),titles=titles),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='BUILT',titles=titles),ensure_ascii=True))
