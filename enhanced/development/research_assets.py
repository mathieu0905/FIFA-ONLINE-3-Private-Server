from pathlib import Path
import sys,re,json,hashlib
sys.dont_write_bytecode=True
sys.path.insert(0,r'D:\FO3ID\server\tools\re');import bigdir
root=Path(__file__).parent/'research'/'assets';root.mkdir(parents=True,exist_ok=True)
source=Path(r'D:\FO3ID\32795\data\data_0.big');rows=[]
for name,offset,size,usize in bigdir.entries(source):
 if not (name.startswith('data/attribdb') or name in ('product.ini','platform.ini')):continue
 data=bigdir.read(source,name);target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 strings=[dict(offset=hex(m.start()),text=m.group().decode('ascii')) for m in re.finditer(rb'[ -~]{4,}',data)]
 (target.parent/(target.name+'.strings.json')).write_text(json.dumps(strings,indent=2),encoding='utf8')
 rows.append(dict(name=name,offset=offset,size=len(data),sha256=hashlib.sha256(data).hexdigest(),related_strings=[r for r in strings if re.search('sprint|accel|speed|attr|locomo|motion',r['text'],re.I)]))
(root/'manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows,indent=2))
