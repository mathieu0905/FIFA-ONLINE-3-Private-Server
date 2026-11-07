from pathlib import Path
import ast,json,hashlib,zlib,base64,copy
R=Path(__file__).resolve().parent
baseline=json.loads((R/'baseline.json').read_text('utf8'));source=(R/'before-business.py').read_bytes().decode('utf8').replace('\r\n','\n')
def data_fn(name,value):
 encoded=base64.b64encode(zlib.compress(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode())).decode()
 return f'def {name}():\n    import json,zlib,base64\n    return json.loads(zlib.decompress(base64.b64decode({encoded!r})))\n'
def replace(src,name,new):
 node=next(x for x in ast.parse(src).body if isinstance(x,ast.FunctionDef) and x.name==name);lines=src.splitlines(keepends=True)
 return ''.join(lines[:node.lineno-1])+new+'\n'+''.join(lines[node.end_lineno:])
before=json.loads((R/'volume-before.json').read_text('utf8'));after=json.loads((R/'volume-after.json').read_text('utf8'))
source=replace(source,'volume_data',data_fn('volume_data',after))
source=source.replace("versions.get(str(i))!='volume110-high8-v2'","versions.get(str(i))!='volume110-price-v3'")
source=source.replace("if versions.get(str(i))=='volume110-v1':", "if versions.get(str(i)) in ('volume110-v1','volume110-high8-v2'):")
source=source.replace("legacy=volume_legacy_data()[str(root)]['packages'][str(i)]", "legacy=(pricing_legacy_data() if versions.get(str(i))=='volume110-high8-v2' else volume_legacy_data())[str(root)]['packages'][str(i)]")
source=source.replace("old=copy.deepcopy(host.item_def(i));items=old.get('items',[])","old=copy.deepcopy(getattr(host,'_pricing_original',host).item_def(i));items=old.get('items',[])")
source=source.replace("{str(i):'volume110-high8-v2' for i in current['steps']}","{str(i):'volume110-price-v3' for i in current['steps']}")
source=source.replace("[str(i)]='volume110-high8-v2'","[str(i)]='volume110-price-v3'")
wrapped={r['function'] for r in baseline['active']['routes'] if r['path']!='/hot/market/supply/activate'}
for name in wrapped:
 source=source.replace('\ndef '+name+'(', '\ndef _pricing_base_'+name+'(',1)
wrappers='\n'.join('def '+name+'(host,query,body):\n    return pricing_dispatch(host,query,body,_pricing_base_'+name+')\n' for name in sorted(wrapped))
data=json.loads((R/'pricing.json').read_text('utf8'))
source+='\n'+data_fn('pricing_legacy_data',before)+'\n'+data_fn('pricing_data',data)+'\n'+(R/'runtime.py').read_text('utf8')+'\n'+wrappers
compile(source,'repriced-business.py','exec');(R/'business.py').write_bytes(source.encode())
(R/'business-meta.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),routes=baseline['active']['routes'],expected_revision=baseline['active']['revision'],bytes=len(source.encode())),indent=2),encoding='utf8')
print(json.dumps(dict(status='BUILT',bytes=len(source.encode()),expected_revision=baseline['active']['revision'])))
