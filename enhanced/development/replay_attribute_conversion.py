"""Execute original x86 conversion instructions in Unicorn, without running FO3.

Only the two region-query callees are stubbed, selecting each of the three tables.
This verifies attribute conversion; it does not simulate locomotion or a match.
"""
from pathlib import Path
import sys,struct,json,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'analysis_deps'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EBP,UC_X86_REG_EIP,UC_X86_REG_EAX,UC_X86_REG_CR4
image=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\experience_levels\fifazf-runtime-analysis.exe')
data=image.read_bytes();base=0x400000;stack=0x3000000;stop=0x3100000
u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(base,(len(data)+4095)//4096*4096);u.mem_write(base,data)
u.mem_map(stack,0x10000);u.mem_map(stop,4096)
u.reg_write(UC_X86_REG_CR4,0x600)
region=0
def hook(uc,address,size,unused):
 if address in (0xbb9760,0xbb9780):
  uc.reg_write(UC_X86_REG_EAX,int((address==0xbb9760 and region==1) or (address==0xbb9780 and region==2)))
  sp=uc.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',uc.mem_read(sp,4))[0]
  uc.reg_write(UC_X86_REG_ESP,sp+4);uc.reg_write(UC_X86_REG_EIP,ret)
u.hook_add(UC_HOOK_CODE,hook)
rows=[]
for region in range(3):
 for score in (50,80,90,99,100,110,120,130,140,143,144,145,149,150,151,160,200):
  for extra,mult in ((0,1.0),(2,1.0),(0,0.9)):
   sp=stack+0xf000;u.reg_write(UC_X86_REG_ESP,sp);u.reg_write(UC_X86_REG_EBP,0)
   u.mem_write(sp,struct.pack('<Iiif',stop,score,extra,mult))
   u.emu_start(0x9444f0,stop,count=1000)
   got=u.reg_read(UC_X86_REG_EAX)
   addr=(0x158a600,0x158aac0,0x158a860)[region]
   lookup=struct.unpack_from('<i',data,addr-base+min(score,150)*4)[0]
   # IEEE single precision multiplication, matching MULSS then CVTTSS2SI.
   expect=max(1,min(100,int(struct.unpack('<f',struct.pack('<f',(lookup+extra)*struct.unpack('<f',struct.pack('<f',mult))[0]))[0])))
   assert got==expect,(region,score,extra,mult,got,expect)
   rows.append(dict(region_branch=region,panel_input=score,extra=extra,multiplier=mult,output=got))
report=dict(snapshot_sha256=hashlib.sha256(data).hexdigest(),function='0x9444f0',emulator='Unicorn 2.1.4',test_count=len(rows),all_passed=True,limitations=['Historical runtime analysis image, not a fresh live process capture.','Region-query returns are stubbed to exercise all three table branches.','Instruction replay verifies conversion only, not on-pitch speed or condition multipliers.'],cases=rows)
(ROOT/'evidence'/'instruction-replay.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
print(json.dumps([r for r in rows if r['region_branch']==0 and r['extra']==0 and r['multiplier']==1],indent=2))
