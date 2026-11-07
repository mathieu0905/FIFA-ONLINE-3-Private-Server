"""Correct only this task's launch environment; preserve installed files and all progress."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
sys.dont_write_bytecode=True
import install
import prepare


def main():
    if not install.idle():
        prepare.write(prepare.ROOT/'runtime-recovery.json',dict(status='DEFERRED_GAME_RUNNING',message='更新已延后，当前游戏继续运行',services_action=False))
        print('DEFERRED_GAME_RUNNING');return
    probe="import sys,subprocess,json; p=subprocess.run([sys.executable,'-c',\"print('中文日志与한국어')\"],capture_output=True,text=True,check=True); assert '中文日志与한국어' in p.stdout; print(json.dumps({'parent_utf8':sys.flags.utf8_mode,'roundtrip':True}))"
    roundtrip=install.run([install.PY,'-X','utf8','-c',probe])
    assert json.loads(roundtrip)['parent_utf8']==1
    log=prepare.ROOT/'service.stderr.log';offset=log.stat().st_size if log.exists() else 0
    directory=prepare.ROOT/'runtime-env-fresh-snapshot'
    directory.mkdir(exist_ok=False)
    with install.locks():
        install.assert_idle()
        hot_before=install.get('http://127.0.0.1:8088/api/hot_update_status')
        play_before=(install.S/'play-local.bat').read_bytes()
        db_before=prepare.sha(install.S/'gamedata/fifadb.sqlite')
        install.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',install.S/'stop-server.ps1'])
        deadline=time.monotonic()+15
        while install.listening():
            if time.monotonic()>deadline:raise RuntimeError('Protected stop incomplete; do not launch duplicate services')
            time.sleep(.2)
        snapshot={name:(install.S/'gamedata'/name).read_bytes() for name in ('state.json','shop.json')}
        for name,body in snapshot.items():(directory/name).write_bytes(body)
        launcher,ready=install.restart()
    deadline=time.monotonic()+30
    while True:
        hot=install.get('http://127.0.0.1:8088/api/hot_update_status')
        if hot['revision']==hot_before['revision'] and hot['watcher_running'] and hot['error'] is None:break
        if time.monotonic()>deadline:raise RuntimeError('Existing business package activation not ready')
        time.sleep(.25)
    colors=install.get('https://127.0.0.1/static/info/teamcolor')
    assert colors['teamColors']
    time.sleep(1)
    errors=log.read_bytes()[offset:]
    assert b'UnicodeDecodeError' not in errors and b'Exception in thread' not in errors
    assert (install.S/'play-local.bat').read_bytes()==play_before
    assert prepare.sha(install.S/'gamedata/fifadb.sqlite')==db_before
    after=json.loads((install.S/'gamedata/state.json').read_bytes());before=json.loads(snapshot['state.json'])
    business=lambda state:{k:v for k,v in state.items() if k!='market_simulation'}
    report=dict(status='LAUNCH_ENVIRONMENT_CORRECTED_RUNTIME_READY',launcher_pid=launcher,readiness=ready,
        launch_environment={'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'},unicode_pipe_probe=json.loads(roundtrip),
        log_reader_error_after_restart=False,hot_update_status=hot,services_restored=install.listening()==[443,8088,28002],
        installed_files_unchanged=True,real_assets_written=False,
        state_business_equal=business(after)==business(before),shop_equal=(install.S/'gamedata/shop.json').read_bytes()==snapshot['shop.json'],
        snapshot=str(directory),GUI_used=False,native_game_verified=False,
        fixed_at=datetime.datetime.now().astimezone().isoformat())
    prepare.write(prepare.ROOT/'runtime-recovery.json',report)
    with install.locks():
        handback=json.loads((prepare.ROOT/'installed-handback.json').read_text('utf8'))
        handback.update(runtime_recovery=report,hot_update_status=hot,launcher_pid=launcher,services_restored=report['services_restored'])
        prepare.write(prepare.ROOT/'installed-handback.json',handback)
        top=prepare.ROOT.parent/'root-current-top.json';current=json.loads(top.read_text('utf8'))
        if current.get('top_preflight')==handback['top_preflight']:
            current.update(runtime_recovery=report,hot_update_status=hot,launcher_pid=launcher,services_restored=report['services_restored'])
            install.atomic(install.encoded(current),top)
        summary=json.loads((prepare.ROOT/'final-summary.json').read_text('utf8'))
        summary.update(runtime_recovery=str(prepare.ROOT/'runtime-recovery.json'),services_restored=report['services_restored'],
            business_hot_revision=hot['revision'],watcher_running=hot['watcher_running'],hot_error=hot['error'])
        prepare.write(prepare.ROOT/'final-summary.json',summary)
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
