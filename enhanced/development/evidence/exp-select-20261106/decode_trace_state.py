from pathlib import Path
import json,struct
O=Path(__file__).parent/'native-fault-watch';r=json.loads((O/'capture.json').read_text('utf8'))
blocks=[(int(k,16),bytes.fromhex(v)) for k,v in r['blocks'].items()]
def read(address,n):
    for start,raw in blocks:
        if start<=address and address+n<=start+len(raw):return raw[address-start:address-start+n]
    raise KeyError(hex(address))
def u(address):return struct.unpack('<I',read(address,4))[0]
reg={k:int(v,16) for k,v in r['registers'].items()};out={}
for name in ('ebx','edi','edx'):
    base=reg[name]
    try:out[name]={hex(i):hex(u(base+i)) for i in range(0,160,4)}
    except KeyError:pass
(O/'trace-fields.json').write_text(json.dumps(out,indent=2),'utf8');print(json.dumps(out,indent=2))
