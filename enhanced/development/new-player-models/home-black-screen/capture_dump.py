"""Capture the human-opened official game with read/query access, without a debugger or GUI."""
import ctypes as c
from ctypes import wintypes as w
import datetime,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
def main():
    query="Get-CimInstance Win32_Process -Filter \"Name='fifazf.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',query],capture_output=True,text=True,check=True)
    if not result.stdout.strip():print('NO_OFFICIAL_GAME_RUNNING');return
    processes=json.loads(result.stdout)
    if isinstance(processes,dict):processes=[processes]
    matches=[p for p in processes if (p.get('ExecutablePath') or '').replace('\\','/').casefold()=='d:/fo3id/32795/fifazf.exe']
    if len(matches)!=1:raise RuntimeError('One official game process is required')
    pid=matches[0]['ProcessId'];K=c.WinDLL('kernel32',use_last_error=True);D=c.WinDLL('dbghelp',use_last_error=True)
    K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE
    K.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.c_void_p,w.DWORD,w.DWORD,w.HANDLE];K.CreateFileW.restype=w.HANDLE
    K.CloseHandle.argtypes=[w.HANDLE]
    D.MiniDumpWriteDump.argtypes=[w.HANDLE,w.DWORD,w.HANDLE,w.DWORD,c.c_void_p,c.c_void_p,c.c_void_p];D.MiniDumpWriteDump.restype=w.BOOL
    process=K.OpenProcess(0x410,False,pid)
    if not process:raise c.WinError(c.get_last_error())
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S');path=ROOT/f'official-game-{pid}-{stamp}.dmp'
    handle=K.CreateFileW(str(path),0x40000000,1,None,1,0x80,None)
    if handle in (None,c.c_void_p(-1).value):K.CloseHandle(process);raise c.WinError(c.get_last_error())
    try:
        if not D.MiniDumpWriteDump(process,pid,handle,0x2|0x800|0x1000|0x20000,None,None,None):raise c.WinError(c.get_last_error())
    finally:K.CloseHandle(handle);K.CloseHandle(process)
    report=dict(path=str(path),bytes=path.stat().st_size,pid=pid,executable=matches[0]['ExecutablePath'],process_access='QUERY_INFORMATION|VM_READ',game_started=False,game_stopped=False,gui_used=False,debugger_attached=False,limitation='Snapshot while running; no claim that all pages are atomic or readable.')
    path.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':main()
