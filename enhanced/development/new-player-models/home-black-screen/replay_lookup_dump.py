"""Replay native file resolution against an isolated captured address space.

Only emulator memory can change. Known synchronization/time imports are stubbed;
all other Windows calls stop the replay and remain explicit limitations.
"""
import json,pathlib,struct,sys,re
sys.path[:0]=['D:/fifaol3/analysis_deps']
import unicorn as u
from unicorn.x86_const import *
from minidump_read import Dump
ROOT=pathlib.Path(__file__).resolve().parent
d=Dump(sys.argv[1]);modules=d.modules();exports={}
def string(address):
    out=[]
    for i in range(1024):
        b=d.read(address+i,1)
        if b==b'\0':break
        out.append(b)
    return b''.join(out).decode('latin1')
for module in modules:
    base=module['base']
    if base>0xffffffff or not any(s in module['name'].lower() for s in ['kernel32','kernelbase','ntdll','msvcr']):continue
    try:
        nt=base+d.u32(base+0x3c);er,es=struct.unpack('<II',d.read(nt+24+96,8))
        if not er:continue
        entry=base+er;nfunc,nnames,funcs,names,ordinals=struct.unpack('<IIIII',d.read(entry+20,20))
        for i in range(nnames):
            ordinal=struct.unpack('<H',d.read(base+ordinals+i*2,2))[0];rva=d.u32(base+funcs+ordinal*4)
            if not er<=rva<er+es:exports[base+rva]=string(base+d.u32(base+names+i*4))
    except (KeyError,struct.error):pass

