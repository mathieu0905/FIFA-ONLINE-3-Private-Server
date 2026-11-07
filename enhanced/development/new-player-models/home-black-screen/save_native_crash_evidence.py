import hashlib,json,pathlib,struct,sys
sys.path[:0]=['D:/fifaol3/analysis_deps']
import capstone
from minidump_read import Dump
R=pathlib.Path(__file__).resolve().parent
p=R/'official-game-85916-20261107-012032.dmp';d=Dump(p)
record,context=struct.unpack('<II',d.read(0x45b44a9c,8));raw=d.read(record,80)
code,flags,chained,address,nparams=struct.unpack_from('<5I',raw)
registers={k:hex(d.u32(context+o)) for k,o in [('eax',176),('ecx',172),('edx',168),('ebx',164),('esi',160),('edi',156),('ebp',180),('eip',184),('esp',196)]}
token=d.u32(0x13773b10+8);begin,end,kind=struct.unpack('<III',d.read(token,12));token_text=d.read(begin,end-begin).decode('ascii')
assert code==0xc0000005 and address==0x8fd780 and registers['eax']=='0x0' and token_text=='trainingteamplayers'
cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
funcs=[]
for start,size in [(0x8fd740,70),(0x8fbbc0,68),(0x902b40,160)]:
    b=d.read(start,size);funcs.append(dict(start=hex(start),bytes=b.hex(),sha256=hashlib.sha256(b).hexdigest(),disassembly=[dict(address=hex(i.address),mnemonic=i.mnemonic,operands=i.op_str) for i in cs.disasm(b,start)]))
with p.open('rb') as f:dump_hash=hashlib.file_digest(f,'sha256').hexdigest()
symbols=json.loads((R/'fault-database-symbols.json').read_text('utf8'))
report=dict(dump=str(p),dump_sha256=dump_hash,pid=85916,capture='QUERY_INFORMATION|VM_READ; no debugger or GUI',exception_record=hex(record),exception_code=hex(code),exception_address=hex(address),exception_parameters=list(struct.unpack_from('<'+str(nparams)+'I',raw,20)),registers=registers,
  current_table_token=token_text,query_template=d.read(0x1587338,60).split(b'\0')[0].decode(),playerid=252371,
  observed_database_tables=[t['name'] for t in symbols['tables']],native_players_before=62081,bellingham_native_record_present_before=False,
  functions=funcs,conclusion='Player lookup SELECT players returns null then queries absent trainingteamplayers; parser dereferences a null table descriptor. The static native EA DB confirms missing playerid 252371.',
  unknowns=['Post-repair model rendering and match execution require human-run native verification.','Names inferred from nearest exported symbol in the game crash text are not trusted as function identities.'])
(R/'native-roster/crash-evidence.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('Captured native crash path verified')
