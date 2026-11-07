"""Fresh-parent server transaction. Never interrupt an active game."""
from contextlib import contextmanager
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import ssl

sys.dont_write_bytecode = True
R = Path(__file__).resolve().parent
S = Path(r'D:\FO3ID\server')
C = Path(r'D:\FO3ID\32795')
SELF = 'patches/ai_opponent_progression_preflight.py'
MANIFEST = 'patches/ai-opponent-progression-installed.json'
RECEIPT = 'patches/ai-opponent-progression-receipt.json'
DOC = 'docs/工程经验与修改边界.txt'
ALLOWED = {'ai_opponent_progression.py', 'http_config.py', DOC, SELF, MANIFEST, RECEIPT, 'play-local.bat'}
DOC_ENTRY = '''\n\nFO3-AI-PROGRESSION-001（2026-11-07，ai-opponents-grade10-level30-v1）\n用户要求不改AI难度参数，电脑对手全部+10、30级。只在match_side的user is None分支深拷贝本场电脑阵容，给全部首发/替补/后备设置grade=10、levelinfo={level:30,exp:0}，再交原序列化/阵型/摘要逻辑；身份、模型、战术、难度和用户侧保持原逻辑。既有等级30属性曲线继续复用。原始roster、创建经理、玩家卡及真实state/shop不迁移不改写；仅之后新建比赛应用，不改已保存/进行中的比赛。\n临时内存验证40项通过：四队全员与原输入/用户侧隔离、已有高强化/经验不回写、15级联赛手控及经理模式、5档杯赛/加时规则。正式/运行时验证以D:/fifaol3/ai-opponent-progression/installed-handback.json为准；游戏GUI、实际比赛待用户验收。该钩子不属于ABI2热更新范围，只在游戏未运行且取得共同双锁时提交/正常重启。回归：正式.venv Python -B D:/fifaol3/ai-opponent-progression/test.py。\n'''


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf8')


def digest(body):
    return hashlib.sha256(body).hexdigest()


def sha(path):
    return digest(Path(path).read_bytes())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def closed():
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                             'if(Get-Process fifazf -ErrorAction SilentlyContinue){exit 9}'],
                            creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    if result.returncode:
        raise RuntimeError('更新已延后，当前游戏继续运行')


@contextmanager
def locks():
    owned = []
    try:
        for name in ('.shop-release.lock', '.fo3-publish.lock'):
            path = S/name
            fd = os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os, 'O_BINARY', 0))
            body = encoded(dict(pid=os.getpid(), task='ai-opponent-progression',
                                thread='01a1b3ef-a0a3-79f2-9005-989eb5b9669d'))
            owned.append((path, fd, body))
            os.write(fd, body)
            os.fsync(fd)
        yield
    finally:
        for path, fd, body in reversed(owned):
            os.close(fd)
            if path.exists() and path.read_bytes() == body:
                path.unlink()


