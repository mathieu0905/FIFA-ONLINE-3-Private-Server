"""Minimal temporary file tests; no private service or formal writes."""
import json
from pathlib import Path
import sys
import tempfile
import types
from contextlib import contextmanager
sys.dont_write_bytecode = True
import install as d


def main():
    cases = []
    with tempfile.TemporaryDirectory(prefix='transaction-', dir=d.R) as tmp:
        root = Path(tmp)
        file = root/'a.bin'
        d.atomic_cas(file, None, b'new')
        assert file.read_bytes() == b'new'
        cases.append('add')
        d.atomic_cas(file, b'new', b'updated')
        assert file.read_bytes() == b'updated'
        cases.append('replace')
        try:
            d.atomic_cas(file, b'stale', b'wrong')
        except RuntimeError:
            pass
        else:
            raise AssertionError('Stale baseline accepted')
        assert file.read_bytes() == b'updated'
        cases.append('stale_cas_rejected')
        d.atomic_cas(file, b'updated', b'new')
        cases.append('own_version_rollback')
        file.write_bytes(b'later legitimate write')
        try:
            d.atomic_cas(file, b'new', None)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Rollback overwrote subsequent change')
        assert file.read_bytes() == b'later legitimate write'
        cases.append('later_writer_preserved')
        d.atomic_cas(file, b'later legitimate write', None)
        assert not file.exists()
        cases.append('remove_own_added_file')
        formal = d.S
        d.S = root
        try:
            with d.locks():
                assert (root/'.shop-release.lock').exists() and (root/'.fo3-publish.lock').exists()
            assert not list(root.glob('*.lock'))
            cases.append('dual_locks_released')
            lock = root/'.fo3-publish.lock'
            lock.write_bytes(b'other writer')
            try:
                with d.locks():
                    raise AssertionError('Conflicting lock accepted')
            except FileExistsError:
                pass
            assert lock.read_bytes() == b'other writer' and not (root/'.shop-release.lock').exists()
            cases.append('lock_conflict_preserves_owner')
        finally:
            d.S = formal
        # main() must defer before even reading test manifests or acquiring locks.
        old_closed, old_locks = d.closed, d.locks
        def defer():
            raise RuntimeError('更新已延后，当前游戏继续运行')
        def forbidden_locks():
            raise AssertionError('Locks touched after deferral')
        d.closed, d.locks = defer, forbidden_locks
        try:
            try:
                d.main()
            except RuntimeError as error:
                assert '更新已延后' in str(error)
            else:
                raise AssertionError('Game-running guard did not defer')
            cases.append('game_running_defers_before_any_transaction')
        finally:
            d.closed, d.locks = old_closed, old_locks
        # Fault each position of the actual seven-file transaction. These are
        # tiny byte fixtures, not a copied/runnable game service.
        old_server, old_closed, old_cas = d.S, d.closed, d.atomic_cas
        try:
            d.closed = lambda: None
            for failure in range(1, 8):
                fixture = root/('failure-'+str(failure))
                fixture.mkdir()
                (fixture/'parent.py').write_bytes(b'parent identity')
                payloads = {rel: ('new '+rel).encode() for rel in sorted(d.ALLOWED)}
                before = {rel: None for rel in payloads}
                for rel in ('http_config.py', d.DOC, 'play-local.bat'):
                    before[rel] = ('old '+rel).encode()
                    path = fixture/rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(before[rel])
                p = dict(payloads=payloads, before=before, parent='parent.py',
                         parent_hash=d.sha(fixture/'parent.py'), revision='io-fault',
                         module_hash=d.sha(d.R/'ai_opponent_progression.py'))
                d.S = fixture
                calls = [0]
                def inject(target, expected, replacement):
                    calls[0] += 1
                    if calls[0] == failure:
                        raise OSError('Injected I/O failure')
                    return old_cas(target, expected, replacement)
                d.atomic_cas = inject
                try:
                    d.apply(p)
                except OSError:
                    pass
                else:
                    raise AssertionError('Injected fault accepted')
                for rel, expected in before.items():
                    path = fixture/rel
                    assert (path.read_bytes() if path.exists() else None) == expected
                cases.append('seven_file_rollback_position_'+str(failure))
        finally:
            d.S, d.closed, d.atomic_cas = old_server, old_closed, old_cas
        # Cold-start business restore must be checked only after publication
        # locks have been released; the real watcher refuses reload under lock.
        names = ('R', 'S', 'closed', 'locks', 'plan', 'hot_status', 'stop', 'apply', 'start', 'finish')
        originals = {name: getattr(d, name) for name in names}
        fixture = root/'watcher-order'
        fixture.mkdir()
        (fixture/'gamedata').mkdir()
        for name in ('state.json', 'shop.json'):
            (fixture/'gamedata'/name).write_bytes(b'{}')
        for name in ('tests.json', 'ai_opponent_progression.py', 'install.py'):
            (fixture/name).write_bytes((d.R/name).read_bytes())
        (fixture/'transaction-tests.json').write_bytes(d.encoded(dict(status='PASS', installer_sha256=d.sha(d.R/'install.py'))))
        active = [False]
        events = []
        @contextmanager
        def simulated_locks():
            active[0] = True
            events.append('locked')
            try:
                yield
            finally:
                active[0] = False
                events.append('unlocked')
        def check_finish(*args):
            assert not active[0], 'Watcher restore checked while publisher lock held'
            events.append('finish')
        try:
            d.R = d.S = fixture
            d.closed = lambda: None
            d.locks = simulated_locks
            d.plan = lambda: {}
            d.hot_status = lambda: {'revision': 'unchanged'}
            d.stop = lambda: events.append('stop')
            d.apply = lambda p: {}
            d.start = lambda: (1, 'mock readiness')
            d.finish = check_finish
            d.main()
            assert events == ['locked', 'stop', 'unlocked', 'finish']
            cases.append('watcher_restore_verified_after_publication_unlock')
        finally:
            for name, original in originals.items():
                setattr(d, name, original)
    report = dict(status='PASS', cases=cases, case_count=len(cases),
                  installer_sha256=d.sha(d.R/'install.py'),
                  formal_files_written=False, services_touched=False)
    (d.R/'transaction-tests.json').write_bytes(d.encoded(report))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
