from pathlib import Path
import ast,base64,copy,hashlib,json,sys,zlib
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');sys.path.insert(0,str(S));sys.dont_write_bytecode=True
from hot_update_runtime import compile_handlers
active=json.loads((S/'hot_updates/active.json').read_text('utf8'));raw=(S/active['code']).read_bytes();assert hashlib.sha256(raw).hexdigest()==active['sha256'];source=raw.decode('utf8').replace('\r\n','\n')
ns=compile_handlers(source,'current',active['routes'],allow_templates=True)['/shop/list'].__globals__;before=ns['volume_data']();plan=copy.deepcopy(before)
titles={71350101:'金牌强化连锁礼包',71350201:'传奇巨星连锁礼包',71350301:'经典赛季连锁礼包',71350401:'传奇时刻连锁礼包',71350501:'传奇混合连锁礼包'}
for raw,t in plan.items():
 t['name']=titles[int(raw)]
 for p in t['packages'].values():p['name']=t['name'];p['label']=t['name']
encoded=base64.b64encode(zlib.compress(json.dumps(plan,ensure_ascii=False,separators=(',',':')).encode())).decode()
def replace_fn(src,name,new):
 node=next(x for x in ast.parse(src).body if isinstance(x,ast.FunctionDef) and x.name==name);lines=src.splitlines(keepends=True)
 return ''.join(lines[:node.lineno-1])+new.rstrip()+'\n'+''.join(lines[node.end_lineno:])
new=replace_fn(source,'volume_data',"def volume_data():\n    import json,zlib,base64\n    return json.loads(zlib.decompress(base64.b64decode("+repr(encoded)+")))")
new=replace_fn(new,'clean_pack_definition',(R/'native_pack_names.py').read_text('utf8'))
lines=new.splitlines()
for k,line in enumerate(lines):
 if "old['name']=f'第" in line:lines[k]="                old['name']=tracks[root]['name']"
 elif "row['chainedproductname']=tracks[root]['name']+" in line:lines[k]="        row['chainedproductname']=tracks[root]['name']"
new='\n'.join(lines)+'\n';compile_handlers(new,'native-style',active['routes'],allow_templates=True)
(R/'before-business.py').write_bytes(source.encode());(R/'business.py').write_bytes(new.encode())
for name,data in [('before-plan.json',before),('plan.json',plan)]: (R/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
(R/'build.json').write_text(json.dumps(dict(expected_revision=active['revision'],routes=active['routes'],before_sha256=active['sha256'],after_sha256=hashlib.sha256(new.encode()).hexdigest(),titles=titles),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(status='BUILT_NATIVE_STYLE',titles=titles),ensure_ascii=True))
