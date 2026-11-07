from pathlib import Path
import json,os,subprocess,sys
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server');C=Path(r'D:\FO3ID\32795')
sys.path.insert(0,str(R));import install
flags=subprocess.CREATE_NO_WINDOW
def ps(code):
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',"$ErrorActionPreference='Stop'; "+code],capture_output=True,text=True,creationflags=flags)
    if result.returncode:raise RuntimeError(result.stderr or result.stdout)
    return result
with install.publish_lock(S):
    ps("if(Get-Process fifazf -ErrorAction SilentlyContinue){throw 'Game is running'}")
    m=json.loads((R/'nostalgia-stats-release-manifest.json').read_text(encoding='utf8'))
    install.load(S/m['parent_preflight'],'locked_parent').preflight(S,C)
    for row in m['files']:
        p=(S if row['root']=='server' else C)/row['relative']
        assert (install.sha(p) if p.exists() else None)==row['parent_sha256'],'Concurrent target changed'
    stopped=False
    try:
        ps(r"$managed=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match '(?i)D:\\FO3ID\\server\\(?:start_all|http_config|messenger)\.py' }; foreach($p in $managed){Stop-Process -Id $p.ProcessId -ErrorAction SilentlyContinue}")
        stopped=True
        result=install._install_locked(S,C)
        print(json.dumps(dict(status='INSTALLED',files=result['files'])),flush=True)
    finally:
        if stopped:
            env={**os.environ,'FO3_GAME':str(C),'FO3_LANGUAGE':'chi','FO3_MAX_GRADE':'20'}
            with (R/'service.stdout.log').open('ab') as out,(R/'service.stderr.log').open('ab') as err:
                subprocess.Popen([str(S/'.venv/Scripts/python.exe'),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdout=out,stderr=err,stdin=subprocess.DEVNULL,creationflags=flags)