results=[]
read_mode=len(sys.argv)>2 and sys.argv[2]=='read'
for path in ['data/db2/fifadb.db.db2','data/db2/chi.db.db2','data/fifarna/lua/assets/player.lua']:
    em=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32);mapped=set();trace=[];failures=[];stubs=[];count=[0]
    for address,size in [(0x7a000000,0x200000),(0x7c000000,0x10000),(0,0x1000)]:
        em.mem_map(address,size);mapped.update(range(address,address+size,4096))
    stack=0x7a1f0000;argument=0x7c001000;stop=0x7c00f000
    em.mem_write(argument,path.encode()+b'\0');em.mem_write(stack,struct.pack('<II',stop,argument));em.reg_write(UC_X86_REG_ESP,stack);em.reg_write(UC_X86_REG_EFLAGS,0x202)
    if read_mode:
        output=0x7e000000;length={'data/db2/fifadb.db.db2':54134784,'data/db2/chi.db.db2':5647360,'data/fifarna/lua/assets/player.lua':62328}[path]
        em.mem_map(output,0x4000000);mapped.update(range(output,output+0x4000000,4096));em.mem_write(stack,struct.pack('<IIII',stop,argument,output,length))
    def unmapped(uc,access,address,size,value,extra):
        try:
            for page in range(address&~4095,(address+size+4095)&~4095,4096):
                if page not in mapped:uc.mem_map(page,4096);uc.mem_write(page,d.read(page,4096));mapped.add(page)
            return True
        except Exception as error:failures.append(dict(access=access,address=hex(address),error=str(error)));return False
    def finish_call(uc,nargs,result):
        esp=uc.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',uc.mem_read(esp,4))[0];uc.reg_write(UC_X86_REG_EAX,result);uc.reg_write(UC_X86_REG_ESP,esp+4+nargs*4);uc.reg_write(UC_X86_REG_EIP,ret)
    def cstring(uc,address):
        out=bytearray()
        for i in range(4096):
            page=(address+i)&~4095
            if page not in mapped:
                uc.mem_map(page,4096);uc.mem_write(page,d.read(page,4096));mapped.add(page)
            byte=bytes(uc.mem_read(address+i,1))
            if byte==b'\0':break
            out+=byte
        return bytes(out)
    def code(uc,address,size,extra):
        count[0]+=1;trace.append(address)
        if len(trace)>30:trace.pop(0)
        if address==stop:uc.emu_stop();return
        name=exports.get(address)
        if name:
            esp=uc.reg_read(UC_X86_REG_ESP)
            if name in ['QueryPerformanceCounter','RtlQueryPerformanceCounter']:
                dest=struct.unpack('<I',uc.mem_read(esp+4,4))[0];uc.mem_write(dest,struct.pack('<Q',1000000));stubs.append(name);finish_call(uc,1,1);return
            if name in ['memset','memcpy','memmove']:
                dest,source,length=struct.unpack('<III',uc.mem_read(esp+4,12))
                for base,span in [(dest,length)]+([] if name=='memset' else [(source,length)]):
                    for page in range(base&~4095,(base+span+4095)&~4095,4096):
                        if page not in mapped:uc.mem_map(page,4096);uc.mem_write(page,d.read(page,4096));mapped.add(page)
                payload=bytes([source&255])*length if name=='memset' else bytes(uc.mem_read(source,length))
                uc.mem_write(dest,payload);stubs.append(dict(name=name,length=length));finish_call(uc,0,dest);return
            if name in ['strncpy_s','strcpy_s']:
                args=struct.unpack('<IIII',uc.mem_read(esp+4,16));dest,limit,source=args[:3];text=cstring(uc,source)
                if name=='strncpy_s' and args[3]!=0xffffffff:text=text[:args[3]]
                text=text[:limit-1]
                for page in range(dest&~4095,(dest+len(text)+4096)&~4095,4096):
                    if page not in mapped:uc.mem_map(page,4096);uc.mem_write(page,d.read(page,4096));mapped.add(page)
                uc.mem_write(dest,text+b'\0');stubs.append(name);finish_call(uc,0,0);return
            if name in ['tolower','toupper']:
                value=struct.unpack('<I',uc.mem_read(esp+4,4))[0];result=(value+32 if 65<=value<=90 else value) if name=='tolower' else (value-32 if 97<=value<=122 else value)
                finish_call(uc,0,result);return
            if name=='vsprintf_s':
                dest,limit,fmt,values=struct.unpack('<IIII',uc.mem_read(esp+4,16));format_=cstring(uc,fmt).decode('latin1');position=[values]
                def substitute(match):
                    spec=match.group()
                    if spec=='%%':return '%'
                    value=struct.unpack('<I',uc.mem_read(position[0],4))[0];position[0]+=4
                    if spec.endswith('s'):return cstring(uc,value).decode('latin1')
                    if spec.endswith(('x','X')):return format(value,'x' if spec[-1]=='x' else 'X')
                    return str(value)
                text=re.sub(r'%%|%[-+ #0-9.]*[sduxX]',substitute,format_).encode('latin1');assert len(text)<limit
                uc.mem_write(dest,text+b'\0');stubs.append(name);finish_call(uc,0,len(text));return
            if name in ['GetFileAttributesA','GetFileAttributesExA']:
                args=struct.unpack('<III',uc.mem_read(esp+4,12));file=cstring(uc,args[0]).decode('latin1');file=file.replace('\\','/')
                candidate=pathlib.Path(file)
                if not candidate.is_absolute():candidate=pathlib.Path('D:/FO3ID/32795')/candidate
                candidate=candidate.resolve();allowed=candidate.is_relative_to(pathlib.Path('D:/FO3ID/32795'))
                exists=allowed and candidate.exists()
                attr=0x10 if exists and candidate.is_dir() else 0x80
                if name=='GetFileAttributesA':finish_call(uc,1,attr if exists else 0xffffffff)
                elif exists:
                    size=candidate.stat().st_size;uc.mem_write(args[2],struct.pack('<IQQQII',attr,0,0,0,size>>32,size&0xffffffff));finish_call(uc,3,1)
                else:finish_call(uc,3,0)
                stubs.append(dict(name=name,path=file,exists=exists));return
            if name in ['strchr','strrchr','strlen','strcmp','strncmp','_stricmp','_strnicmp']:
                args=struct.unpack('<III',uc.mem_read(esp+4,12));left=cstring(uc,args[0])
                if name in ['strchr','strrchr']:
                    needle=bytes([args[1]&255]);index=(left+b'\0').find(needle) if name=='strchr' else (left+b'\0').rfind(needle);result=args[0]+index if index>=0 else 0
                elif name=='strlen':result=len(left)
                else:
                    right=cstring(uc,args[1])
                    if 'icmp' in name:left=left.lower();right=right.lower()
                    if name in ['strncmp','_strnicmp']:left=left[:args[2]];right=right[:args[2]]
                    result=(left>right)-(left<right)
                stubs.append(name);finish_call(uc,0,result&0xffffffff);return
            if name in ['EnterCriticalSection','LeaveCriticalSection','RtlEnterCriticalSection','RtlLeaveCriticalSection','AcquireSRWLockExclusive','ReleaseSRWLockExclusive']:
                stubs.append(name);finish_call(uc,1,0);return
            if name in ['GetCurrentThreadId','GetTickCount']:
                stubs.append(name);finish_call(uc,0,91676 if name=='GetCurrentThreadId' else 0);return
            failures.append(dict(stopped_export=name,address=hex(address),stack=bytes(uc.mem_read(uc.reg_read(UC_X86_REG_ESP),28)).hex()));uc.emu_stop();return
        if address>=0x70000000 and address<0x7a000000:
            failures.append(dict(stopped_system_code=hex(address)));uc.emu_stop()
    em.hook_add(u.UC_HOOK_MEM_UNMAPPED,unmapped);em.hook_add(u.UC_HOOK_CODE,code)
    try:em.emu_start(0xbb4d60 if read_mode else 0xbb4820,stop,timeout=10_000_000,count=300000)
    except u.UcError as error:failures.append(dict(emulator_error=str(error)))
    results.append(dict(path=path,eax=em.reg_read(UC_X86_REG_EAX),edx=em.reg_read(UC_X86_REG_EDX),eip=hex(em.reg_read(UC_X86_REG_EIP)),instructions=count[0],stubs=stubs,failures=failures,trace=[hex(a) for a in trace]))
out=dict(dump=str(d.path),mode='read' if read_mode else 'size',results=results,live_process_modified=False,model_compatibility_proven=False)
(ROOT/('dump-read-replay.json' if read_mode else 'dump-lookup-replay.json')).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
