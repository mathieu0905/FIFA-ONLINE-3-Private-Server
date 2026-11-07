"""Direct production club balance install with current guards, CAS and game protection."""
from contextlib import contextmanager
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
import uuid
sys.dont_write_bytecode=True
import common as prepare

R=prepare.R;S=prepare.S;C=prepare.C
PY=S/'.venv/Scripts/python.exe'
HIDDEN=subprocess.CREATE_NO_WINDOW
SELF='patches/club_base_balance_20261107_preflight.py'
MANIFEST='patches/25ucl-import-20261107-installed.json'
RECEIPT='patches/25ucl-import-20261107-receipt.json'
EVIDENCE='patches/25ucl-import-20261107-evidence.json.gz'
DOC='docs/工程经验与修改边界.txt' 


def encoded(obj):return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf8')
def digest(body):return hashlib.sha256(body).hexdigest()
def run(args,**kwargs):
    result=subprocess.run([str(x) for x in args],cwd=S,capture_output=True,text=True,encoding='utf8',errors='replace',creationflags=HIDDEN,env=environment(),**kwargs)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout.strip()
def environment():
    env=dict(os.environ,FO3_GAME=str(C),FO3_LANGUAGE='chi',FO3_MAX_GRADE='20',PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    env['PSModulePath']=str(Path(env.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/Modules')+';'+str(Path(env.get('ProgramFiles','C:/Program Files'))/'WindowsPowerShell/Modules')
    return env
def idle():
    result=subprocess.run(['powershell.exe','-NoProfile','-Command','if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],env=environment(),creationflags=HIDDEN)
    return result.returncode==0
def assert_idle():
    if not idle():raise RuntimeError('更新已延后，当前游戏继续运行')


@contextmanager
def locks(server=S):
    owned=[]
    try:
        for name in ('.shop-release.lock','.fo3-publish.lock'):
            path=server/name
            body=encoded(dict(pid=os.getpid(),task='25ucl-import',created=datetime.datetime.now().astimezone().isoformat()))
            fd=os.open(path,os.O_EXCL|os.O_CREAT|os.O_WRONLY|getattr(os,'O_BINARY',0))
            owned.append((path,fd,body));os.write(fd,body);os.fsync(fd)
        yield
    finally:
        for path,fd,body in reversed(owned):
            os.close(fd)
            if path.exists() and path.read_bytes()==body:path.unlink()


def atomic(source,target):
    target=Path(target);tmp=target.with_name(target.name+'.ucl25-'+uuid.uuid4().hex)
    try:
        if isinstance(source,Path):shutil.copyfile(source,tmp)
        else:tmp.write_bytes(source)
        os.replace(tmp,target)
    finally:tmp.unlink(missing_ok=True)


def current_hash(path):return prepare.sha(path) if path.exists() else None
def cas(entry):
    if current_hash(entry['target'])!=entry['before']:raise RuntimeError('Concurrent file change: '+str(entry['target']))
    atomic(entry['source'],entry['target'])


def rollback(entries):
    retained=[]
    for entry in reversed(entries):
        target=entry['target']
        if current_hash(target)!=entry['after']:
            retained.append(str(target));continue
        if entry['before'] is None:target.unlink()
        else:atomic(entry['backup'],target)
    return retained


def listening():
    ports=[]
    for port in (443,8088,28002):
        try:
            with socket.create_connection(('127.0.0.1',port),.3):ports.append(port)
        except OSError:pass
    return ports


def get(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    with opener.open(url,timeout=20) as response:return json.load(response)


def restart():
    assert_idle()
    with (R/'service.stdout.log').open('ab') as out,(R/'service.stderr.log').open('ab') as err:
        p=subprocess.Popen([str(PY),'-B','-u',str(S/'start_all.py')],cwd=S,env=environment(),stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=HIDDEN)
    ready=run([PY,'-B',S/'wait_services.py','--timeout','30'])
    return p.pid,ready


