"""Replay the native resolver in a private emulator using read-only process pages.
No threads, code or data are written into the game. System calls are stopped.
"""
import ctypes as c, json, pathlib, struct, sys
sys.path[:0]=['D:/fifaol3/analysis_deps', 'C:/Users/15128/Documents/Codex/2026-11-06/https-github-com-soloplayer24-fifa-online/work/experience_levels/analysis_deps']
import unicorn as u
from unicorn.x86_const import *
from capture_visual_inputs import K
ROOT=pathlib.Path(__file__).resolve().parent
pid=int(sys.argv[1]);h=K.OpenProcess(0x410,False,pid)
if not h:raise c.WinError(c.get_last_error())
def read(address,n):
    b=c.create_string_buffer(n);done=c.c_size_t()
    if not K.ReadProcessMemory(h,address,b,n,c.byref(done)):raise c.WinError(c.get_last_error())
    return b.raw[:done.value]
def main():
    results=[]
    for path in ['data/db2/fifadb.db.db2','data/db2/chi.db.db2','data/fifarna/lua/assets/player.lua']:
        em=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32);mapped=set();trace=[];counts=[0];failure=[]
        for addr,size in [(0x7a000000,0x200000),(0x7c000000,0x10000),(0,0x1000)]:
            em.mem_map(addr,size);mapped.update(range(addr,addr+size,4096))
        stack=0x7a1f0000;string=0x7c001000;stop=0x7c00f000
        em.mem_write(string,path.encode()+b'\0');em.mem_write(stack,struct.pack('<II',stop,string))
        em.reg_write(UC_X86_REG_ESP,stack);em.reg_write(UC_X86_REG_EBP,0);em.reg_write(UC_X86_REG_EFLAGS,0x202)
        def unmapped(uc,access,address,size,value,extra):
            try:
                first=address&~4095;end=(address+size+4095)&~4095
                for page in range(first,end,4096):
                    if page not in mapped:
                        data=read(page,4096);uc.mem_map(page,4096);uc.mem_write(page,data);mapped.add(page)
                return True
            except Exception as error:
                failure.append(dict(address=hex(address),access=access,error=str(error)));return False
        def code(uc,address,size,extra):
            counts[0]+=1;trace.append(address)
            if len(trace)>30:trace.pop(0)
            if address==stop:uc.emu_stop()
            elif address>=0x70000000 and address<0x7a000000:
                failure.append(dict(system_call_stopped=hex(address),stack=bytes(uc.mem_read(uc.reg_read(UC_X86_REG_ESP),24)).hex()));uc.emu_stop()
        em.hook_add(u.UC_HOOK_MEM_UNMAPPED,unmapped);em.hook_add(u.UC_HOOK_CODE,code)
        try:em.emu_start(0xbb4820,stop,timeout=10_000_000,count=200000)
        except u.UcError as error:failure.append(dict(emulator_error=str(error)))
        result=dict(path=path,eax=em.reg_read(UC_X86_REG_EAX),edx=em.reg_read(UC_X86_REG_EDX),eip=hex(em.reg_read(UC_X86_REG_EIP)),instructions=counts[0],trace=[hex(a) for a in trace],failure=failure,pages=len(mapped))
        results.append(result)
    (ROOT/'native-lookup-replay.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(json.dumps(results))
try:main()
finally:K.CloseHandle(h)
