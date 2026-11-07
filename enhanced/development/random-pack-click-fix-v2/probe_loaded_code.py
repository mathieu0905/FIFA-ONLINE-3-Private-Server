"""Read-only byte-pattern observation of the selected game process; no debugger or writes."""
from pathlib import Path
import ctypes, ctypes.wintypes as W, hashlib, json, sys, time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
TOOLS=Path(r'C:\Users\15128\Documents\Codex\2026-11-06\https-github-com-soloplayer24-fifa-online\work\bp_client')
sys.path[:0]=[str(TOOLS),r'D:\FO3ID\server\tools\re']
from avm_patch import ABC
pid=int(sys.argv[1])
fixed=ROOT.parent/'random-pack-click-fix/client'
old=ROOT.parent/'random-pack-dual/client'
filename='TeamManagementPlayerCardScreen-after.abc'
newabc=ABC((fixed/filename).read_bytes())
oldabc=ABC((old/filename).read_bytes())
def tail(directory):
    patch=json.loads((directory/'TeamManagementPlayerCardScreen-ABC.patch.json').read_text('utf8'))['51']
    return bytes.fromhex(patch['updated'])[len(bytes.fromhex(patch['original']))-1:]
needles={'installed_native_draw51':tail(fixed)[20:100],
         'older_blue_draw51':tail(old)[20:100],
         'bulk_handler67':newabc.A['body'][67][:80]}
v2=ABC((ROOT/'client'/filename).read_bytes())
needles['v2_bound_bulk_handler68']=v2.A['body'][68][:80]
assert all(len(v)==80 for v in needles.values()) and len(set(needles.values()))==len(needles)
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD]; k.OpenProcess.restype=W.HANDLE
k.CloseHandle.argtypes=[W.HANDLE]
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
class MBI(ctypes.Structure):
    _fields_=[('BaseAddress',ctypes.c_void_p),('AllocationBase',ctypes.c_void_p),('AllocationProtect',W.DWORD),
              ('PartitionId',W.WORD),('RegionSize',ctypes.c_size_t),('State',W.DWORD),('Protect',W.DWORD),('Type',W.DWORD)]
k.VirtualQueryEx.argtypes=[W.HANDLE,ctypes.c_void_p,ctypes.POINTER(MBI),ctypes.c_size_t]
k.VirtualQueryEx.restype=ctypes.c_size_t
k.ReadProcessMemory.argtypes=[W.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
handle=k.OpenProcess(0x0400|0x0010,False,pid)  # QUERY_INFORMATION | VM_READ only
if not handle: raise ctypes.WinError(ctypes.get_last_error())
hits={name:[] for name in needles}; scanned=0; regions=0; skipped=0; started=time.monotonic()
try:
    namebuf=ctypes.create_unicode_buffer(32768); count=W.DWORD(len(namebuf))
    if not k.QueryFullProcessImageNameW(handle,0,namebuf,ctypes.byref(count)):raise ctypes.WinError(ctypes.get_last_error())
    executable=Path(namebuf.value)
    assert str(executable).lower()==r'D:\FO3ID\32795\fifazf.exe'.lower(),str(executable)
    address=0
    while address<0x100000000:
        info=MBI()
        if not k.VirtualQueryEx(handle,ctypes.c_void_p(address),ctypes.byref(info),ctypes.sizeof(info)):break
        base=info.BaseAddress or 0; size=info.RegionSize
        if size==0:break
        if info.State==0x1000 and not info.Protect&0x101 and info.Protect&0xee:
            regions+=1; offset=0; overlap=b''
            while offset<size:
                chunk=min(1024*1024,size-offset); buffer=ctypes.create_string_buffer(chunk); read=ctypes.c_size_t()
                if k.ReadProcessMemory(handle,ctypes.c_void_p(base+offset),buffer,chunk,ctypes.byref(read)):
                    raw=overlap+buffer.raw[:read.value]; scanned+=read.value
                    for label,needle in needles.items():
                        at=raw.find(needle)
                        while at>=0:
                            found=base+offset-len(overlap)+at
                            if len(hits[label])<32 and hex(found) not in hits[label]:hits[label].append(hex(found))
                            at=raw.find(needle,at+1)
                    overlap=raw[-79:]
                else:skipped+=1;overlap=b''
                offset+=chunk
        address=base+size
finally:k.CloseHandle(handle)
report=dict(pid=pid,executable=str(executable),read_only=True,process_paused=False,process_modified=False,
            searched_address_limit='0x100000000',readable_regions=regions,bytes_read=scanned,failed_chunks=skipped,
            needle_sha256={n:hashlib.sha256(v).hexdigest() for n,v in needles.items()},hits=hits,
            elapsed_seconds=round(time.monotonic()-started,3),
            limitation='Byte presence establishes loaded/raw code evidence only; does not establish current handler execution or object state')
(ROOT/'loaded-code-observation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
