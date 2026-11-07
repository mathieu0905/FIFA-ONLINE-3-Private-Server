"""Exercise the noninterruption boundary before any official file access."""
from pathlib import Path
import json
import tempfile
from install_when_idle import install, impact, HERE


def main():
    checks = []
    with tempfile.TemporaryDirectory(prefix='idle-install-guard-', dir=HERE) as temp:
        root = Path(temp)
        server = root / 'never-created-server'
        for process in [dict(Name='fifazf.exe', ProcessId=1),
                        dict(Name='python.exe', ProcessId=2, CommandLine='D:/FO3ID/server/http_config.py'),
                        dict(Name='python.exe', ProcessId=3, CommandLine='D:/FO3ID/server/messenger.py')]:
            result = install(server, root / 'client', lambda: [process])
            assert result['status'] == 'DEFERRED_GAME_CONTINUES'
            assert result['formal_written'] is False and result['formal_activated'] is False
            assert result['services_action'] == 'none' and not server.exists()
            checks.append('Refused before official path/lock/write for ' + process['Name'] + ':' + str(process['ProcessId']))
        assert impact(lambda: [])['status'] == 'IDLE_INSTALL_AVAILABLE'
        checks.append('Idle impact inspection does not itself install or start services')
        try:
            def failed_probe():
                raise RuntimeError('Inventory unavailable')
            install(server, root / 'client', failed_probe)
        except RuntimeError:
            assert not server.exists()
        else:
            raise AssertionError('Failed process probe must refuse installation')
        checks.append('Inventory failure is fail-closed before official access')
    report = dict(status='PASS', checks=checks, native_verified=False)
    (HERE / 'idle-install-regression.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
