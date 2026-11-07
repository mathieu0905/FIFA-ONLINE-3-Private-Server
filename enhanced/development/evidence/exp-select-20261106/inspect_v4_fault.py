from pathlib import Path
import struct,sys,json
sys.path[:0]=['D:/fifaol3/analysis_deps','D:/fifaol3/new-player-models/home-black-screen']
from minidump_read import Dump
import capstone
O=Path(__file__).parent/'entry-failure-v4';d=Dump(O/'native.dmp');at,_=d.streams[6]
size,context=struct.unpack_from('<II',d.data,at+160)
regs={k:struct.unpack_from('<I',d.data,context+o)[0] for k,o in [('eax',176),('ecx',172),('edx',168),('ebx',164),('esi',160),('edi',156),('ebp',180),('eip',184),('esp',196)]}
cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def read(va,n):
    try:return d.read(va,n)
    except KeyError:return b''
code=read(regs['eip']-32,100)
stack=read(regs['esp'],512)
report=dict(registers={k:hex(v) for k,v in regs.items()},exception_parameters=[hex(x) for x in struct.unpack_from('<15Q',d.data,at+40)],code=code.hex(),disassembly=[dict(address=hex(i.address),mnemonic=i.mnemonic,operands=i.op_str) for i in cs.disasm(code,regs['eip']-32)],stack=[hex(x) for x in struct.unpack('<'+str(len(stack)//4)+'I',stack)],memory_ranges=[(hex(a),hex(b)) for a,b,c in d.ranges])
(O/'fault.json').write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps({k:report[k] for k in ('registers','exception_parameters','disassembly','stack')},indent=2))
