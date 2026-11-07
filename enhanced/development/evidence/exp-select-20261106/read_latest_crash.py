from pathlib import Path
import sys,struct,json,re,hashlib
sys.path.insert(0,'D:/fifaol3/new-player-models/home-black-screen')
from minidump_read import Dump
p=Path(sys.argv[1]) if len(sys.argv)>1 else Path('D:/FO3ID/32795/fifazf[2026-11-07_02-41-22]_id.dmp')
O=p.parent if len(sys.argv)>1 else Path(__file__).parent/'entry-failure-v3';O.mkdir(exist_ok=True)
d=Dump(p)
r=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),streams=d.streams,threads=d.threads(),modules=d.modules(),native_pass=False)
if 6 in d.streams:
    at,_=d.streams[6];tid=struct.unpack_from('<I',d.data,at)[0]
    code,flags,record,address=struct.unpack_from('<IIQQ',d.data,at+8)
    r['exception']=dict(thread=tid,code=hex(code),address=hex(address))
strings=[s.decode('ascii','replace') for s in re.findall(rb'[\x20-\x7e]{8,}',d.data)]
r['error_strings']=[s for s in strings if re.search('Verify|Error|ExpCaps|TextField|playerLevel|fo3Exp|fo3Batch',s,re.I)]
(O/'dump.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({k:r[k] for k in ('exception','error_strings') if k in r},ensure_ascii=True))
