"""User-authorized formal cutover. Holds both publication locks across restart."""
from pathlib import Path
import json,os,subprocess,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));import deploy as d
assert d.read(R/'test-results.json')['status']=='PASS'
assert d.read(R/'install-tests.json')['status']=='PASS'
def gameclosed():
    code="if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9};exit 0"
    p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',code],creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError('Game still running; no forced exit')
with (d.nullcontext() if d.S.resolve() in d._held_locks else d.locks(d.S)):
    gameclosed();d.preview(dict(server=d.S.resolve(),client=d.C.resolve()))
    stop="$ErrorActionPreference='Stop'; $managed=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\\.exe$' -and $_.CommandLine -match '(?i)D:\\\\FO3ID\\\\server\\\\(?:start_all|http_config|messenger)\\.py' }; foreach($p in $managed){Stop-Process -Id $p.ProcessId -ErrorAction SilentlyContinue}"
    error=None
    try:
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',stop+'; exit 0'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        d.stopped()
        result=d.install(review_sha=d.tx.sha(d.OUT/'manifest.json'))
    except BaseException as exc:
        error=exc
        # Only restart a completely valid old or new installed release.
        import re
        play=(d.S/'play-local.bat').read_bytes();name=re.search(rb'patches\\(\w+_preflight\.py)',play).group(1).decode()
        d.load(d.S/'patches'/name,'rollback_runtime_guard').preflight(d.S,d.C)
    env=os.environ.copy();env.update(FO3_GAME=str(d.C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20')
    with (R/'formal.stdout.log').open('ab') as stdout,(R/'formal.stderr.log').open('ab') as stderr:
        proc=subprocess.Popen([str(d.S/'.venv/Scripts/python.exe'),'-u',str(d.S/'start_all.py')],cwd=d.S,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    ready=subprocess.run([str(d.S/'.venv/Scripts/python.exe'),'-B',str(d.S/'wait_services.py'),'--timeout','25'],cwd=d.S,env=env,capture_output=True,text=True)
    if ready.returncode:raise RuntimeError('Service restart failed: '+ready.stdout+ready.stderr)
    if error:raise error
    result.update(service_restart=True,launcher_pid=proc.pid,readiness=ready.stdout.strip())
    d.write(R/'cutover-result.json',result);print(json.dumps(result))