def plan():
    play = (S/'play-local.bat').read_bytes()
    found = re.search(rb'patches\\(\w+_preflight\.py)', play)
    if not found:
        raise RuntimeError('Current launcher preflight not found')
    parent_rel = 'patches/'+found.group(1).decode()
    if parent_rel == SELF:
        raise RuntimeError('Already installed; use current preflight to verify')
    parent = load(S/parent_rel, 'ai_parent')
    prior = parent.preflight(S, C)
    composition = parent.compose_manifest(S, C)
    validator = load(S/'patches/startup_market_preflight.py', 'ai_validator')
    validator.verify_manifest(composition, S, C)
    guards = validator.table(composition['guards'])
    parent_receipt = json.loads((S/parent.RECEIPT).read_text('utf-8-sig'))
    source = (S/parent_rel).read_text('utf8')
    for old, new in ((parent.MANIFEST, MANIFEST), (parent.RECEIPT, RECEIPT),
                     (parent.SELF, SELF), (parent_receipt['status'], 'INSTALLED_AI_PROGRESSION'),
                     (prior['status'], 'AI_OPPONENT_PROGRESSION_PREFLIGHT_PASS')):
        if old not in source:
            raise RuntimeError('Unsupported fresh parent helper shape: '+old)
        source = source.replace(old, new)
    anchor = '\n if not required<=seen:'
    if source.count(anchor) != 1:
        raise RuntimeError('Fresh parent required-guard block needs review')
    source = source.replace(anchor, "\n required.update({('server','ai_opponent_progression.py'),('server','http_config.py'),('server','"+DOC+"')})"+anchor)
    compile(source, SELF, 'exec')
    http = (S/'http_config.py').read_bytes()
    marker = b'if __name__ == "__main__":'
    if http.count(marker) != 1 or b'import ai_opponent_progression' in http:
        raise RuntimeError('Fresh HTTP hook boundary differs')
    hook = b'import ai_opponent_progression\nai_opponent_progression.install(sys.modules[__name__])\n\n'
    patched_http = http.replace(marker, hook+marker)
    compile(patched_http, 'http_config.py', 'exec')
    doc = (S/DOC).read_bytes()
    if b'FO3-AI-PROGRESSION-001' in doc:
        raise RuntimeError('AI progression ledger entry already exists')
    payloads = {'ai_opponent_progression.py': (R/'ai_opponent_progression.py').read_bytes(),
                'http_config.py': patched_http, DOC: doc+DOC_ENTRY.encode('utf8'),
                SELF: source.encode('utf8'),
                'play-local.bat': play.replace(parent_rel.replace('/', '\\').encode(), SELF.replace('/', '\\').encode())}
    for rel, body in payloads.items():
        key = ('server', rel.casefold())
        if key in guards and sha(S/rel) != guards[key]['sha256']:
            raise RuntimeError('Fresh parent target mismatch: '+rel)
        if rel in (SELF, 'ai_opponent_progression.py') and (S/rel).exists():
            raise RuntimeError('Additive target already exists: '+rel)
        guards[key] = dict(root='server', relative=rel, sha256=digest(body))
    composition['guards'] = list(guards.values())
    composition['files_verified'] = False
    composition.setdefault('ancestry', []).append(dict(layer='ai-opponent-progression-v1', native_status='PENDING'))
    revision = 'ai-opponent-progression-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    manifest = dict(schema=1, revision=revision, client=str(C), state_shop_replaced=False,
                    guards=composition['guards'], composition=composition,
                    parent_preflight=parent_rel, parent_preflight_sha256=sha(S/parent_rel))
    payloads[MANIFEST] = encoded(manifest)
    payloads[RECEIPT] = encoded(dict(status='INSTALLED_AI_PROGRESSION', revision=revision,
                                   manifest_sha256=digest(payloads[MANIFEST]), state_shop_replaced=False,
                                   native_status='PENDING'))
    assert set(payloads) == ALLOWED
    for rel in (MANIFEST, RECEIPT):
        if (S/rel).exists():
            raise RuntimeError('Immutable metadata already exists: '+rel)
    before = {rel: (S/rel).read_bytes() if (S/rel).exists() else None for rel in payloads}
    return dict(payloads=payloads, before=before, parent=parent_rel,
                parent_hash=sha(S/parent_rel), revision=revision, prior=prior,
                module_hash=sha(R/'ai_opponent_progression.py'))


def atomic_cas(target, before, after):
    actual = target.read_bytes() if target.exists() else None
    if actual != before:
        raise RuntimeError('Concurrent target change: '+str(target))
    if after is None:
        target.unlink()
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name+'.ai-progress-'+str(os.getpid())+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
        if (target.read_bytes() if target.exists() else None) != before:
            raise RuntimeError('Concurrent change before replace: '+str(target))
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def apply(p):
    closed()
    if sha(S/p['parent']) != p['parent_hash'] or sha(R/'ai_opponent_progression.py') != p['module_hash']:
        raise RuntimeError('Reviewed build or fresh parent changed')
    backup = S/'backups'/p['revision']
    backup.mkdir(parents=True)
    for rel, body in p['before'].items():
        if body is not None:
            target = backup/rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
    committed = []
    try:
        for rel in [r for r in p['payloads'] if r != 'play-local.bat']+['play-local.bat']:
            closed()
            atomic_cas(S/rel, p['before'][rel], p['payloads'][rel])
            committed.append(rel)
        proof = load(S/SELF, 'ai_installed_gate').preflight(S, C)
    except BaseException:
        conflicts = []
        for rel in reversed(committed):
            try:
                atomic_cas(S/rel, p['payloads'][rel], p['before'][rel])
            except RuntimeError:
                conflicts.append(rel)
        if conflicts:
            raise RuntimeError('Later legitimate changes retained during rollback: '+repr(conflicts))
        raise
    return dict(status='INSTALLED', revision=p['revision'], backup=str(backup), preflight=proof,
                top_preflight=str(S/SELF), top_manifest=str(S/MANIFEST), top_receipt=str(S/RECEIPT),
                composition_api='compose_manifest(server=None,client=None)', state_shop_written=False)


def call(path):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    with opener.open('https://127.0.0.1'+path, timeout=15) as response:
        return json.load(response)


def hot_status():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8088/api/hot_update_status', timeout=10) as response:
        return json.load(response)


def stop():
    closed()
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                             '-File', str(S/'stop-server.ps1')], capture_output=True, text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Protected stop refused; no formal files written: '+result.stdout+result.stderr)
    for _ in range(25):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
            'if(Get-NetTCPConnection -State Listen -LocalPort 443,8088,28002 -ErrorAction SilentlyContinue){exit 9}'],
            creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode == 0:
            return
        time.sleep(.2)
    raise RuntimeError('Listeners still active after protected stop; no formal files written')


