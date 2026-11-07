"""Bounded passive crash capture: no debugger, GUI, process writes, suspend or termination."""
from pathlib import Path
import ctypes as c,ctypes.wintypes as w,json,sys,time,struct,subprocess,shutil
sys.path.insert(0,'D:/fifaol3/new-player-models/home-black-screen')
from minidump_read import Dump
O=Path(__file__).parent/'native-fault-watch';O.mkdir(exist_ok=True)
C=Path('D:/FO3ID/32795');known={p.name for p in C.glob('*.dmp')};deadline=time.monotonic()+180
K=c.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE
K.ReadProcessMemory.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)];K.ReadProcessMemory.restype=w.BOOL
K.CloseHandle.argtypes=[w.HANDLE]
print('PASSIVE_CRASH_CAPTURE_ARMED_180_SECONDS',flush=True)
while time.monotonic()<deadline:
    pending=[p for p in C.glob('*.dmp') if p.name not in known]
    if not pending:time.sleep(.2);continue
    source=max(pending,key=lambda p:p.stat().st_mtime);time.sleep(.2)
    try:
        target=O/source.name;shutil.copyfile(source,target);d=Dump(target)
        at,_=d.streams[6];_,ctx=struct.unpack_from('<II',d.data,at+160)
        regs={key:struct.unpack_from('<I',d.data,ctx+offset)[0] for key,offset in [('eax',176),('ecx',172),('edx',168),('ebx',164),('esi',160),('edi',156),('ebp',180),('eip',184),('esp',196)]}
    except (OSError,KeyError,struct.error):time.sleep(.2);continue
    query="Get-CimInstance Win32_Process -Filter \"Name='fifazf.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    result=subprocess.run(['powershell','-NoProfile','-Command',query],capture_output=True,text=True)
    rows=json.loads(result.stdout or '[]');rows=[rows] if isinstance(rows,dict) else rows
    matches=[p for p in rows if (p.get('ExecutablePath') or '').replace('\\','/').lower()=='d:/fo3id/32795/fifazf.exe']
    report=dict(source=source.name,registers={k:hex(v) for k,v in regs.items()},process_access='QUERY_INFORMATION|VM_READ',gui=False,process_modified=False,blocks={})
    for p in matches:
        h=K.OpenProcess(0x410,False,p['ProcessId'])
        if not h:continue
        queue=[(address,0) for address in regs.values() if address>0x10000];seen=set()
        try:
            while queue and len(seen)<384:
                address,depth=queue.pop(0);address &= ~15
                if address in seen or address<0x10000 or address>0x7fff0000:continue
                seen.add(address);buf=c.create_string_buffer(256);done=c.c_size_t()
                if not K.ReadProcessMemory(h,address,buf,256,c.byref(done)):continue
                raw=buf.raw[:done.value];report['blocks'][hex(address)]=raw.hex()
                if depth<3:
                    for value in struct.unpack('<'+'I'*(len(raw)//4),raw[:len(raw)//4*4]):
                        if 0x10000<value<0x7fff0000:queue.append((value,depth+1))
        finally:K.CloseHandle(h)
        report['pid']=p['ProcessId']
    crh=source.with_suffix('.crh')
    if crh.exists():shutil.copyfile(crh,O/crh.name)
    (O/'capture.json').write_text(json.dumps(report,indent=2),'utf8')
    print('CAPTURED '+str(len(report['blocks']))+' read-only memory blocks',flush=True);sys.exit(0)
print('CAPTURE_WINDOW_EXPIRED_NO_NEW_CRASH',flush=True)
