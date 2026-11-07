from pathlib import Path
import sys,re,struct,json,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).parent
OLD=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\experience_levels')
sys.path.insert(0,str(OLD/'analysis_deps'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
data=(OLD/'fifazf-runtime-analysis.exe').read_bytes();base=0x400000
cs=Cs(CS_ARCH_X86,CS_MODE_32)
out=ROOT/'evidence';out.mkdir(exist_ok=True)
if len(sys.argv)>1 and sys.argv[1]=='tables':
 tables={hex(a):list(struct.unpack_from('<151i',data,a-base)) for a in (0x158a600,0x158a860,0x158aac0)}
 (out/'conversion-tables.json').write_text(json.dumps(tables,indent=2),encoding='utf8')
 print(json.dumps({k:{str(i):v[i] for i in [0,1,50,70,80,90,99,100,110,120,130,140,149,150]} for k,v in tables.items()},indent=2))
 for a in (0x158aee0,0x1592a60,0x1592a64,0x1592a6c,0x1592a7c,0x159298c,0x15331e8):
  b=data[a-base:a-base+100];print(hex(a),repr(b.split(b'\0')[0]),b[:8].hex())
elif len(sys.argv)>1 and sys.argv[1]=='strings':
 rows=[]
 for m in re.finditer(rb'[\x20-\x7e]{5,}',data):
  s=m.group().decode('ascii')
  if re.search(r'sprint|accel|attribute|dribbl|speed|PLAYERGRADE',s,re.I):
   refs=[hex(base+x.start()) for x in re.finditer(re.escape(struct.pack('<I',base+m.start())),data) if x.start()<0x1100000]
   rows.append(dict(address=hex(base+m.start()),text=s,refs=refs))
 (out/'attribute-strings.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
 print(json.dumps(rows[:160],indent=2))
else:
 for a in sys.argv[1:] or ['9444f0','93df60','93e0d0']:
  parts=a.split(':');start=int(parts[0],16);length=int(parts[1],16) if len(parts)>1 else 0x500
  rows=[f'{i.address:08x} {i.bytes.hex():22} {i.mnemonic:9} {i.op_str}' for i in cs.disasm(data[start-base:start-base+length],start)]
  (out/f'disasm-{start:x}.txt').write_text('\n'.join(rows),encoding='utf8')
  print('\n'.join(rows))
