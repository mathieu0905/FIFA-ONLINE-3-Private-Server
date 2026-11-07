"""Separate service and client actions. No batch files are executed."""
from pathlib import Path
import argparse,datetime,importlib.util,json,os,re,socket,subprocess,sys,time
S=Path(__file__).resolve().parent.parent
PY=S/'.venv/Scripts/python.exe'
PS=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
HIDDEN=subprocess.CREATE_NO_WINDOW

def say(s):print(s,flush=True)
def run(args,**kwargs):
    result=subprocess.run([str(x) for x in args],cwd=S,creationflags=HIDDEN,**kwargs)
    if result.returncode:raise RuntimeError('步骤失败，退出码 '+str(result.returncode))

def closed():
    r=subprocess.run([str(PS),'-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 1}'],creationflags=HIDDEN)
    if r.returncode:raise RuntimeError('游戏正在运行，请先正常退出游戏。')

def gate():
    # The legacy launcher remains the version descriptor for existing publishers.
    # Reading its single preflight line does not execute the batch file.
    matches=re.findall(rb'(?m)^\.venv\\Scripts\\python\.exe (patches\\[a-zA-Z0-9_]+_preflight\.py)\r?$',(S/'play-local.bat').read_bytes())
    if len(matches)!=1:raise RuntimeError('无法识别当前发布版本，请联系维护者。')
    return S/matches[0].decode().replace('\\','/')

def validate():
    say('正在校验当前正式版本…');run([PY,'-B',gate()])
    say('正在检查球员与模型完整性…');run([PY,'-B',S/'tools/player_import/check.py'])

def ready():
    spec=importlib.util.spec_from_file_location('fo3_services_ready',S/'wait_services.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    try:module.ready();return True
    except (OSError,ValueError,RuntimeError):return False

def busy_ports():
    ports=[]
    for port in (443,8088,28002):
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.3):ports.append(port)
        except OSError:pass
    return ports

def start_server():
    if ready():say('服务端已经运行，无需重复启动。');return
    closed()
    ports=busy_ports()
    if ports:raise RuntimeError('服务尚未完整就绪，但端口已被占用：'+str(ports)+'。请先检查或停止原服务。')
    validate()
    if not (S/'gamedata/fifadb.sqlite').is_file():raise RuntimeError('缺少正式球员数据库。')
    env=dict(os.environ,FO3_GAME='D:/FO3ID/32795',FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',PYTHONIOENCODING='utf-8')
    log=S/'captures/native-server-start.log';log.parent.mkdir(exist_ok=True)
    say('正在后台启动 HTTPS、管理页和消息服务…')
    with log.open('ab',buffering=0) as f:
        p=subprocess.Popen([str(PY),'-B','-u',str(S/'start_all.py')],cwd=S,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP)
    try:run([PY,'-B',S/'wait_services.py'])
    except Exception:
        raise RuntimeError('服务启动未就绪，请查看 '+str(log)+'；后台进程 '+str(p.pid))
    say('服务端已就绪，可以单独打开客户端。')

def stop_server():
    closed();say('正在停止本安装的服务端…')
    run([PS,'-NoProfile','-ExecutionPolicy','Bypass','-File',S/'stop-server.ps1'])
    say('服务端已停止。')

def start_client():
    closed()
    if not ready():raise RuntimeError('服务端尚未就绪，请先点击“启动服务端”。')
    # Launch installed files only. Publication owns resource installation and checks.
    # A release lock must never turn an ordinary client launch into a write transaction.
    closed()
    env=dict(os.environ,__COMPAT_LAYER='RunAsInvoker')
    subprocess.Popen([str(S/'launcher/fifalauncher.exe')],cwd=S/'launcher',env=env,creationflags=HIDDEN)
    say('客户端启动请求已发送。服务端保持运行。')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('check','server-start','server-stop','client-start'));args=parser.parse_args()
    if args.action=='client-start':
        start_client();return
    if args.action=='server-start' and ready():
        say('服务端已经运行，无需重复启动。');return
    lock=None;token=json.dumps(dict(pid=os.getpid(),task='native-launcher-'+args.action))
    try:
        if args.action!='check':
            lock=S/'.shop-release.lock'
            try:
                with lock.open('x') as f:f.write(token)
            except FileExistsError:
                raise RuntimeError('正在发布更新，暂不能启动或停止服务端；已有服务就绪时仍可打开客户端。') from None
        {'check':validate,'server-start':start_server,'server-stop':stop_server,'client-start':start_client}[args.action]()
    finally:
        if lock and lock.exists() and lock.read_text()==token:lock.unlink()

if __name__=='__main__':
    try:main()
    except Exception as e:say('错误：'+str(e));sys.exit(1)