def start():
    closed()
    env = os.environ.copy()
    env.update(FO3_GAME=str(C), FO3_LANGUAGE='chi', FO3_MAX_GRADE='20')
    env['PSModulePath'] = os.path.expandvars(r'%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules')
    with (R/'service.stdout.log').open('ab') as out, (R/'service.stderr.log').open('ab') as err:
        process = subprocess.Popen([str(S/'.venv/Scripts/python.exe'), '-B', '-u', str(S/'start_all.py')],
                    cwd=S, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                    creationflags=subprocess.CREATE_NO_WINDOW)
    ready = subprocess.run([str(S/'.venv/Scripts/python.exe'), '-B', str(S/'wait_services.py'), '--timeout', '30'],
                cwd=S, env=env, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if ready.returncode:
        raise RuntimeError('Services did not become ready: '+ready.stdout+ready.stderr)
    return process.pid, ready.stdout.strip()


def main():
    closed()  # Before locks, snapshots, writes or service interruption.
    tests = json.loads((R/'tests.json').read_text('utf8'))
    assert tests['status'] == 'PASS' and tests['case_count'] == 40
    assert tests['source_sha256'] == sha(R/'ai_opponent_progression.py')
    transaction_tests = json.loads((R/'transaction-tests.json').read_text('utf8'))
    assert transaction_tests['status'] == 'PASS' and transaction_tests['installer_sha256'] == sha(R/'install.py')
    with locks():
        closed()
        p = plan()
        (R/'plan.json').write_bytes(encoded({k:v for k,v in p.items() if k not in ('payloads', 'before')}))
        old_hot = hot_status()
        stop()  # Any failure/defer aborts; never apply/start from that branch.
        snapshot = {name: (S/'gamedata'/name).read_bytes() for name in ('state.json', 'shop.json')}
        for name, body in snapshot.items():
            (R/('stopped-'+name)).write_bytes(body)
        result = None
        error = None
        try:
            result = apply(p)
        except BaseException as exc:
            error = exc
        # A successfully stopped installation restores services even on rollback.
        # If a game appeared after stop, closed() prevents any further activation.
        launcher, ready = start()
        if error:
            raise error
        result.update(service_restart=True, launcher_pid=launcher, readiness=ready)
    # The business watcher deliberately waits for both publication locks. Never
    # wait for its cold-start restore while retaining those locks.
    finish(result, snapshot, old_hot)


def finish(result, snapshot, old_hot):
    rules = call('/info/ai-opponent-rules')
    assert rules['version'] == 'ai-opponents-grade10-level30-v1' and rules['grade'] == 10 and rules['level'] == 30
    hot = hot_status()
    deadline = time.monotonic()+15
    while (hot.get('revision') != old_hot['revision'] or not hot.get('watcher_running')) and time.monotonic() < deadline:
        time.sleep(.2)
        hot = hot_status()
    assert hot['revision'] == old_hot['revision'] and hot['error'] is None and hot['watcher_running']
    assert hot['routes'] == old_hot['routes']
    with locks():
        if SELF.replace('/', '\\').encode() not in (S/'play-local.bat').read_bytes():
            raise RuntimeError('Newer legal top retained; refusing stale handback overwrite')
        # Other valid writes (market background ticks) may resume after startup.
        before_state = json.loads(snapshot['state.json'])
        after_state = json.loads((S/'gamedata/state.json').read_bytes())
        business = lambda st: {k:v for k,v in st.items() if k != 'market_simulation'}
        assert business(before_state) == business(after_state), 'Concurrent business progress preserved; never restore old state'
        assert (S/'gamedata/shop.json').read_bytes() == snapshot['shop.json']
        check = subprocess.run([str(S/'.venv/Scripts/python.exe'), '-B', str(S/'tools/player_import/check.py')],
                              cwd=S, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        assert check.returncode == 0, check.stdout+check.stderr
        result.update(status='INSTALLED_AND_RUNTIME_ACTIVE', runtime_active=True, services_restored=True,
                      rules=rules, hot_update_status=hot, native_game_verified=False,
                      hashes={rel: sha(S/rel) for rel in ALLOWED},
                      validation=dict(memory_cases=json.loads((R/'tests.json').read_text('utf8'))['case_count'], player_import=True,
                                      state_business_exact=True, shop_exact=True, game_gui_used=False),
                      observed_at=datetime.datetime.now().astimezone().isoformat())
        (R/'installed-handback.json').write_bytes(encoded(result))
        (Path(r'D:\fifaol3')/'root-current-top.json').write_bytes(encoded(result))
        print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
