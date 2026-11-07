"""Install the verified ability delta only with game AND managed services idle.

No service stop/start, kill, socket mutation or hot-host monkey patch is present.
Default invocation is impact-only; --apply refuses a live process before locks,
backups or any official write. An idle installation needs a normal later start.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SERVER = Path('D:/FO3ID/server')
CLIENT = Path('D:/FO3ID/32795')


def probe_processes():
    command = r"Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -eq 'fifazf.exe' -or ($_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match '(?i)D:[\\/]FO3ID[\\/]server[\\/](?:http_config|messenger|start_all)\.py') } | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    powershell = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(powershell), '-NoProfile', '-Command', command],
                            capture_output=True, text=True, encoding='utf8', errors='replace',
                            creationflags=subprocess.CREATE_NO_WINDOW, timeout=20)
    if result.returncode:
        raise RuntimeError('Cannot establish whether game/services are idle: ' + result.stderr)
    data = json.loads(result.stdout.strip()) if result.stdout.strip() else []
    data = data if isinstance(data, list) else [data]
    if any(not isinstance(row, dict) or not row.get('Name') or not row.get('ProcessId') for row in data):
        raise RuntimeError('Invalid process inventory; refuse installation')
    return data


def impact(process_probe=probe_processes):
    processes = process_probe()
    return dict(status='DEFERRED_GAME_CONTINUES' if processes else 'IDLE_INSTALL_AVAILABLE',
                message='更新已延后，当前游戏继续运行。' if processes else '仅在游戏与正式服务均停止时安装；本工具不会停止或启动任何进程。',
                requires_cold_start=True, hot_abi_supported=False,
                processes=processes, formal_written=False, formal_activated=False,
                services_action='none', gui_action='none')


def install(server=SERVER, client=CLIENT, process_probe=probe_processes):
    if (HERE / 'superseded.json').exists():
        return dict(status='SUPERSEDED_BY_REQUESTED_MODEL_RETRAINING', formal_written=False,
                    formal_activated=False, services_action='none', gui_action='none',
                    message='Earlier rule-only replacement is retired; use the requested trained model after validation.')
    result = impact(process_probe)
    if result['processes']:
        return result
    regression = json.loads((HERE / 'regression.json').read_text('utf8'))
    hashes = json.loads((HERE / 'payload-hashes.json').read_text('utf8'))
    if regression['status'] != 'PASS' or regression['payload_hashes'] != hashes:
        raise RuntimeError('Regression does not cover this payload')
    payload = {rel: (HERE / 'payload' / rel).read_bytes() for rel in hashes}
    if any(hashlib.sha256(payload[rel]).hexdigest() != digest for rel, digest in hashes.items()):
        raise RuntimeError('Verified payload changed')
    baseline = json.loads((HERE / 'source-baseline.json').read_text('utf8'))
    sys.path.insert(0, str(server))
    spec = importlib.util.spec_from_file_location('_ability_release', server / 'hot_update_release.py')
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    with release.locks(server, 'ability-value-v1'):
        # Launcher server-start obeys this same first lock; a new server cannot
        # be launched through it between this check and our final play CAS.
        result = impact(process_probe)
        if result['processes']:
            return result
        coordination = json.loads(Path('D:/fifaol3/coordination-current.json').read_text('utf8'))
        if coordination.get('current_unhanded_writers') or coordination.get('next_formal_writer') or coordination.get('queue'):
            raise RuntimeError('Another coordinated install owns the formal write window; defer to its owner')
        for rel, digest in baseline.items():
            if release.sha(server / rel) != digest:
                raise RuntimeError('Fresh official baseline changed; rebase, do not overwrite: ' + rel)
        # Preserve historical prices and real assets as evidence, never as a
        # rollback target. The transaction below never writes any of them.
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        snapshot = HERE / ('idle-snapshot-' + stamp)
        snapshot.mkdir()
        protected = ['gamedata/state.json', 'gamedata/shop.json', 'gamedata/npc-market-prices.sqlite']
        before = {}
        for rel in protected:
            data = (server / rel).read_bytes()
            (snapshot / Path(rel).name).write_bytes(data)
            before[rel] = hashlib.sha256(data).hexdigest()
        experience = 'docs/工程经验与修改边界.txt'
        text = (server / experience).read_text('utf8')
        note = '''

FO3-ABILITY-VALUE-001（2026-11-07，ability-value-v1，实机PENDING）：
确认旧模型仅提高莱斯科特positioning 32→66便令初价316→63 EP；正式60866条价格中28307条为1 EP。初价复算匹配历史seed，不修改旧模型/seed/成交回执消错。
修复采用原生ROLE_WEIGHTS与正权重支持能力、显式FO3逆足/花式代码、连续递增本地EP曲线，不再对估价除1000。12张历史40季卡的-1..-3能力只在估值中显式按0计并在解释中列出，不改球员DB；已有特殊花式code5保留、溢出档不加价。姓名/赛季/动画/特性编号不作不明金额溢价。现有强化投资倍率使用精确有理数，相关能力增加不降价。
历史seed/prices/price_events和state/shop逐字节不写；旧市场变动按原basis/initial的比率保留并限制0.9～1.1，不把旧绝对价格当新身价。旧玩家挂单/成交/款项及已展示NPC数量/报价继续正常到期，新报价按能力生成，不重填库存。
当前ABI1不支持市场后台对象替换。安装器在任何正式写入前检查游戏与正式服务进程，有运行者即“更新已延后，当前游戏继续运行”；不调用stop/reload/kill，不自动重启。安装仅在两者均停止后，fresh父层、共同双锁、全部guard/receipt、备份/CAS提交；运行时生效需正常冷启动，静态回归不冒充已激活或实机比赛通过。
证据D:/fifaol3/value-diagnosis/{report.json,regression.json,install-status.json}；回归test_ability_value.py，安装install_when_idle.py --apply。资产有后续变化仅保留并报告，不回旧存档。货币曲线为可解释的本服平衡规则，并非实机表现已经标定的结论。
'''
        payload[experience] = (text + note).encode('utf8')
        result = impact(process_probe)
        if result['processes']:
            return result
        installed = release.commit(server, client, 'ability_value', payload)
        after = {rel: release.sha(server / rel) for rel in protected}
        installed.update(status='INSTALLED_AWAITING_NORMAL_COLD_START', formal_written=True,
                         formal_activated=False, services_action='none', gui_action='none',
                         protected_hashes_before=before, protected_hashes_after=after,
                         protected_unchanged=before == after, fresh_snapshot=str(snapshot),
                         native_verified=False, regression=str(HERE / 'regression.json'))
        # Only an actual successful official transaction advances the observation.
        release.atomic(Path('D:/fifaol3/root-current-top.json'), release.body(installed))
        return installed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    result = install() if args.apply else impact()
    result['checked_at'] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    (HERE / 'install-status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
