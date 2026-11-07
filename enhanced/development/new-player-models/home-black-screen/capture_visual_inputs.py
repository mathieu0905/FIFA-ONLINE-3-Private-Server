"""Read selected FO3 visual inputs. Never launches, suspends or writes the game.

Run while the human has the official client open, before choosing Bellingham.
Only structured candidate fields are retained; unrelated process memory is discarded.
"""
import ctypes as c
from ctypes import wintypes as w
import datetime, json, pathlib, struct, subprocess, time

ROOT = pathlib.Path(__file__).resolve().parent
K = c.WinDLL('kernel32', use_last_error=True)

class MBI(c.Structure):
    _fields_ = [('BaseAddress', c.c_void_p), ('AllocationBase', c.c_void_p),
                ('AllocationProtect', w.DWORD), ('PartitionId', w.WORD),
                ('RegionSize', c.c_size_t), ('State', w.DWORD),
                ('Protect', w.DWORD), ('Type', w.DWORD)]

K.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
K.OpenProcess.restype = w.HANDLE
K.VirtualQueryEx.argtypes = [w.HANDLE, c.c_void_p, c.POINTER(MBI), c.c_size_t]
K.VirtualQueryEx.restype = c.c_size_t
K.ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
K.ReadProcessMemory.restype = w.BOOL
K.CloseHandle.argtypes = [w.HANDLE]

def main():
    command = "Get-CimInstance Win32_Process -Filter \"Name='fifazf.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True, text=True, check=True)
    if not result.stdout.strip():
        print('NO_GAME_RUNNING: human must open the official client; nothing changed.')
        return
    processes = json.loads(result.stdout)
    if isinstance(processes, dict): processes = [processes]
    matches = [p for p in processes if (p.get('ExecutablePath') or '').replace('\\', '/').casefold() == 'd:/fo3id/32795/fifazf.exe']
    if len(matches) != 1: raise RuntimeError('Cannot identify one official client process')
    pid = matches[0]['ProcessId']
    handle = K.OpenProcess(0x410, False, pid)  # QUERY_INFORMATION | VM_READ only
    if not handle: raise c.WinError(c.get_last_error())
    report = dict(pid=pid, executable=matches[0]['ExecutablePath'], candidates=[], bytes_read=0,
                  memory_written=False, gui_used=False, debugger_attached=False,
                  limitation='Candidates are raw structured matches, not proof of selected or rendered player.')
    start = time.monotonic()
    needles = {struct.pack('<II', selector, 1): selector for selector in range(30001, 30020)}
    try:
        address = 0
        while address < 0x80000000 and time.monotonic() - start < 45:
            info = MBI()
            if not K.VirtualQueryEx(handle, address, c.byref(info), c.sizeof(info)): break
            base = info.BaseAddress or 0
            end = base + info.RegionSize
            if end <= address: break
            if info.State == 0x1000 and info.Type == 0x20000 and not info.Protect & 0x101 and info.Protect & 0xCC:
                for offset in range(base, end, 4 * 1024 * 1024):
                    size = min(4 * 1024 * 1024 + 0x700, end - offset)
                    data = c.create_string_buffer(size)
                    done = c.c_size_t()
                    ok = K.ReadProcessMemory(handle, offset, data, size, c.byref(done))
                    if not ok or not done.value: continue
                    block = data.raw[:done.value]
                    report['bytes_read'] += done.value
                    for needle, selector in needles.items():
                        at = block.find(needle)
                        while at >= 0:
                            if at >= 0x494 and at + 0x10 <= len(block):
                                full = at - 0x494
                                playerid = struct.unpack_from('<I', block, full + 0x3AC)[0]
                                if 0 < playerid < 1000000:
                                    report['candidates'].append(dict(kind='full_player_candidate', address=hex(offset + full),
                                        selector=selector, playerid=playerid,
                                        headassetid=struct.unpack_from('<I', block, full + 0x484)[0]))
                            if at >= 0x74 and at + 0x2C <= len(block):
                                visual = at - 0x74
                                asset = struct.unpack_from('<I', block, visual + 8)[0]
                                proxy = struct.unpack_from('<I', block, visual + 0x88)[0]
                                eye = struct.unpack_from('<I', block, visual + 0x98)[0]
                                if 0 < asset < 1000000 and proxy in (0, 1, 2) and 0 <= eye <= 100:
                                    report['candidates'].append(dict(kind='visual_player_candidate', address=hex(offset + visual),
                                        selector=selector, playerassetid=asset, headClass=1, faceProxyHeadClass=proxy, eyeColor=eye))
                            at = block.find(needle, at + 4)
                    if time.monotonic() - start >= 45: break
            address = end
    finally:
        K.CloseHandle(handle)
    report['elapsed_seconds'] = round(time.monotonic() - start, 3)
    report['candidates'] = list({json.dumps(x, sort_keys=True): x for x in report['candidates']}.values())
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    output = ROOT / ('visual-inputs-' + stamp + '.json')
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(output=str(output), candidates=len(report['candidates']), bytes_read=report['bytes_read'])))

if __name__ == '__main__': main()
